"""Test setup: a temporary SQLite database, separate from the real one.

The environment variables are set BEFORE the app is imported, so the app
connects to the temporary database. Tables are created by the real Alembic
migrations, then emptied after each test.
"""

import itertools
import os
import shutil
import tempfile
from pathlib import Path

_TMP_DIR = tempfile.mkdtemp(prefix="medradar-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_TMP_DIR, 'test.db').as_posix()}"
os.environ["JWT_SECRET"] = "test-only-secret-" + "x" * 40
os.environ.pop("FRONTEND_URL", None)

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import DATABASE_URL  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.limiter import limiter  # noqa: E402
from app.models import ROLE_ADMIN, User  # noqa: E402
from app.security import hash_password, password_context  # noqa: E402

# bcrypt is slow on purpose (cost 12 by default); a low cost keeps the tests fast
password_context.update(bcrypt__rounds=4)

BACKEND = Path(__file__).resolve().parents[1]
PASSWORD = "Pharma2026x"
ADMIN_PASSWORD = "Admin2026x"
_counter = itertools.count(1)


@pytest.fixture(scope="session", autouse=True)
def database():
    # Safety: never run the tests (which empty the tables) on the real database
    assert Path(_TMP_DIR).as_posix() in DATABASE_URL
    config = Config(str(BACKEND / "alembic.ini"))
    config.attributes["configure_logger"] = False
    command.upgrade(config, "head")
    yield
    engine.dispose()
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


@pytest.fixture(scope="session")
def client(database):
    from app.main import app
    with TestClient(app) as c:  # "with" runs the startup that loads the CSV
        yield c


@pytest.fixture(autouse=True)
def clean_state():
    limiter.reset()
    yield
    with engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
    limiter.reset()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def registration(**overrides):
    """A valid registration; email and professional number are unique for each call."""
    n = next(_counter)
    pharmacy = {
        "nom": f"Pharmacie Test {n}",
        "adresse": f"{n} rue de Test",
        "commune": "Oran",
        "quartier": "Centre-ville",
        "latitude": 35.697,
        "longitude": -0.633,
        "telephone": "041 23 45 67",
        "numero_professionnel": f"PRO-{n:05d}",
        "horaires": "8h-20h",
    }
    pharmacy.update(overrides.pop("pharmacie", {}))
    data = {
        "email": f"pharmacien{n}@example.com",
        "mot_de_passe": PASSWORD,
        "nom": "Test",
        "prenom": "Pharmacien",
        "telephone": "0550 12 34 56",
        "pharmacie": pharmacy,
    }
    data.update(overrides)
    return data


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def login(client, email, password=PASSWORD):
    response = client.post("/auth/login", json={"email": email, "mot_de_passe": password})
    assert response.status_code == 200, response.text
    return auth(response.json()["access_token"])


def register_pharmacist(client, **overrides):
    """Register; returns (headers, pharmacy id, email)."""
    data = registration(**overrides)
    response = client.post("/auth/register-pharmacist", json=data)
    assert response.status_code == 201, response.text
    return login(client, data["email"]), response.json()["pharmacie"]["id"], data["email"]


@pytest.fixture
def admin_headers(client):
    with SessionLocal() as db:
        db.add(User(email="admin@example.com", password_hash=hash_password(ADMIN_PASSWORD),
                    last_name="Admin", first_name="Test", phone="", role=ROLE_ADMIN))
        db.commit()
    return login(client, "admin@example.com", ADMIN_PASSWORD)


@pytest.fixture
def validated_pharmacist(client, admin_headers):
    """A pharmacist whose pharmacy was approved: returns (headers, pharmacy id)."""
    def make(**overrides):
        headers, pharmacy_id, _ = register_pharmacist(client, **overrides)
        response = client.post(f"/admin/pharmacies/{pharmacy_id}/approve", headers=admin_headers)
        assert response.status_code == 200, response.text
        return headers, pharmacy_id
    return make


@pytest.fixture
def store(client):
    return client.app.state.store


def find_medicine(store, brand, dosage):
    return next(m for m in store.records if m["nom_marque"] == brand and m["dosage_norm"] == dosage)
