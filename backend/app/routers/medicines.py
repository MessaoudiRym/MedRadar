"""Medicine search and equivalents (data from the official nomenclature)."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import Equivalents, Health, Medicine, SearchResult, SmartSearchResult

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
    return {"status": "ok", "medicines": len(request.app.state.store)}


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
    return smart.search(q, limit, db, get_remote_address(request),
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
