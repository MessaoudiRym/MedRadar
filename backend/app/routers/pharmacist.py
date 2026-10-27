"""Pharmacist space: own pharmacy and stock declarations.

The pharmacy is ALWAYS the one linked to the logged-in account (get_own_pharmacy):
no route takes a pharmacy id from the client, so a pharmacist cannot write
for another pharmacy.
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..alerts import send_alerts
from ..db import get_db, utcnow
from ..models import (PHARMACY_PENDING, PHARMACY_REJECTED, PHARMACY_VALIDATED, SOURCE_MANUAL, STOCK_IN,
                      DeliveryLine, DeliveryNote, Pharmacy, StockDeclaration, TrackedMedicine,
                      User)
from ..schemas import (DeclarationOut, OwnPharmacy, PharmacyUpdate, StockBulkIn,
                       StockDeclarationIn, TrackedStock)
from ..security import get_own_pharmacy, get_validated_pharmacy, require_pharmacist
from ..stock import is_stale, latest_declarations

router = APIRouter(prefix="/pharmacist", tags=["pharmacist"])


@router.patch("/pharmacy", response_model=OwnPharmacy)
def update_pharmacy(data: PharmacyUpdate, pharmacy: Pharmacy = Depends(get_own_pharmacy),
                    db: Session = Depends(get_db)):
    """Phone and opening hours change freely. A new address or position must be checked again."""
    if data.telephone is not None:
        pharmacy.phone = data.telephone
    if data.horaires is not None:
        pharmacy.opening_hours = data.horaires or None

    moved = False
    if data.adresse is not None and data.adresse != pharmacy.address:
        pharmacy.address = data.adresse
        moved = True
    if data.latitude is not None and (data.latitude, data.longitude) != (
            pharmacy.latitude, pharmacy.longitude):
        pharmacy.latitude, pharmacy.longitude = data.latitude, data.longitude
        moved = True

    # A suspended pharmacy stays suspended: moving is not a way out of a suspension
    if moved and pharmacy.status in (PHARMACY_VALIDATED, PHARMACY_REJECTED):
        pharmacy.status = PHARMACY_PENDING
        pharmacy.status_reason = None
        pharmacy.validated_at = None
        pharmacy.validated_by = None
    db.commit()
    return pharmacy


def _check_medicines(request, medicine_ids):
    store = request.app.state.store
    unknown = [m for m in medicine_ids if store.get(m) is None]
    if unknown:
        raise HTTPException(status_code=404,
                            detail=f"Médicament introuvable : {', '.join(unknown)}")


def notify_alerts(request, background_tasks, pharmacy, items):
    """After the response: email the patients waiting for a medicine now in stock."""
    in_stock = {i.medicament_id for i in items if i.statut == STOCK_IN}
    if in_stock:
        background_tasks.add_task(send_alerts, request.app.state.mailer, request.app.state.store,
                                  pharmacy.id, in_stock)


def _declare(db, pharmacy, user, items, source=SOURCE_MANUAL, bon_id=None, commit=True):
    """Add declarations (history is kept) and track the medicines.

    items: objects with medicament_id and statut. commit=False lets the delivery
    note confirmation save everything in one transaction.
    """
    now = utcnow()
    tracked = {t.medicine_id for t in db.query(TrackedMedicine).filter(
        TrackedMedicine.pharmacy_id == pharmacy.id,
        TrackedMedicine.medicine_id.in_([i.medicament_id for i in items]))}
    declarations = []
    for item in items:
        declarations.append(StockDeclaration(
            pharmacy_id=pharmacy.id, medicine_id=item.medicament_id,
            status=item.statut, declared_by=user.id, declared_at=now,
            source=source, bon_id=bon_id))
        if item.medicament_id not in tracked:
            db.add(TrackedMedicine(pharmacy_id=pharmacy.id, medicine_id=item.medicament_id))
            tracked.add(item.medicament_id)
    db.add_all(declarations)
    if commit:
        db.commit()
    return [{"medicament_id": d.medicine_id, "statut": d.status,
             "date_declaration": d.declared_at} for d in declarations]


@router.post("/stock", response_model=DeclarationOut, status_code=status.HTTP_201_CREATED)
def declare_stock(request: Request, data: StockDeclarationIn, background_tasks: BackgroundTasks,
                  pharmacy: Pharmacy = Depends(get_validated_pharmacy),
                  user: User = Depends(require_pharmacist), db: Session = Depends(get_db)):
    _check_medicines(request, [data.medicament_id])
    declared = _declare(db, pharmacy, user, [data])[0]
    notify_alerts(request, background_tasks, pharmacy, [data])
    return declared


@router.post("/stock/bulk", response_model=list[DeclarationOut],
             status_code=status.HTTP_201_CREATED)
def declare_stock_bulk(request: Request, data: StockBulkIn, background_tasks: BackgroundTasks,
                       pharmacy: Pharmacy = Depends(get_validated_pharmacy),
                       user: User = Depends(require_pharmacist), db: Session = Depends(get_db)):
    """Up to 50 declarations; all are saved, or none if one medicine is unknown."""
    _check_medicines(request, [d.medicament_id for d in data.declarations])
    declared = _declare(db, pharmacy, user, data.declarations)
    notify_alerts(request, background_tasks, pharmacy, data.declarations)
    return declared


@router.get("/stock", response_model=list[TrackedStock])
def tracked_stock(request: Request, pharmacy: Pharmacy = Depends(get_own_pharmacy),
                  db: Session = Depends(get_db)):
    """Tracked medicines, the least recently updated first (what to update next)."""
    store = request.app.state.store
    latest = {row.medicine_id: row for row in latest_declarations(db, pharmacy_id=pharmacy.id)}
    tracked = db.query(TrackedMedicine).filter(TrackedMedicine.pharmacy_id == pharmacy.id).all()
    received = last_receptions(db, pharmacy.id)

    items = []
    for t in tracked:
        medicine = store.get(t.medicine_id)
        if medicine is None:  # no longer in the nomenclature
            continue
        row = latest.get(t.medicine_id)
        items.append({
            "medicament": medicine,
            "statut": row.status if row else None,
            "date_declaration": row.declared_at if row else None,
            "a_confirmer": is_stale(row.declared_at) if row else True,
            "derniere_reception": received.get(t.medicine_id),
        })
    # Never declared first, then from oldest to newest
    items.sort(key=lambda i: (i["date_declaration"] is not None,
                              i["date_declaration"] or 0, i["medicament"]["nom_marque"]))
    return items


def last_receptions(db, pharmacy_id):
    """Last reception of each medicine, from the delivery notes kept (not cancelled)."""
    rows = db.execute(
        select(DeliveryNote, DeliveryLine)
        .join(DeliveryLine, DeliveryLine.bon_id == DeliveryNote.id)
        .where(DeliveryNote.pharmacie_id == pharmacy_id, DeliveryNote.annule_le.is_(None),
               DeliveryLine.action == "en_stock", DeliveryLine.medicament_id.is_not(None))
        .order_by(DeliveryNote.confirme_le.desc(), DeliveryLine.id)).all()
    last = {}
    for note, line in rows:
        last.setdefault(line.medicament_id, {
            "bon_id": note.id, "date": note.date_bon or note.confirme_le.date(),
            "fournisseur": note.fournisseur, "quantite": line.quantite,
            "numero_lot": line.numero_lot, "date_peremption": line.date_peremption})
    return last


@router.delete("/tracked/{medicine_id}", status_code=status.HTTP_204_NO_CONTENT)
def untrack(medicine_id: str, pharmacy: Pharmacy = Depends(get_own_pharmacy),
            db: Session = Depends(get_db)):
    """Stop following a medicine: it is no longer shown to patients for this pharmacy."""
    tracked = db.get(TrackedMedicine, (pharmacy.id, medicine_id))
    if tracked is None:
        raise HTTPException(status_code=404, detail="Ce médicament n'est pas dans votre liste.")
    db.delete(tracked)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
