"""Admin space: check pharmacies before patients can see them."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, selectinload

from ..db import get_db, utcnow
from ..delivery.schemas import DeliveryStats
from ..models import (PHARMACY_PENDING, PHARMACY_REJECTED, PHARMACY_SUSPENDED,
                      PHARMACY_VALIDATED, DeliveryLine, DeliveryNote, DeliveryPhoto, Pharmacy,
                      User)
from ..schemas import AdminPharmacy, ReasonIn
from ..security import require_admin

# Every route of this router requires an admin token
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

PharmacyStatus = Literal["en_attente", "validee", "refusee", "suspendue"]


def _get_pharmacy(db, pharmacy_id):
    pharmacy = db.get(Pharmacy, pharmacy_id)
    if pharmacy is None:
        raise HTTPException(status_code=404, detail="Pharmacie introuvable.")
    return pharmacy


def _check_transition(pharmacy, allowed_from, action):
    if pharmacy.status not in allowed_from:
        raise HTTPException(status_code=409,
                            detail=f"Impossible de {action} une pharmacie au statut "
                                   f"« {pharmacy.status} ».")


@router.get("/pharmacies", response_model=list[AdminPharmacy])
def list_pharmacies(statut: PharmacyStatus | None = Query(None), db: Session = Depends(get_db)):
    query = select(Pharmacy).options(selectinload(Pharmacy.owner)).order_by(Pharmacy.created_at)
    if statut:
        query = query.where(Pharmacy.status == statut)
    return db.scalars(query).all()


@router.post("/pharmacies/{pharmacy_id}/approve", response_model=AdminPharmacy)
def approve(pharmacy_id: int, admin: User = Depends(require_admin),
            db: Session = Depends(get_db)):
    pharmacy = _get_pharmacy(db, pharmacy_id)
    _check_transition(pharmacy, {PHARMACY_PENDING, PHARMACY_REJECTED, PHARMACY_SUSPENDED},
                      "valider")
    pharmacy.status = PHARMACY_VALIDATED
    pharmacy.status_reason = None
    pharmacy.validated_at = utcnow()
    pharmacy.validated_by = admin.id
    db.commit()
    return pharmacy


@router.post("/pharmacies/{pharmacy_id}/reject", response_model=AdminPharmacy)
def reject(pharmacy_id: int, data: ReasonIn, db: Session = Depends(get_db)):
    pharmacy = _get_pharmacy(db, pharmacy_id)
    _check_transition(pharmacy, {PHARMACY_PENDING}, "refuser")
    pharmacy.status = PHARMACY_REJECTED
    pharmacy.status_reason = data.motif
    db.commit()
    return pharmacy


@router.post("/pharmacies/{pharmacy_id}/suspend", response_model=AdminPharmacy)
def suspend(pharmacy_id: int, data: ReasonIn, db: Session = Depends(get_db)):
    """A suspended pharmacy disappears from patient results and can no longer declare stock."""
    pharmacy = _get_pharmacy(db, pharmacy_id)
    _check_transition(pharmacy, {PHARMACY_VALIDATED}, "suspendre")
    pharmacy.status = PHARMACY_SUSPENDED
    pharmacy.status_reason = data.motif
    db.commit()
    return pharmacy


@router.get("/stats/deliveries", response_model=DeliveryStats)
def delivery_stats(db: Session = Depends(get_db)):
    """Global counts only. The admin never sees the content of a note or its photos."""
    return {
        "bons_gardes": db.scalar(select(func.count(DeliveryNote.id))) or 0,
        "lignes": db.scalar(select(func.count(DeliveryLine.id))) or 0,
        "pages_photos": db.scalar(select(func.count(DeliveryPhoto.id))) or 0,
        "pharmacies_utilisatrices": db.scalar(
            select(func.count(distinct(DeliveryNote.pharmacie_id)))) or 0,
    }
