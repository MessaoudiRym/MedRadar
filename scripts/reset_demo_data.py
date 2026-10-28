"""Put the demo data back in its initial state (every night during the jury week).

Deleted and recreated: the demo pharmacies (is_demo = True, the 2 pending ones
included, so the admin can always show a validation), their stock and history,
and the demo pharmacist accounts (pharmacien1@medradar.demo ...) with the password
DEMO_PHARMACIST_PASSWORD. Dates are relative to today.

Never touched: pharmacies registered by real pharmacists, their accounts, and the
admin account. The script checks it before saving: if anything else would change,
nothing is saved and it stops with an error.

DATABASE_URL must be set in the environment (the .env file is not enough), so
that the production database is never reset by accident.

Usage:
    DATABASE_URL=... DEMO_PHARMACIST_PASSWORD=... python scripts/reset_demo_data.py
"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

if not os.environ.get("DATABASE_URL", "").strip():
    sys.exit("DATABASE_URL is not set in the environment: nothing done. "
             "Set it for this command only (see docs/deployment.md).")

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import func, select  # noqa: E402

from app.config import DATABASE_URL  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Pharmacy, StockDeclaration, User  # noqa: E402
from app.schemas import check_password  # noqa: E402
from generate_demo_data import DEMO_EMAIL_DOMAIN, print_summary, rebuild  # noqa: E402


def where():
    """The database, without the password: e.g. postgresql+psycopg on ep-xxx.neon.tech."""
    parts = urlsplit(DATABASE_URL)
    return f"{parts.scheme} on {parts.hostname or parts.path}"


def protected(db):
    """Everything the reset must never change: real pharmacies, other accounts."""
    real = select(Pharmacy.id).where(Pharmacy.is_demo.is_(False))
    return {
        "real pharmacies": sorted(tuple(row) for row in db.execute(
            select(Pharmacy.id, Pharmacy.status, Pharmacy.owner_id, Pharmacy.address)
            .where(Pharmacy.is_demo.is_(False)))),
        "their stock declarations": db.scalar(select(func.count()).select_from(StockDeclaration)
                                              .where(StockDeclaration.pharmacy_id.in_(real))),
        "other accounts (admin, real pharmacists)": sorted(tuple(row) for row in db.execute(
            select(User.id, User.email, User.role, User.password_hash)
            .where(User.email.not_like(f"%{DEMO_EMAIL_DOMAIN}")))),
    }


def demo_counts(db):
    demo = select(Pharmacy.id).where(Pharmacy.is_demo.is_(True))
    return (db.scalar(select(func.count()).select_from(Pharmacy).where(Pharmacy.is_demo.is_(True))),
            db.scalar(select(func.count()).select_from(StockDeclaration)
                      .where(StockDeclaration.pharmacy_id.in_(demo))))


def main():
    password = os.environ.get("DEMO_PHARMACIST_PASSWORD", "")
    try:
        check_password(password)
    except ValueError as error:
        sys.exit(f"DEMO_PHARMACIST_PASSWORD is missing or too weak: {error}")

    print(f"Database        : {where()}")
    with SessionLocal() as db:
        # A real pharmacy owned by a "@medradar.demo" account would lose its owner
        owners = db.scalar(select(func.count()).select_from(Pharmacy).join(
            User, Pharmacy.owner_id == User.id).where(
            Pharmacy.is_demo.is_(False), User.email.like(f"%{DEMO_EMAIL_DOMAIN}")))
        if owners:
            sys.exit(f"{owners} real pharmacy(ies) belong to a {DEMO_EMAIL_DOMAIN} account: "
                     "nothing done, check them in the admin space first.")

        before = protected(db)
        old_pharmacies, old_declarations = demo_counts(db)
        summary = rebuild(db, password)
        db.flush()
        after = protected(db)

        changed = [name for name in before if before[name] != after[name]]
        if changed:
            db.rollback()
            sys.exit("Stopped, nothing saved: the reset would change " + ", ".join(changed))
        db.commit()

    print(f"Deleted         : {old_pharmacies} demo pharmacies, {old_declarations} of their "
          "stock declarations, their history and the demo accounts")
    print_summary(summary)
    print(f"Untouched       : {len(before['real pharmacies'])} real pharmacies, "
          f"{len(before['other accounts (admin, real pharmacists)'])} other accounts (admin included)")
    print("Demo data reset: OK")


if __name__ == "__main__":
    main()
