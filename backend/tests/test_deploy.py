"""What the production deployment relies on: health checks, logs, proxy, headers."""

import logging

from starlette.requests import Request

from app.limiter import client_ip
from app.migrate import migrate


def request_with(headers, client=("10.0.0.1", 1234)):
    scope = {"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
             "client": client}
    return Request(scope)


def test_health_is_light_and_shows_no_secret(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["medicines"] > 4000
    assert set(body["features"]) == {"photo_recognition", "delivery_scan", "email_alerts",
                                     "multilingual_search"}
    assert "key" not in str(body).lower()


def test_deep_health_checks_the_database(client):
    response = client.get("/health/deep")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_client_ip_is_the_first_forwarded_address():
    assert client_ip(request_with({"X-Forwarded-For": "41.100.1.2, 10.1.2.3"})) == "41.100.1.2"
    assert client_ip(request_with({})) == "10.0.0.1"


def test_login_limit_is_per_forwarded_ip(client):
    def attempt(ip):
        return client.post("/auth/login", headers={"X-Forwarded-For": ip},
                           json={"email": "nobody@example.com", "mot_de_passe": "Wrong2026x"})
    codes = [attempt("41.100.1.2").status_code for _ in range(6)]
    assert codes[-1] == 429
    assert attempt("41.100.9.9").status_code == 401  # another patient is not blocked


def test_security_headers_and_hsts_behind_https(client):
    response = client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "max-age" in response.headers["Strict-Transport-Security"]


def test_access_log_has_the_route_but_never_the_query(client, caplog):
    logger = logging.getLogger("medradar.access")
    logger.addHandler(caplog.handler)
    try:
        client.get("/medicines/search", params={"q": "glucophage secret"})
    finally:
        logger.removeHandler(caplog.handler)
    lines = [r.getMessage() for r in caplog.records if r.name == "medradar.access"]
    assert any(line.startswith("GET /medicines/search 200 ") for line in lines)
    assert not any("secret" in line or "glucophage" in line for line in lines)


def test_admin_routes_are_not_in_the_public_docs(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(path.startswith("/admin") for path in paths)
    assert "/health/deep" in paths


def test_migrations_can_run_again(client):
    migrate()  # already up to date: does nothing, raises nothing
    migrate()


def test_cors_allows_every_frontend_url(monkeypatch):
    import importlib

    from app import config
    monkeypatch.setenv("FRONTEND_URL", "https://medradar.vercel.app/, https://www.medradar.dz")
    try:
        importlib.reload(config)
        assert config.FRONTEND_URLS == ["https://medradar.vercel.app", "https://www.medradar.dz"]
        assert config.FRONTEND_URL == "https://medradar.vercel.app"
    finally:
        monkeypatch.delenv("FRONTEND_URL")
        importlib.reload(config)


def test_no_migration_lock_through_the_neon_pooler(monkeypatch):
    from app import migrate as module

    monkeypatch.setattr(module, "is_sqlite", False)
    monkeypatch.setattr(module, "DATABASE_URL",
                        "postgresql+psycopg://u:p@ep-x-pooler.eu-central-1.aws.neon.tech/db")
    assert module._can_lock() is False
    monkeypatch.setattr(module, "DATABASE_URL",
                        "postgresql+psycopg://u:p@ep-x.eu-central-1.aws.neon.tech/db")
    assert module._can_lock() is True


def test_uptime_monitors_can_check_health_with_head(client):
    response = client.head("/health")
    assert response.status_code == 200
    assert response.content == b""
