"""History of the delivery notes a pharmacist chose to keep (traceability).

Only the pharmacist's own pharmacy: a note of another pharmacy is "not found"
(404), never "forbidden", so its existence is not revealed. No price or amount
is ever stored. Photos are served only to the owner, never cached.
"""

import csv
import io
import math
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..delivery.history import annulable, cancel_note, delete_note
from ..delivery.matching import summary
from ..delivery.schemas import (CancelOut, NoteDetail, NoteList, NoteUpdate, Reception)
from ..models import DeliveryLine, DeliveryNote, DeliveryPhoto, Pharmacy, User
from ..security import get_validated_pharmacy, require_pharmacist

router = APIRouter(prefix="/pharmacist", tags=["delivery notes"])

PER_PAGE = 20
NOT_FOUND = "Bon introuvable."
NO_PHOTO = "Pas de photo pour ce bon."
CANCEL_TOO_LATE = "Un bon ne peut être annulé que dans les 24 heures après sa confirmation."
ALREADY_CANCELLED = "Ce bon est déjà annulé."
EXPORT_COLUMNS = ["date", "fournisseur", "numero_bon", "medicament", "dosage", "quantite",
                  "numero_lot", "date_peremption", "action"]


def _note(db, note_id: int, pharmacy: Pharmacy) -> DeliveryNote:
    note = db.get(DeliveryNote, note_id)
    if note is None or note.pharmacie_id != pharmacy.id:
        raise HTTPException(status_code=404, detail=NOT_FOUND)
    return note


def _summary(note: DeliveryNote) -> dict:
    fields = ("id", "fournisseur", "numero_bon", "date_bon", "scanne_le", "confirme_le",
              "duree_secondes", "nb_lignes_lues", "nb_mis_en_stock", "nb_rupture", "nb_non_livres",
              "nb_ignores", "photo_gardee", "annule_le")
    return {f: getattr(note, f) for f in fields} | {"annulable": annulable(note)}


def _period(query, du: date | None, au: date | None):
    if du:
        query = query.where(DeliveryNote.confirme_le >= datetime.combine(du, time.min))
    if au:
        query = query.where(DeliveryNote.confirme_le <= datetime.combine(au, time.max))
    return query


@router.get("/deliveries", response_model=NoteList)
def list_notes(request: Request, du: date | None = None, au: date | None = None,
               fournisseur: str | None = Query(None, max_length=120),
               q: str | None = Query(None, max_length=100,
                                     description="A medicine: when did I receive it?"),
               page: int = Query(1, ge=1), pharmacy: Pharmacy = Depends(get_validated_pharmacy),
               db: Session = Depends(get_db)):
    """Notes of the history, the most recent first."""
    query = _period(select(DeliveryNote).where(DeliveryNote.pharmacie_id == pharmacy.id), du, au)
    if fournisseur:
        query = query.where(DeliveryNote.fournisseur.ilike(f"%{fournisseur.strip()}%"))
    if q and q.strip():
        # The medicines matching the query (any language), or the text read on the note
        ids = [m["id"] for m in request.app.state.smart_search.suggest(q, 50)]
        with_medicine = select(DeliveryLine.bon_id).where(or_(
            DeliveryLine.medicament_id.in_(ids),
            DeliveryLine.designation_lue.ilike(f"%{q.strip()}%")))
        query = query.where(DeliveryNote.id.in_(with_medicine))
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    notes = db.scalars(query.order_by(DeliveryNote.confirme_le.desc(), DeliveryNote.id.desc())
                       .offset((page - 1) * PER_PAGE).limit(PER_PAGE)).all()
    return {"page": page, "pages": max(1, math.ceil(total / PER_PAGE)), "total": total,
            "bons": [_summary(n) for n in notes]}


@router.get("/deliveries/export")
def export_csv(request: Request, du: date | None = None, au: date | None = None,
               pharmacy: Pharmacy = Depends(get_validated_pharmacy),
               db: Session = Depends(get_db)):
    """The lines of the notes of a period, for accounting or an inspection. No price."""
    store = request.app.state.store
    query = _period(select(DeliveryNote, DeliveryLine)
                    .join(DeliveryLine, DeliveryLine.bon_id == DeliveryNote.id)
                    .where(DeliveryNote.pharmacie_id == pharmacy.id), du, au)
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(EXPORT_COLUMNS)
    for note, line in db.execute(query.order_by(DeliveryNote.confirme_le, DeliveryLine.id)):
        medicine = store.get(line.medicament_id) if line.medicament_id else None
        writer.writerow([
            (note.date_bon or note.confirme_le.date()).isoformat(), note.fournisseur or "",
            note.numero_bon or "",
            medicine["nom_marque"] if medicine else line.designation_lue,
            medicine["dosage_norm"] if medicine else "",
            "" if line.quantite is None else f"{line.quantite:g}",
            line.numero_lot or "", line.date_peremption or "",
            line.action + (" (bon annulé)" if note.annule_le else ""),
        ])
    name = f"medradar-bons-{du or 'debut'}-{au or 'aujourdhui'}.csv"
    # A BOM so that Excel reads the accents
    return Response(content="﻿" + out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{name}"',
                             "Cache-Control": "private, no-store"})


@router.get("/deliveries/{note_id}", response_model=NoteDetail)
def get_note(request: Request, note_id: int, pharmacy: Pharmacy = Depends(get_validated_pharmacy),
             db: Session = Depends(get_db)):
    note = _note(db, note_id, pharmacy)
    store = request.app.state.store
    lines = []
    for line in note.lignes:
        medicine = store.get(line.medicament_id) if line.medicament_id else None
        lines.append({
            "id": line.id, "designation_lue": line.designation_lue,
            "medicament_id": line.medicament_id,
            "medicament": summary(medicine) if medicine else None,
            "quantite": line.quantite, "numero_lot": line.numero_lot,
            "date_peremption": line.date_peremption,
            "statut_correspondance": line.statut_correspondance, "action": line.action,
            "corrigee_par_pharmacien": line.corrigee_par_pharmacien,
        })
    pages = db.scalars(select(DeliveryPhoto.page).where(DeliveryPhoto.bon_id == note.id)
                       .order_by(DeliveryPhoto.page)).all()
    return _summary(note) | {"lignes": lines, "pages_photos": pages}


@router.get("/deliveries/{note_id}/photos/{page}", response_class=Response,
            responses={200: {"content": {"image/jpeg": {}}}})
def get_photo(note_id: int, page: int, pharmacy: Pharmacy = Depends(get_validated_pharmacy),
              db: Session = Depends(get_db)):
    """Only for the pharmacy that kept it; never a public link, never cached."""
    note = _note(db, note_id, pharmacy)
    photo = db.scalar(select(DeliveryPhoto).where(DeliveryPhoto.bon_id == note.id,
                                                  DeliveryPhoto.page == page))
    if photo is None:
        raise HTTPException(status_code=404, detail=NO_PHOTO)
    return Response(content=photo.image, media_type="image/jpeg",
                    headers={"Cache-Control": "private, no-store"})


@router.patch("/deliveries/{note_id}", response_model=NoteDetail)
def update_note(request: Request, note_id: int, data: NoteUpdate,
                pharmacy: Pharmacy = Depends(get_validated_pharmacy),
                db: Session = Depends(get_db)):
    """Correct the supplier, the number or the date of the note."""
    note = _note(db, note_id, pharmacy)
    for field in data.model_fields_set:
        setattr(note, field, getattr(data, field) or None)
    db.commit()
    return get_note(request, note_id, pharmacy, db)


@router.delete("/deliveries/{note_id}/photos", status_code=status.HTTP_204_NO_CONTENT)
def delete_photos(note_id: int, pharmacy: Pharmacy = Depends(get_validated_pharmacy),
                  db: Session = Depends(get_db)):
    """Delete only the photos; the detail of the note stays."""
    note = _note(db, note_id, pharmacy)
    note.photos = []
    note.photo_gardee = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/deliveries/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_note(note_id: int, pharmacy: Pharmacy = Depends(get_validated_pharmacy),
                db: Session = Depends(get_db)):
    """Delete the note, its lines and photos. Stock declarations already made stay."""
    delete_note(db, _note(db, note_id, pharmacy))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/deliveries/{note_id}/cancel", response_model=CancelOut)
def cancel(request: Request, note_id: int, pharmacy: Pharmacy = Depends(get_validated_pharmacy),
           user: User = Depends(require_pharmacist), db: Session = Depends(get_db)):
    """Undo a note confirmed by mistake, within 24 hours: the previous statuses are put
    back by new declarations; medicines declared again since are left as they are."""
    note = _note(db, note_id, pharmacy)
    if note.annule_le is not None:
        raise HTTPException(status_code=409, detail=ALREADY_CANCELLED)
    if not annulable(note):
        raise HTTPException(status_code=409, detail=CANCEL_TOO_LATE)
    restored, left = cancel_note(db, note, user.id)
    store = request.app.state.store

    def ref(medicine_id):
        medicine = store.get(medicine_id) or {}
        return {"medicament_id": medicine_id, "nom_marque": medicine.get("nom_marque"),
                "dosage_norm": medicine.get("dosage_norm")}
    return {"annule_le": note.annule_le, "retablis": [ref(m) for m in restored],
            "laisses": [ref(m) for m in left]}


@router.get("/medicines/{medicine_id}/receptions", response_model=list[Reception])
def receptions(medicine_id: str, pharmacy: Pharmacy = Depends(get_validated_pharmacy),
               db: Session = Depends(get_db)):
    """The last receptions of a medicine, from the notes kept in the history."""
    rows = db.execute(
        select(DeliveryNote, DeliveryLine)
        .join(DeliveryLine, DeliveryLine.bon_id == DeliveryNote.id)
        .where(DeliveryNote.pharmacie_id == pharmacy.id, DeliveryLine.medicament_id == medicine_id,
               DeliveryLine.action == "en_stock")
        .order_by(DeliveryNote.confirme_le.desc()).limit(10)).all()
    return [reception(note, line) for note, line in rows]


def reception(note: DeliveryNote, line: DeliveryLine) -> dict:
    return {"bon_id": note.id, "date": note.date_bon or note.confirme_le.date(),
            "fournisseur": note.fournisseur, "numero_bon": note.numero_bon,
            "quantite": line.quantite, "numero_lot": line.numero_lot,
            "date_peremption": line.date_peremption, "annule": note.annule_le is not None}
