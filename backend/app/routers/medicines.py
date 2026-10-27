"""Medicine search and equivalents (data from the official nomenclature)."""

import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from ..limiter import client_ip
from ..schemas import DeepHealth, Equivalents, Health, Medicine, SearchResult, SmartSearchResult
from .recognition import enabled_features

router = APIRouter(tags=["medicines"])

NOTICE = (
    "Ces médicaments contiennent la même substance active, au même dosage et sous "
    "la même forme. Demandez toujours l'avis de votre pharmacien ou de votre "
    "médecin avant de changer de médicament."
)


def get_medicine_or_404(request: Request, medicine_id: str):
    medicine = request.app.state.store.get(medicine_id)
    if medicine is None:
        raise HTTPException(status_code=404, detail="Médicament introuvable.")
    return medicine


@router.get("/health", response_model=Health, tags=["health"])
def health(request: Request):
    """Very light (called every 5 minutes by the uptime monitor): memory only, no database."""
    return {"status": "ok", "medicines": len(request.app.state.store),
            "version": request.app.state.version, "features": enabled_features(request.app)}


@router.get("/health/deep", response_model=DeepHealth, tags=["health"],
            responses={503: {"model": DeepHealth}})
def deep_health():
    """Also checks the database (for the deployment checks, not for the uptime monitor:
    it would keep the free database awake)."""
    start = time.monotonic()
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={
            "status": "error", "database": "unreachable", "database_ms": None})
    return {"status": "ok", "database": "ok",
            "database_ms": round((time.monotonic() - start) * 1000)}


@router.get("/medicines/search", response_model=list[SearchResult] | SmartSearchResult)
def search_medicines(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100,
                   description="Brand name or active substance, in French, Arabic, Darija, "
                               "arabizi or English"),
    limit: int = Query(10, ge=1, le=50),
    interpret: bool = Query(False, description="false while typing (a list, never the language "
                                               "model); true when the patient validates the search "
                                               "(results with how the query was understood)"),
    db: Session = Depends(get_db),
):
    smart = request.app.state.smart_search
    if not interpret:
        return smart.suggest(q, limit)
    return smart.search(q, limit, db, client_ip(request),
                        request.app.state.interpreter, request.app.state.search_mode)


@router.get("/medicines/{medicine_id}", response_model=Medicine)
def get_medicine(request: Request, medicine_id: str):
    return get_medicine_or_404(request, medicine_id)


@router.get("/medicines/{medicine_id}/equivalents", response_model=Equivalents)
def get_equivalents(request: Request, medicine_id: str):
    medicine = get_medicine_or_404(request, medicine_id)
    equivalents = request.app.state.store.equivalents(medicine)
    return {
        "medicine": medicine,
        "dosage_verifie": medicine["dosage_verifie"],
        "count": len(equivalents),
        "equivalents": equivalents,
        "notice": NOTICE,
    }
