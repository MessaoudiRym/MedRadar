"""Medicine search and equivalents (data from the official nomenclature)."""

from fastapi import APIRouter, HTTPException, Query, Request

from ..schemas import Equivalents, Health, Medicine, SearchResult

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


@router.get("/medicines/search", response_model=list[SearchResult])
def search_medicines(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100, description="Brand name or active substance"),
    limit: int = Query(10, ge=1, le=50),
):
    return request.app.state.index.search(q, limit)


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
