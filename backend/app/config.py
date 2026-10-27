"""Settings, read from environment variables (or from the .env file at the project root).

Secrets are never written in the code: see .env.example.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Variables already set in the environment win over the .env file
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _database_url():
    url = os.environ.get("DATABASE_URL", "sqlite:///backend/medradar.db")
    # A relative SQLite path is relative to the project root, whatever the current folder
    prefix = "sqlite:///"
    if url.startswith(prefix) and not Path(url[len(prefix):]).is_absolute():
        url = prefix + (PROJECT_ROOT / url[len(prefix):]).as_posix()
    return url


DATABASE_URL = _database_url()
MEDICINES_CSV = Path(os.environ.get(
    "MEDICINES_CSV", PROJECT_ROOT / "data" / "clean" / "medicaments.csv"))
FRONTEND_URL = os.environ.get("FRONTEND_URL", "").rstrip("/")

# Photo recognition: a vision model reads the medicine box.
# Without LLM_API_KEY the feature is off and the rest of the API works normally.
# "fake" is for the tests and the end-to-end demo only: no network call.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").strip().lower()
LLM_API_KEY = os.environ.get("LLM_API_KEY", "").strip()
# Free tier Flash model (Pro models are paid only): https://ai.google.dev/gemini-api/docs/models
LLM_MODEL = os.environ.get("LLM_MODEL", "").strip() or "gemini-3.8-flash"
# Tried once when the main model is overloaded (503); "none" to turn it off
LLM_FALLBACK_MODEL = os.environ.get("LLM_FALLBACK_MODEL", "").strip() or "gemini-3.5-flash-lite"
if LLM_FALLBACK_MODEL.lower() == "none":
    LLM_FALLBACK_MODEL = ""
LLM_TIMEOUT_SECONDS = 30
# Model that understands search queries. A Flash-Lite model by default: answers in
# about 1 s, and the free tier of gemini-3.8-flash only allows 20 requests a day
# (measured October 2026), far too few for a search box. LLM_MODEL is its fallback.
LLM_SEARCH_MODEL = os.environ.get("LLM_SEARCH_MODEL", "").strip() or "gemini-3.5-flash-lite"

# Delivery note scan (pharmacists): reading time limit of the model, and how long the
# history kept by a pharmacist lasts (photos are deleted first, then the notes)
DELIVERY_TIMEOUT_SECONDS = 60
HISTORY_PHOTO_RETENTION_DAYS = int(os.environ.get("HISTORY_PHOTO_RETENTION_DAYS", "") or 90)
HISTORY_RETENTION_MONTHS = int(os.environ.get("HISTORY_RETENTION_MONTHS", "") or 24)

# Multilingual search: when the language model helps to understand a query.
#   llm_first:   queries in Arabic, Darija, arabizi or English, and unsure French queries
#   rules_first: only when the normal search and the transliteration rules are unsure
ARABIC_SEARCH_MODES = ("llm_first", "rules_first")
ARABIC_SEARCH_MODE = os.environ.get("ARABIC_SEARCH_MODE", "").strip().lower() or "llm_first"
if ARABIC_SEARCH_MODE not in ARABIC_SEARCH_MODES:
    raise RuntimeError(f"ARABIC_SEARCH_MODE must be one of: {', '.join(ARABIC_SEARCH_MODES)}")

# Alert emails, sent with the Brevo API (free plan: 300 emails a day). Without
# EMAIL_API_KEY no email is sent and the app hides the alert form.
# "fake" is for the tests and the end-to-end demo only: emails are kept in memory.
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "brevo").strip().lower() or "brevo"
EMAIL_API_KEY = os.environ.get("EMAIL_API_KEY", "").strip()
# The sender, verified in the Brevo account (Senders, domains & dedicated IPs)
EMAIL_FROM = os.environ.get("EMAIL_FROM", "").strip()
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "").strip() or "MedRadar"
EMAIL_TIMEOUT_SECONDS = 15

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 7
JWT_MIN_SECRET_LENGTH = 32


def jwt_secret():
    """The key that signs tokens. Required: the API refuses to start without it."""
    secret = os.environ.get("JWT_SECRET", "")
    if len(secret) < JWT_MIN_SECRET_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET must be set and at least {JWT_MIN_SECRET_LENGTH} characters long. "
            'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"')
    return secret
