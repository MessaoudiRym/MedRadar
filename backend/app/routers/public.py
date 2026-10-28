"""Public routes for patients: pharmacies, availability and alerts. No account needed."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..geo import ORAN_CENTER, haversine_km, nearest_district
from ..limiter import limiter
from ..models import PHARMACY_VALIDATED, STOCK_IN, Alert, Pharmacy, Search
from ..schemas import AlertIn, AlertOut, Availability, PublicPharmacy
from ..stock import is_stale, latest_declarations
from .medicines import NOTICE, get_medicine_or_404

router = APIRouter(tags=["patients"])

DEMO_MESSAGE = "Disponibilités simulées pour la démonstration."
MAX_ACTIVE_ALERTS = 5
DEFAULT_RADIUS_KM = 10
NOT_COUNTED_HEADER = "x-medradar-check"


@router.get("/pharmacies", response_model=list[PublicPharmacy])
def list_pharmacies(db: Session = Depends(get_db)):
    """Validated pharmacies only (demo ones included), without personal data."""
    return db.scalars(select(Pharmacy).where(Pharmacy.status == PHARMACY_VALIDATED)
                      .order_by(Pharmacy.name)).all()


@router.get("/medicines/{medicine_id}/availability", response_model=Availability)
def availability(
    request: Request,
    medicine_id: str,
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    radius_km: float = Query(DEFAULT_RADIUS_KM, gt=0, le=50),
    db: Session = Depends(get_db),
):
    """Where to find this medicine or one of its equivalents, nearest first."""
    medicine = get_medicine_or_404(request, medicine_id)
    if (lat is None) != (lng is None):
        raise HTTPException(status_code=422, detail="lat et lng doivent être envoyés ensemble.")
    position_given = lat is not None
    if not position_given:
        lat, lng = ORAN_CENTER

    # The medicine itself (all its packs) and its exact equivalents
    group = request.app.state.store.same_key(medicine)
    by_id = {m["id"]: m for m in group}
    rows = latest_declarations(db, medicine_ids=by_id)
    pharmacies = {p.id: p for p in db.scalars(select(Pharmacy).where(
        Pharmacy.id.in_({r.pharmacy_id for r in rows}),
        Pharmacy.status == PHARMACY_VALIDATED))}

    results = {m_id: {"en_stock": [], "rupture": []} for m_id in by_id}
    for row in rows:
        pharmacy = pharmacies.get(row.pharmacy_id)
        if pharmacy is None:  # pending, rejected or suspended
            continue
        distance = haversine_km(lat, lng, pharmacy.latitude, pharmacy.longitude)
        if distance > radius_km:
            continue
        entry = PublicPharmacy.model_validate(pharmacy).model_dump() | {
            "statut": row.status,
            "distance_km": round(distance, 2),
            "derniere_mise_a_jour": row.declared_at,
            "a_confirmer": is_stale(row.declared_at),
        }
        results[row.medicine_id]["en_stock" if row.status == STOCK_IN else "rupture"].append(entry)

    groups = []
    for m_id, lists in results.items():
        is_requested = by_id[m_id]["nom_marque"] == medicine["nom_marque"]
        if not is_requested and not lists["en_stock"] and not lists["rupture"]:
            continue
        for entries in lists.values():
            entries.sort(key=lambda e: e["distance_km"])
        groups.append({"medicament": by_id[m_id], "est_demande": is_requested, **lists})
    groups.sort(key=lambda g: (not g["est_demande"], -len(g["en_stock"]),
                               g["medicament"]["nom_marque"]))

    shown = [e for g in groups for e in g["en_stock"] + g["rupture"]]
    demo = any(e["est_demo"] for e in shown)

    # Anonymous statistics: the medicine and, at most, the district. The automatic
    # checks of the online version (scripts/smoke_test.py) are not counted.
    if request.headers.get(NOT_COUNTED_HEADER) != "1":
        db.add(Search(medicine_id=medicine["id"],
                      district=nearest_district(lat, lng) if position_given else None))
        db.commit()

    return {
        "medicament": medicine,
        "latitude": lat,
        "longitude": lng,
        "rayon_km": radius_km,
        "nb_pharmacies_en_stock": len({e["id"] for g in groups for e in g["en_stock"]}),
        "resultats": groups,
        "demo_data": demo,
        "demo_message": DEMO_MESSAGE if demo else None,
        "notice": NOTICE,
    }


@router.post("/alerts", response_model=AlertOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
def create_alert(request: Request, data: AlertIn, db: Session = Depends(get_db)):
    """Be emailed once when the medicine, or an exact equivalent, is declared in stock nearby."""
    if request.app.state.mailer is None:
        raise HTTPException(status_code=503, detail="Les alertes par email ne sont pas disponibles.")
    medicine = get_medicine_or_404(request, data.medicament_id)
    active = Alert.email == data.email, Alert.sent_at.is_(None)
    if db.scalar(select(Alert.id).where(*active, Alert.medicine_id == medicine["id"])):
        raise HTTPException(status_code=409, detail="Une alerte existe déjà pour ce médicament.")
    if db.scalar(select(func.count()).select_from(Alert).where(*active)) >= MAX_ACTIVE_ALERTS:
        raise HTTPException(status_code=409,
                            detail=f"Limite de {MAX_ACTIVE_ALERTS} alertes atteinte pour cet email.")

    lat, lng = (data.lat, data.lng) if data.lat is not None else ORAN_CENTER
    alert = Alert(
        email=data.email,
        medicine_id=medicine["id"],
        # Rounded to about 1 km: enough to find nearby pharmacies, less precise than a home
        latitude=round(lat, 2),
        longitude=round(lng, 2),
        radius_km=data.rayon_km or DEFAULT_RADIUS_KM,
    )
    db.add(alert)
    db.commit()
    return {"id": alert.id, "medicament_id": alert.medicine_id,
            "message": "Alerte enregistrée. Vous serez prévenu(e) par email."}
