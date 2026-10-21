"""Recognize a medicine from a photo of its box.

The vision model reads the box, the nomenclature decides, the patient confirms.
The photo stays in memory for the time of the request: it is never written
to disk, to the database or to the logs.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from starlette.formparsers import MultiPartException, MultiPartParser

from ..db import get_db
from ..images import MAX_BYTES, TOO_LARGE, ImageRejected, prepare_image
from ..limiter import limiter
from ..models import RecognitionAttempt
from ..recognition import rank
from ..schemas import Features, RecognitionResult
from ..vision.base import BOX, QuotaExceeded, ReaderError, ReaderTimeout, read_box

logger = logging.getLogger("medradar")
router = APIRouter(tags=["photo recognition"])

FIELD = "photo"
# Room for the multipart headers around the file
MAX_REQUEST_BYTES = MAX_BYTES + 64 * 1024
RATE_LIMIT = "10/hour"

DISABLED = "La reconnaissance par photo n'est pas disponible. Tapez le nom du médicament."
NO_PHOTO = "Ajoutez une photo de la boîte (champ « photo »)."
PRESCRIPTION = ("Pour protéger vos données, photographiez la boîte du médicament, "
                "pas l'ordonnance.")
UNREADABLE = ("Nous n'arrivons pas à lire cette boîte. Essayez une photo plus nette, "
              "bien éclairée, ou tapez le nom.")
SATURATED = ("La lecture des photos est momentanément saturée. Tapez le nom du médicament "
             "ou réessayez dans une minute.")
TIMEOUT = ("La lecture de la photo a pris trop de temps. Réessayez ou tapez le nom "
           "du médicament.")
FAILED = "Nous n'avons pas pu lire cette photo. Réessayez ou tapez le nom du médicament."
NO_MATCH = ("Aucun médicament de la nomenclature ne correspond à ce que nous avons lu. "
            "Vérifiez le nom sur la boîte et tapez-le.")


class RecognitionFailed(Exception):
    """Sent as {"detail": message, "code": code}: the code lets the app show its own text."""

    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def save_attempt(db: Session, succeeded: bool):
    db.add(RecognitionAttempt(succeeded=succeeded))
    db.commit()


async def read_photo(request: Request) -> bytes:
    """The uploaded file, read in memory with a size limit.

    FastAPI's UploadFile would copy files over 1 MB to a temporary file on disk:
    the body is read here instead, and the parser is told to keep it in memory.
    """
    if not request.headers.get("content-type", "").startswith("multipart/form-data"):
        raise RecognitionFailed(400, "photo_manquante", NO_PHOTO)
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_REQUEST_BYTES:
        raise RecognitionFailed(413, "trop_lourde", TOO_LARGE)

    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > MAX_REQUEST_BYTES:
            raise RecognitionFailed(413, "trop_lourde", TOO_LARGE)

    async def stream():
        yield bytes(body)

    parser = MultiPartParser(request.headers, stream(), max_files=1, max_fields=5)
    parser.spool_max_size = MAX_REQUEST_BYTES  # never roll over to a file on disk
    try:
        form = await parser.parse()
    except MultiPartException:
        raise RecognitionFailed(400, "photo_manquante", NO_PHOTO) from None
    try:
        upload = form.get(FIELD)
        if upload is None or isinstance(upload, str):
            raise RecognitionFailed(400, "photo_manquante", NO_PHOTO)
        return await upload.read()
    finally:
        await form.close()


@router.get("/features", response_model=Features)
def features(request: Request):
    """What this server can do: the app hides the photo buttons when it is off."""
    return {"photo_recognition": request.app.state.reader is not None}


@router.post(
    "/medicines/recognize",
    response_model=RecognitionResult,
    openapi_extra={"requestBody": {"required": True, "content": {"multipart/form-data": {
        "schema": {"type": "object", "required": [FIELD], "properties": {
            FIELD: {"type": "string", "format": "binary",
                    "description": "Photo of the box: JPEG, PNG or WebP, 5 MB max"}}}}}}},
)
@limiter.limit(RATE_LIMIT)
async def recognize(request: Request, db: Session = Depends(get_db)):
    """Read a medicine box photo and propose at most 3 medicines of the nomenclature.

    The patient must confirm one: nothing is chosen for them.
    """
    reader = request.app.state.reader
    if reader is None:
        raise RecognitionFailed(503, "desactivee", DISABLED)

    data = await read_photo(request)
    try:
        image = await run_in_threadpool(prepare_image, data)
    except ImageRejected as error:
        raise RecognitionFailed(error.status, error.code, error.message) from None
    finally:
        del data

    try:
        reading = await run_in_threadpool(read_box, reader, image)
    except QuotaExceeded:
        logger.warning("Photo recognition: provider quota exceeded")
        save_attempt(db, False)
        raise RecognitionFailed(503, "saturee", SATURATED) from None
    except ReaderTimeout:
        logger.warning("Photo recognition: provider timeout")
        save_attempt(db, False)
        raise RecognitionFailed(504, "delai", TIMEOUT) from None
    except ReaderError as error:  # invalid answer twice, network, key refused
        logger.warning("Photo recognition failed: %s", error)
        save_attempt(db, False)
        raise RecognitionFailed(502, "echec", FAILED) from None
    finally:
        del image

    # A prescription is never processed: nothing read on it is searched or returned
    if reading.type_image != BOX:
        save_attempt(db, False)
        if reading.type_image == "ordonnance":
            raise RecognitionFailed(422, "ordonnance", PRESCRIPTION)
        raise RecognitionFailed(422, "illisible", UNREADABLE)
    if not reading.lisible or not (reading.nom_marque or reading.dci):
        save_attempt(db, False)
        raise RecognitionFailed(422, "illisible", UNREADABLE)

    store, index = request.app.state.store, request.app.state.index
    best = rank(reading, store, index)
    save_attempt(db, bool(best))
    return {
        "texte_lu": reading.model_dump(include={"nom_marque", "dci", "dosage", "forme"}),
        "resultats": [{**medicine, "correspondance": level} for medicine, level in best],
        "message": None if best else NO_MATCH,
    }
