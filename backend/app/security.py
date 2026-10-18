"""Passwords (bcrypt), tokens (JWT) and access checks.

- A password is never stored: only its bcrypt hash.
- After login, the user receives a signed token (JWT) valid 7 days.
- Each protected route reads the token, checks its signature and expiry,
  then loads the user from the database: the role comes from the database,
  not from the token.
"""

import calendar
from datetime import timedelta

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import JWT_ALGORITHM, JWT_EXPIRE_DAYS, jwt_secret
from .db import get_db, utcnow
from .models import (PHARMACY_PENDING, PHARMACY_REJECTED, PHARMACY_SUSPENDED,
                     PHARMACY_VALIDATED, ROLE_ADMIN, ROLE_PHARMACIST, Pharmacy, User)

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Used to spend the same time when the email does not exist,
# so that response time does not reveal which accounts exist
_DUMMY_HASH = password_context.hash("not-a-real-password-0")

bearer = HTTPBearer(auto_error=False)

NOT_AUTHENTICATED = "Authentification requise."
INVALID_TOKEN = "Session invalide ou expirée. Veuillez vous reconnecter."


def hash_password(password):
    return password_context.hash(password)


def verify_password(password, password_hash):
    return password_context.verify(password, password_hash or _DUMMY_HASH)


def create_access_token(user):
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "role": user.role,
        "iat": _timestamp(now),
        "exp": _timestamp(now + timedelta(days=JWT_EXPIRE_DAYS)),
    }
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM)


def _timestamp(naive_utc):
    """Seconds since 1970 for a UTC date stored without time zone."""
    return calendar.timegm(naive_utc.utctimetuple())


def _unauthorized(detail):
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    if credentials is None:
        raise _unauthorized(NOT_AUTHENTICATED)
    try:
        payload = jwt.decode(credentials.credentials, jwt_secret(),
                             algorithms=[JWT_ALGORITHM], options={"require": ["sub", "exp", "iat"]})
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError):
        raise _unauthorized(INVALID_TOKEN)

    user = db.get(User, user_id)
    if user is None:
        raise _unauthorized(INVALID_TOKEN)
    # Tokens created before a password change are no longer valid
    if user.password_changed_at and payload["iat"] < _timestamp(user.password_changed_at):
        raise _unauthorized(INVALID_TOKEN)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_ADMIN:
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs.")
    return user


def require_pharmacist(user: User = Depends(get_current_user)) -> User:
    if user.role != ROLE_PHARMACIST:
        raise HTTPException(status_code=403, detail="Accès réservé aux pharmaciens.")
    return user


def get_own_pharmacy(user: User = Depends(require_pharmacist),
                     db: Session = Depends(get_db)) -> Pharmacy:
    """The pharmacy of the logged-in pharmacist — never one chosen by the client."""
    pharmacy = db.query(Pharmacy).filter(Pharmacy.owner_id == user.id).one_or_none()
    if pharmacy is None:
        raise HTTPException(status_code=403, detail="Aucune pharmacie liée à ce compte.")
    return pharmacy


PHARMACY_NOT_VALIDATED = {
    PHARMACY_PENDING: "Votre pharmacie est en cours de vérification.",
    PHARMACY_REJECTED: "Votre pharmacie a été refusée. Consultez le motif dans votre espace.",
    PHARMACY_SUSPENDED: "Votre pharmacie est suspendue. Consultez le motif dans votre espace.",
}


def get_validated_pharmacy(pharmacy: Pharmacy = Depends(get_own_pharmacy)) -> Pharmacy:
    """Only a validated pharmacy can declare stock."""
    if pharmacy.status != PHARMACY_VALIDATED:
        raise HTTPException(status_code=403, detail=PHARMACY_NOT_VALIDATED.get(
            pharmacy.status, PHARMACY_NOT_VALIDATED[PHARMACY_PENDING]))
    return pharmacy
