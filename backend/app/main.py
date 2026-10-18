"""MedRadar API: search a medicine and get its registered equivalents.

Run from the backend/ folder:
    uvicorn app.main:app --reload
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .data import load_store
from .schemas import Equivalents, Health, Medicine, SearchResult
from .search import SearchIndex

NOTICE = (
    "Ces médicaments contiennent la même substance active, au même dosage et sous "
    "la même forme. Demandez toujours l'avis de votre pharmacien ou de votre "
    "médecin avant de changer de médicament."
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = load_store()  # read the CSV once, kept in memory
    app.state.store = store
    app.state.index = SearchIndex(store.records)
    yield


app = FastAPI(
    title="MedRadar API",
    description="Find registered equivalents of an out-of-stock medicine, "
                "from the Algerian national nomenclature.",
    version="0.1.0",
    lifespan=lifespan,
)

origins = ["http://localhost:3000"]
if os.environ.get("FRONTEND_URL"):
    origins.append(os.environ["FRONTEND_URL"].rstrip("/"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_medicine_or_404(request: Request, medicine_id: int):
    medicine = request.app.state.store.get(medicine_id)
    if medicine is None:
        raise HTTPException(status_code=404, detail="Medicine not found")
    return medicine


@app.get("/health", response_model=Health)
def health(request: Request):
    return {"status": "ok", "medicines": len(request.app.state.store)}


@app.get("/medicines/search", response_model=list[SearchResult])
def search_medicines(
    request: Request,
    q: str = Query(..., min_length=2, description="Brand name or active substance"),
    limit: int = Query(10, ge=1, le=50),
):
    return request.app.state.index.search(q, limit)


@app.get("/medicines/{medicine_id}", response_model=Medicine)
def get_medicine(request: Request, medicine_id: int):
    return get_medicine_or_404(request, medicine_id)


@app.get("/medicines/{medicine_id}/equivalents", response_model=Equivalents)
def get_equivalents(request: Request, medicine_id: int):
    medicine = get_medicine_or_404(request, medicine_id)
    equivalents = request.app.state.store.equivalents(medicine)
    return {
        "medicine": medicine,
        "dosage_verifie": medicine["dosage_verifie"],
        "count": len(equivalents),
        "equivalents": equivalents,
        "notice": NOTICE,
    }
