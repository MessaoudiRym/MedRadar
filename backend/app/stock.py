"""Current stock status = the most recent declaration for (pharmacy, medicine)."""

from datetime import timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from .db import utcnow
from .models import StockDeclaration, TrackedMedicine

STALE_AFTER = timedelta(days=7)


def is_stale(declared_at):
    """Older than 7 days: the patient should call before going."""
    return declared_at is not None and utcnow() - declared_at > STALE_AFTER


def latest_declarations(db: Session, medicine_ids=None, pharmacy_id=None):
    """Most recent declaration of each tracked (pharmacy, medicine) pair.

    Returns rows (pharmacy_id, medicine_id, status, declared_at). A medicine
    removed from a pharmacy's tracked list is no longer shown to patients.
    """
    ranked = select(
        StockDeclaration.pharmacy_id,
        StockDeclaration.medicine_id,
        StockDeclaration.status,
        StockDeclaration.declared_at,
        func.row_number().over(
            partition_by=(StockDeclaration.pharmacy_id, StockDeclaration.medicine_id),
            order_by=(StockDeclaration.declared_at.desc(), StockDeclaration.id.desc()),
        ).label("rank"),
    )
    if medicine_ids is not None:
        ranked = ranked.where(StockDeclaration.medicine_id.in_(list(medicine_ids)))
    if pharmacy_id is not None:
        ranked = ranked.where(StockDeclaration.pharmacy_id == pharmacy_id)
    ranked = ranked.subquery()

    query = (
        select(ranked.c.pharmacy_id, ranked.c.medicine_id, ranked.c.status, ranked.c.declared_at)
        .join(TrackedMedicine, and_(TrackedMedicine.pharmacy_id == ranked.c.pharmacy_id,
                                    TrackedMedicine.medicine_id == ranked.c.medicine_id))
        .where(ranked.c.rank == 1)
    )
    return db.execute(query).all()
