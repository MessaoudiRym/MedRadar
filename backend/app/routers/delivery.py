"""Scan a wholesaler's delivery note: the model reads, our code matches, the
pharmacist confirms. Only for a validated pharmacy, and only its own data.

POST /pharmacist/delivery-scan only ANALYSES: nothing is declared. The result
(and the compressed pages, only if they may be kept) waits 1 hour for the
confirmation, then is deleted. Stock is declared only by
POST /pharmacist/delivery-scan/{scan_id}/confirm, with the pharmacist's list.
"""

import json
import logging
import uuid
from types import SimpleNamespace

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from limits import parse
from sqlalchemy.orm import Session

from ..db import get_db, utcnow
from ..delivery.history import (PHOTO_MAX_BYTES, PHOTO_PAGES_PER_MONTH, SCAN_LIFETIME,
                                can_keep_photos, purge_expired_scans)
from ..delivery.matching import NOT_DELIVERED, LineMatcher, analyse_lines
from ..delivery.reader import read_note
from ..delivery.schemas import ConfirmIn, ConfirmOut, ScanResult
from ..images import ImageRejected, compress_jpeg, prepare_image
from ..limiter import limiter
from ..llm.errors import LLMError, LLMTimeout, ProviderBusy, QuotaExceeded
from ..models import (SOURCE_DELIVERY_SCAN, DeliveryLine, DeliveryNote, DeliveryPhoto,
                      DeliveryScan, DeliveryScanPage, Pharmacy, User)
from ..security import get_validated_pharmacy, require_pharmacist
from ..uploads import UploadRejected, read_files
from .pharmacist import _declare, notify_alerts

logger = logging.getLogger("medradar")
router = APIRouter(prefix="/pharmacist", tags=["delivery notes"])

FIELD = "pages"
MAX_PAGES = 5
MAX_PAGE_BYTES = 8 * 1024 * 1024
MAX_SIDE = 2000
MAX_REQUEST_BYTES = MAX_PAGES * MAX_PAGE_BYTES + 256 * 1024
SCANS_PER_DAY = parse("20/day")

DISABLED = ("La lecture des bons de livraison n'est pas disponible. "
            "Mettez votre stock à jour à la main.")
NO_PAGES = "Ajoutez la photo du bon de livraison (champ « pages »)."
TOO_LARGE = "Photo trop lourde (8 Mo maximum par page). Prenez une photo plus légère."
TOO_MANY = "Cinq pages au maximum par bon."
NOT_A_NOTE = ("Ce document ne ressemble pas à un bon de livraison. "
              "Photographiez le bon reçu avec votre commande.")
SATURATED = "La lecture est momentanément saturée, réessayez dans une minute."
TIMEOUT = ("La lecture du bon a pris trop de temps. Réessayez avec une photo plus nette "
           "ou moins de pages.")
FAILED = ("Nous n'avons pas pu lire ce bon. Réessayez avec une photo plus nette, "
          "ou mettez votre stock à jour à la main.")
DAILY_LIMIT = ("Limite de 20 bons scannés par jour atteinte. Mettez votre stock à jour "
               "à la main ou réessayez demain.")
PHOTO_LIMIT = (f"Limite de {PHOTO_PAGES_PER_MONTH} pages de photos par mois atteinte : "
               "le bon peut être gardé, mais sans sa photo.")
SCAN_NOT_FOUND = "Analyse introuvable."
SCAN_EXPIRED = "Cette analyse a expiré (1 heure). Scannez le bon à nouveau."
ALREADY_CONFIRMED = "Ce bon a déjà été confirmé."
UNKNOWN_MEDICINE = "Médicament introuvable ou non vendu en pharmacie : {ids}"


class ScanFailed(Exception):
    """Sent as {"detail": message, "code": code} (handler in app/main.py)."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def prepare_pages(files: list[bytes]) -> list[bytes]:
    return [prepare_image(data, max_bytes=MAX_PAGE_BYTES, max_side=MAX_SIDE, too_large=TOO_LARGE)
            for data in files]


@router.post(
    "/delivery-scan",
    response_model=ScanResult,
    openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {
        "schema": {"type": "object", "required": [FIELD], "properties": {
            FIELD: {"type": "array", "maxItems": MAX_PAGES,
                    "items": {"type": "string", "format": "binary"},
                    "description": "1 to 5 pages: JPEG, PNG or WebP, 8 MB max each"}}}}}}},
)
async def scan(request: Request, pharmacy: Pharmacy = Depends(get_validated_pharmacy),
               user: User = Depends(require_pharmacist), db: Session = Depends(get_db)):
    """Read the note and propose a medicine for each line. NOTHING is declared here."""
    reader = request.app.state.delivery_reader
    if reader is None:
        raise ScanFailed(503, "desactivee", DISABLED)
    purge_expired_scans(db)
    if not limiter.limiter.hit(SCANS_PER_DAY, "delivery-scan", str(pharmacy.id)):
        raise ScanFailed(429, "limite", DAILY_LIMIT)

    try:
        files = await read_files(request, FIELD, MAX_PAGES, MAX_REQUEST_BYTES, missing=NO_PAGES,
                                 too_large=TOO_LARGE, too_many=TOO_MANY)
        pages = await run_in_threadpool(prepare_pages, files)
    except (UploadRejected, ImageRejected) as error:
        raise ScanFailed(error.status, error.code, error.message) from None
    finally:
        files = None  # the originals are not kept, even in memory

    started = utcnow()
    try:
        reading = await run_in_threadpool(read_note, reader, pages)
    except (QuotaExceeded, ProviderBusy) as error:
        logger.warning("Delivery scan: provider saturated (%s)", error)
        raise ScanFailed(503, "saturee", SATURATED) from None
    except LLMTimeout:
        logger.warning("Delivery scan: provider timeout")
        raise ScanFailed(504, "delai", TIMEOUT) from None
    except LLMError as error:
        logger.warning("Delivery scan failed: %s", error)
        raise ScanFailed(502, "echec", FAILED) from None

    if reading.document.type_document == "autre":
        raise ScanFailed(422, "pas_un_bon", NOT_A_NOTE)

    matcher = LineMatcher(request.app.state.store, request.app.state.index)
    lines, summary = analyse_lines(matcher, reading)
    photo_possible = can_keep_photos(db, pharmacy.id, len(pages))
    document = {
        "type_document": reading.document.type_document,
        "fournisseur": reading.document.fournisseur,
        "numero_bon": reading.document.numero_bon,
        "date_bon": reading.document.date_bon.isoformat() if reading.document.date_bon else None,
    }
    result = {"document": document, "lignes": lines, "resume": summary}

    scan_row = DeliveryScan(id=str(uuid.uuid4()), pharmacie_id=pharmacy.id, cree_par=user.id,
                            cree_le=started, expire_le=started + SCAN_LIFETIME,
                            resultat_json=json.dumps(result), photo_possible=photo_possible)
    if photo_possible:
        # Kept compressed for 1 hour, only in case the pharmacist chooses "keep the photo"
        archived = await run_in_threadpool(lambda: [compress_jpeg(p, PHOTO_MAX_BYTES) for p in pages])
        scan_row.pages = [DeliveryScanPage(page=i + 1, image=img) for i, img in enumerate(archived)]
    db.add(scan_row)
    db.commit()
    logger.info("Delivery scan: %d lines read, %d exact", summary["lignes_lues"], summary["exactes"])

    return {"scan_id": scan_row.id, "expire_le": scan_row.expire_le, **result,
            "photo_possible": photo_possible,
            "message_photo": None if photo_possible else PHOTO_LIMIT}


def _get_scan(db, scan_id: str, pharmacy: Pharmacy) -> DeliveryScan:
    scan_row = db.get(DeliveryScan, scan_id)
    # Another pharmacy's scan is "not found": its existence is not revealed
    if scan_row is None or scan_row.pharmacie_id != pharmacy.id:
        raise HTTPException(status_code=404, detail=SCAN_NOT_FOUND)
    if scan_row.confirme_le is not None:
        raise HTTPException(status_code=409, detail=ALREADY_CONFIRMED)
    if scan_row.expire_le < utcnow():
        db.delete(scan_row)
        db.commit()
        raise HTTPException(status_code=410, detail=SCAN_EXPIRED)
    return scan_row


@router.post("/delivery-scan/{scan_id}/confirm", response_model=ConfirmOut)
def confirm(request: Request, scan_id: str, data: ConfirmIn, background_tasks: BackgroundTasks,
            pharmacy: Pharmacy = Depends(get_validated_pharmacy),
            user: User = Depends(require_pharmacist), db: Session = Depends(get_db)):
    """Declare the lines the pharmacist kept, in one transaction, and keep the note
    in the history if asked. A scan is confirmed only once."""
    scan_row = _get_scan(db, scan_id, pharmacy)
    store = request.app.state.store
    unknown = sorted({line.medicament_id for line in data.lignes
                      if line.action != "ignoree" and store.get(line.medicament_id) is None})
    if unknown:
        raise HTTPException(status_code=422, detail=UNKNOWN_MEDICINE.format(ids=", ".join(unknown)))

    scanned = json.loads(scan_row.resultat_json)["lignes"]
    now = utcnow()

    # One declaration per medicine; "in stock" wins if a medicine is on two lines
    statuses = {}
    for line in data.lignes:
        if line.action in ("en_stock", "rupture"):
            if statuses.get(line.medicament_id) != "en_stock":
                statuses[line.medicament_id] = line.action

    keep_photo = data.garder_historique and data.garder_photo
    photo_message = None
    if keep_photo and not (scan_row.photo_possible and scan_row.pages
                           and can_keep_photos(db, pharmacy.id, len(scan_row.pages))):
        keep_photo, photo_message = False, PHOTO_LIMIT

    note = None
    if data.garder_historique:
        note = DeliveryNote(
            pharmacie_id=pharmacy.id, confirme_par=user.id, fournisseur=data.fournisseur,
            numero_bon=data.numero_bon, date_bon=data.date_bon, scanne_le=scan_row.cree_le,
            confirme_le=now, duree_secondes=int((now - scan_row.cree_le).total_seconds()),
            nb_lignes_lues=json.loads(scan_row.resultat_json)["resume"]["lignes_lues"],
            nb_mis_en_stock=sum(1 for s in statuses.values() if s == "en_stock"),
            nb_rupture=sum(1 for s in statuses.values() if s == "rupture"),
            nb_non_livres=sum(1 for line in scanned if line["correspondance"] == NOT_DELIVERED),
            nb_ignores=sum(1 for line in data.lignes if line.action == "ignoree"),
            photo_gardee=keep_photo)
        for line in data.lignes:
            # What MedRadar proposed for this line: the pharmacist "corrected" it when
            # the medicine or the action is not the one proposed
            proposed = scanned[line.ligne] if line.ligne is not None and line.ligne < len(scanned) else {}
            proposed_id = (proposed.get("medicament") or {}).get("id")
            proposed_action = "en_stock" if proposed.get("coche") else "ignoree"
            corrected = bool(proposed) and (line.medicament_id != proposed_id
                                            or line.action != proposed_action)
            note.lignes.append(DeliveryLine(
                designation_lue=line.designation_lue, medicament_id=line.medicament_id,
                quantite=line.quantite, numero_lot=line.numero_lot,
                date_peremption=line.date_peremption,
                statut_correspondance=proposed.get("correspondance", "a_verifier"),
                action=line.action, corrigee_par_pharmacien=corrected))
        if keep_photo:
            note.photos = [DeliveryPhoto(page=p.page, image=p.image, cree_le=now)
                           for p in scan_row.pages]
        db.add(note)
        db.flush()  # the note's id, for the declarations

    items = [SimpleNamespace(medicament_id=m, statut=s) for m, s in statuses.items()]
    if items:
        _declare(db, pharmacy, user, items, source=SOURCE_DELIVERY_SCAN,
                 bon_id=note.id if note else None, commit=False)

    # The scan's content is erased at once; the empty row only says "confirmed"
    scan_row.confirme_le = now
    scan_row.resultat_json = "{}"
    scan_row.pages = []
    db.commit()
    notify_alerts(request, background_tasks, pharmacy, items)

    return {
        "nb_en_stock": sum(1 for s in statuses.values() if s == "en_stock"),
        "nb_rupture": sum(1 for s in statuses.values() if s == "rupture"),
        "duree_secondes": int((now - scan_row.cree_le).total_seconds()),
        "bon_id": note.id if note else None,
        "photo_gardee": keep_photo,
        "message_photo": photo_message,
    }
