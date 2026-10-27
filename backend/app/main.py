"""MedRadar API: medicines, equivalents, pharmacies and stock.

Run from the backend/ folder:
    uvicorn app.main:app --reload
"""

import asyncio
import logging
import subprocess
import sys
import time
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from .config import APP_VERSION, ARABIC_SEARCH_MODE, FRONTEND_URLS, PROJECT_ROOT, jwt_secret
from .data import load_store
from .limiter import limiter
from .mail import make_mailer
from .migrate import migrate
from .delivery import make_delivery_reader
from .delivery.history import CLEANUP_EVERY, run_cleanup
from .routers import admin, auth, deliveries, delivery, medicines, pharmacist, public, recognition
from .routers.delivery import ScanFailed
from .routers.recognition import RecognitionFailed
from .llm import make_interpreter
from .search import SearchIndex
from .smart_search import SmartSearch
from .transliteration import PhoneticIndex
from .vision import make_reader

logger = logging.getLogger("medradar")
if not logger.handlers:
    # Visible in the Render logs (stdout), one line per message
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


class HideQueryStrings(logging.Filter):
    """Access logs keep the path, never the parameters: searches (q=...) and
    positions (lat=, lng=) are personal and are not written in the logs."""

    def filter(self, record):
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str) and "?" in args[2]:
            record.args = (*args[:2], args[2].split("?", 1)[0] + "?…", *args[3:])
        return True


logging.getLogger("uvicorn.access").addFilter(HideQueryStrings())
access_logger = logger.getChild("access")


@asynccontextmanager
async def lifespan(app: FastAPI):
    jwt_secret()  # refuse to start without a proper secret
    migrate()  # no pre-deploy command on the free plan: the API migrates itself
    app.state.version = APP_VERSION or git_version()
    store = load_store()  # read the CSV once, kept in memory
    app.state.store = store
    app.state.index = SearchIndex(store.records)
    app.state.smart_search = SmartSearch(store, app.state.index, PhoneticIndex(app.state.index))
    app.state.interpreter = make_interpreter()  # None: the search uses rules only
    app.state.search_mode = ARABIC_SEARCH_MODE
    app.state.reader = make_reader()  # None: photo recognition is off
    app.state.delivery_reader = make_delivery_reader()  # None: delivery note scan is off
    app.state.mailer = make_mailer()  # None: alert emails are off
    cleanup = asyncio.create_task(clean_every_day())  # expired scans, old history
    yield
    cleanup.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup


def git_version():
    """Short git hash, when git and the repository are there (else None)."""
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT,
                                capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


async def clean_every_day():
    """Delivery notes: unconfirmed scans, then photos and notes past their retention."""
    while True:
        try:
            await run_in_threadpool(run_cleanup)
        except Exception:
            logger.exception("Delivery cleanup failed")
        await asyncio.sleep(CLEANUP_EVERY.total_seconds())


app = FastAPI(
    title="MedRadar API",
    description="Find registered equivalents of an out-of-stock medicine, "
                "from the Algerian national nomenclature, and pharmacies that have it.",
    version="0.4.0",
    lifespan=lifespan,
)
app.state.limiter = limiter

origins = ["http://localhost:3000", *FRONTEND_URLS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Opener-Policy": "same-origin",
}


@app.middleware("http")
async def log_and_secure(request: Request, call_next):
    """Security headers on every answer, and one log line per request: method,
    route, status and duration. The route is the template (/medicines/{medicine_id}),
    never the query string: no search text, no position, no email in the logs."""
    start = time.monotonic()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
    finally:
        route = request.scope.get("route")
        path = getattr(route, "path", None) or "(unknown route)"
        access_logger.info("%s %s %s %dms", request.method, path, status,
                           (time.monotonic() - start) * 1000)
    response.headers.update(SECURITY_HEADERS)
    if request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


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
    if request.url.path == "/medicines/recognize":
        return JSONResponse(status_code=429, content={
            "detail": "Limite de 10 photos par heure atteinte. Tapez le nom du médicament "
                      "ou réessayez plus tard.",
            "code": "limite"})
    return JSONResponse(status_code=429,
                        content={"detail": "Trop de tentatives. Réessayez dans une minute."})


@app.exception_handler(ScanFailed)
@app.exception_handler(RecognitionFailed)
async def recognition_failed(request: Request, exc: RecognitionFailed | ScanFailed):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "code": exc.code})


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    """Log the details on the server, send no technical trace to the client."""
    logger.exception("Unexpected error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur."})


for module in (medicines, recognition, public, auth, pharmacist, delivery, deliveries):
    app.include_router(module.router)
# Admin routes work as before, but are not listed in the public /docs
app.include_router(admin.router, include_in_schema=False)
