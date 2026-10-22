"""Delivery note history: retention, monthly photo limit, cancellation.

The history is never rewritten: a cancellation ADDS declarations that put the
previous statuses back; it does not delete the ones made by the note.
"""

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update

from ..config import HISTORY_PHOTO_RETENTION_DAYS, HISTORY_RETENTION_MONTHS
from ..db import SessionLocal, utcnow
from ..models import (SOURCE_MANUAL, DeliveryLine, DeliveryNote, DeliveryPhoto, DeliveryScan,
                      StockDeclaration, TrackedMedicine)

logger = logging.getLogger("medradar")

SCAN_LIFETIME = timedelta(hours=1)
CANCEL_WINDOW = timedelta(hours=24)
PHOTO_PAGES_PER_MONTH = 50
PHOTO_MAX_BYTES = 300 * 1024
CLEANUP_EVERY = timedelta(days=1)


def month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def months_ago(now: datetime, months: int) -> datetime:
    year, month = divmod(now.year * 12 + now.month - 1 - months, 12)
    day = min(now.day, 28)  # every month has a 28th
    return now.replace(year=year, month=month + 1, day=day)


def photo_pages_this_month(db, pharmacy_id, now=None) -> int:
    since = month_start(now or utcnow())
    return db.scalar(
        select(func.count(DeliveryPhoto.id))
        .join(DeliveryNote, DeliveryNote.id == DeliveryPhoto.bon_id)
        .where(DeliveryNote.pharmacie_id == pharmacy_id, DeliveryPhoto.cree_le >= since)) or 0


def can_keep_photos(db, pharmacy_id, pages, now=None) -> bool:
    return photo_pages_this_month(db, pharmacy_id, now) + pages <= PHOTO_PAGES_PER_MONTH


def annulable(note: DeliveryNote, now=None) -> bool:
    return note.annule_le is None and (now or utcnow()) - note.confirme_le <= CANCEL_WINDOW


# --------------------------------------------------------------------------
# Retention
# --------------------------------------------------------------------------

def purge_expired_scans(db, now=None):
    """Unconfirmed scans (and their pages) disappear after 1 hour."""
    result = db.execute(delete(DeliveryScan).where(DeliveryScan.expire_le < (now or utcnow())))
    db.commit()
    return result.rowcount


def purge_history(db, now=None):
    """Photos older than HISTORY_PHOTO_RETENTION_DAYS (the detail stays), then notes
    older than HISTORY_RETENTION_MONTHS. Returns (photos, notes) deleted."""
    now = now or utcnow()
    photo_limit = now - timedelta(days=HISTORY_PHOTO_RETENTION_DAYS)
    old_photos = select(DeliveryPhoto.bon_id).where(DeliveryPhoto.cree_le < photo_limit)
    affected = set(db.scalars(old_photos))
    photos = db.execute(delete(DeliveryPhoto).where(DeliveryPhoto.cree_le < photo_limit)).rowcount
    if affected:
        still = set(db.scalars(select(DeliveryPhoto.bon_id).where(DeliveryPhoto.bon_id.in_(affected))))
        db.execute(update(DeliveryNote).where(DeliveryNote.id.in_(affected - still))
                   .values(photo_gardee=False))

    note_limit = months_ago(now, HISTORY_RETENTION_MONTHS)
    old_notes = select(DeliveryNote.id).where(DeliveryNote.confirme_le < note_limit)
    # The declarations stay; only their link to the note goes
    db.execute(update(StockDeclaration).where(StockDeclaration.bon_id.in_(old_notes))
               .values(bon_id=None))
    db.execute(delete(DeliveryLine).where(DeliveryLine.bon_id.in_(old_notes)))
    db.execute(delete(DeliveryPhoto).where(DeliveryPhoto.bon_id.in_(old_notes)))
    notes = db.execute(delete(DeliveryNote).where(DeliveryNote.confirme_le < note_limit)).rowcount
    db.commit()
    return photos, notes


def run_cleanup():
    """At startup, then once a day (app/main.py)."""
    with SessionLocal() as db:
        scans = purge_expired_scans(db)
        photos, notes = purge_history(db)
    if scans or photos or notes:
        logger.info("Delivery cleanup: %d scans, %d photo pages, %d notes deleted",
                    scans, photos, notes)


def delete_note(db, note: DeliveryNote):
    """Lines and photos go; the stock declarations stay, without their link."""
    db.execute(update(StockDeclaration).where(StockDeclaration.bon_id == note.id)
               .values(bon_id=None))
    db.delete(note)
    db.commit()


# --------------------------------------------------------------------------
# Cancellation (24 hours): previous statuses are put back by NEW declarations
# --------------------------------------------------------------------------

def cancel_note(db, note: DeliveryNote, user_id: int):
    """Returns (restored, left): medicine ids put back, and ids declared again since."""
    now = utcnow()
    made = db.scalars(select(StockDeclaration)
                      .where(StockDeclaration.bon_id == note.id)
                      .order_by(StockDeclaration.id)).all()
    restored, left = [], []
    for declaration in made:
        same = (StockDeclaration.pharmacy_id == note.pharmacie_id,
                StockDeclaration.medicine_id == declaration.medicine_id)
        newer = db.scalar(select(StockDeclaration.id).where(
            *same, StockDeclaration.id > declaration.id, StockDeclaration.bon_id.is_distinct_from(note.id))
            .limit(1))
        if newer is not None:
            left.append(declaration.medicine_id)  # declared again since: left as it is
            continue
        previous = db.scalar(select(StockDeclaration).where(*same, StockDeclaration.id < declaration.id)
                             .order_by(StockDeclaration.declared_at.desc(), StockDeclaration.id.desc())
                             .limit(1))
        if previous is not None:
            db.add(StockDeclaration(pharmacy_id=note.pharmacie_id, medicine_id=declaration.medicine_id,
                                    status=previous.status, declared_by=user_id, declared_at=now,
                                    source=SOURCE_MANUAL))
        else:
            # No status before the note: back to "no information" (no invented "out of
            # stock"). The declarations stay in the history; the medicine is no longer
            # followed, so patients see no information for this pharmacy.
            tracked = db.get(TrackedMedicine, (note.pharmacie_id, declaration.medicine_id))
            if tracked is not None:
                db.delete(tracked)
        restored.append(declaration.medicine_id)
    note.annule_le = now
    db.commit()
    return restored, left
