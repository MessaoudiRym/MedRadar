"""MedRadar API: medicines, equivalents, pharmacies and stock.

Run from the backend/ folder:
    uvicorn app.main:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .config import FRONTEND_URL, jwt_secret
from .data import load_store
from .limiter import limiter
from .routers import admin, auth, medicines, pharmacist
from .search import SearchIndex

logger = logging.getLogger("medradar")


@asynccontextmanager
async def lifespan(app: FastAPI):
    jwt_secret()  # refuse to start without a proper secret
    store = load_store()  # read the CSV once, kept in memory
    app.state.store = store
    app.state.index = SearchIndex(store.records)
    yield


app = FastAPI(
    title="MedRadar API",
    description="Find registered equivalents of an out-of-stock medicine, "
                "from the Algerian national nomenclature, and pharmacies that have it.",
    version="0.2.0",
    lifespan=lifespan,
)
app.state.limiter = limiter

origins = ["http://localhost:3000"]
if FRONTEND_URL:
    origins.append(FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    """Invalid request: say which field and why, but never echo the values sent
    (they can contain a password)."""
    errors = [{
        "loc": list(err.get("loc", [])),
        "msg": err.get("msg", "").removeprefix("Value error, "),
        "type": err.get("type", ""),
    } for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(RateLimitExceeded)
async def rate_limited(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429,
                        content={"detail": "Trop de tentatives. Réessayez dans une minute."})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    """Log the details on the server, send no technical trace to the client."""
    logger.exception("Unexpected error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur."})


for module in (medicines, auth, pharmacist, admin):
    app.include_router(module.router)
