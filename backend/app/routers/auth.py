"""Pharmacist registration, login and account."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import JWT_EXPIRE_DAYS
from ..db import get_db, utcnow
from ..limiter import limiter
from ..models import PHARMACY_PENDING, ROLE_PHARMACIST, Pharmacy, User
from ..schemas import (ChangePasswordRequest, LoginRequest, Me, PharmacistRegistration,
                       RegisterResponse, Token)
from ..security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

REGISTERED = ("Votre compte a été créé. Il sera visible des patients après "
              "vérification de votre pharmacie.")
BAD_CREDENTIALS = "Email ou mot de passe incorrect"
EMAIL_TAKEN = "Un compte existe déjà avec cet email."
PROFESSIONAL_NUMBER_TAKEN = "Une pharmacie est déjà inscrite avec ce numéro professionnel."


def token_response(user):
    return {
        "access_token": create_access_token(user),
        "role": user.role,
        "expires_in": JWT_EXPIRE_DAYS * 24 * 3600,
    }


@router.post("/register-pharmacist", response_model=RegisterResponse,
             status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def register_pharmacist(request: Request, data: PharmacistRegistration,
                        db: Session = Depends(get_db)):
    """Create the pharmacist account AND the pharmacy, in one transaction.

    The pharmacy starts "en_attente": it is invisible to patients until an admin checks it.
    The role is always "pharmacien": no field of the request can change it.
    """
    if db.scalar(select(User.id).where(User.email == data.email)):
        raise HTTPException(status_code=409, detail=EMAIL_TAKEN)
    p = data.pharmacie
    if db.scalar(select(Pharmacy.id).where(
            Pharmacy.professional_number == p.numero_professionnel)):
        raise HTTPException(status_code=409, detail=PROFESSIONAL_NUMBER_TAKEN)

    user = User(
        email=data.email,
        password_hash=hash_password(data.mot_de_passe),
        last_name=data.nom,
        first_name=data.prenom,
        phone=data.telephone,
        role=ROLE_PHARMACIST,
    )
    pharmacy = Pharmacy(
        name=p.nom, address=p.adresse, commune=p.commune, district=p.quartier,
        latitude=p.latitude, longitude=p.longitude, phone=p.telephone,
        professional_number=p.numero_professionnel, opening_hours=p.horaires,
        status=PHARMACY_PENDING, is_demo=False, owner=user,
    )
    db.add_all([user, pharmacy])
    try:
        db.commit()  # both rows, or neither
    except IntegrityError:
        db.rollback()  # two registrations at the same time with the same email
        raise HTTPException(status_code=409, detail=EMAIL_TAKEN)
    return {"message": REGISTERED, "pharmacie": pharmacy}


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    """Same answer whether the email exists or not, so accounts cannot be discovered."""
    user = db.scalar(select(User).where(User.email == data.email))
    # verify_password runs bcrypt even for an unknown email (same response time)
    password_ok = verify_password(data.mot_de_passe, user.password_hash if user else None)
    if user is None or not password_ok:
        raise HTTPException(status_code=401, detail=BAD_CREDENTIALS,
                            headers={"WWW-Authenticate": "Bearer"})
    user.last_login_at = utcnow()
    db.commit()
    return token_response(user)


@router.get("/me", response_model=Me)
def me(user: User = Depends(get_current_user)):
    return {"utilisateur": user, "pharmacie": user.pharmacy}


@router.post("/change-password", response_model=Token)
@limiter.limit("5/minute")
def change_password(request: Request, data: ChangePasswordRequest,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Returns a new token: tokens created before the change stop working."""
    if not verify_password(data.ancien_mot_de_passe, user.password_hash):
        raise HTTPException(status_code=400, detail="Mot de passe actuel incorrect.")
    if data.ancien_mot_de_passe == data.nouveau_mot_de_passe:
        raise HTTPException(status_code=400,
                            detail="Le nouveau mot de passe doit être différent de l'ancien.")
    user.password_hash = hash_password(data.nouveau_mot_de_passe)
    user.password_changed_at = utcnow()
    db.commit()
    return token_response(user)
