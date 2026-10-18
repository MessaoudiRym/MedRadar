"""Create (or reset the password of) the admin account.

The email and password are read from ADMIN_EMAIL and ADMIN_PASSWORD
(environment or .env file): they are never written in the code.
No API route can create an admin: this script is the only way.

Usage (after `alembic upgrade head`):
    python scripts/create_admin.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from email_validator import EmailNotValidError, validate_email  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.db import SessionLocal, utcnow  # noqa: E402  (also loads .env)
from app.models import ROLE_ADMIN, User  # noqa: E402
from app.schemas import check_password  # noqa: E402
from app.security import hash_password  # noqa: E402


def main():
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        sys.exit("ADMIN_EMAIL and ADMIN_PASSWORD must be set (in .env or the environment).")
    try:
        email = validate_email(email, check_deliverability=False).normalized.lower()
        check_password(password)
    except (EmailNotValidError, ValueError) as error:
        sys.exit(f"Invalid admin credentials: {error}")

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is not None and user.role != ROLE_ADMIN:
            sys.exit(f"{email} already exists as a {user.role} account; choose another email.")
        if user is None:
            db.add(User(email=email, password_hash=hash_password(password),
                        last_name="Admin", first_name="MedRadar", phone="", role=ROLE_ADMIN))
            print(f"Admin account created: {email}")
        else:
            user.password_hash = hash_password(password)
            user.password_changed_at = utcnow()  # old tokens stop working
            print(f"Admin account already exists, password updated: {email}")
        db.commit()


if __name__ == "__main__":
    main()
