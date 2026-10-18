import pytest
from fastapi.testclient import TestClient

from app.main import NOTICE, app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # "with" runs the startup that loads the CSV
        yield c


def find_id(client, brand, dosage):
    results = client.get("/medicines/search", params={"q": brand, "limit": 50}).json()
    for r in results:
        if r["nom_marque"] == brand and r["dosage_norm"] == dosage:
            return r["id"]
    raise AssertionError(f"{brand} {dosage} not found")


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["medicines"] > 4000


def test_search_with_typo_finds_glucophage(client):
    results = client.get("/medicines/search", params={"q": "glucofage"}).json()
    top3 = [r["nom_marque"] for r in results[:3]]
    assert any(name.startswith("GLUCOPHAGE") for name in top3)


def test_search_by_molecule(client):
    results = client.get("/medicines/search", params={"q": "metformine"}).json()
    assert results
    assert all("METFORMINE" in r["molecule"] for r in results)


def test_search_amlodipine_returns_at_least_5(client):
    results = client.get("/medicines/search", params={"q": "amlodipine"}).json()
    assert len(results) >= 5


def test_search_result_fields(client):
    result = client.get("/medicines/search", params={"q": "tahor"}).json()[0]
    assert set(result) == {"id", "nom_marque", "molecule", "dosage_norm",
                           "forme_groupe", "nb_equivalents"}


def test_glucophage_850_has_13_equivalents(client):
    medicine_id = find_id(client, "GLUCOPHAGE 850", "850MG")
    body = client.get(f"/medicines/{medicine_id}/equivalents").json()
    assert body["count"] == 13
    assert len(body["equivalents"]) == 13
    names = [e["nom_marque"] for e in body["equivalents"]]
    assert len(names) == len(set(names))  # one result per brand name
    assert "GLUCOPHAGE 850" not in names
    assert body["notice"] == NOTICE


def test_diamicron_60_has_no_equivalent(client):
    medicine_id = find_id(client, "DIAMICRON", "60MG")
    body = client.get(f"/medicines/{medicine_id}/equivalents").json()
    assert body["medicine"]["forme_groupe"] == "comprimé — libération modifiée"
    assert body["count"] == 0


def test_medicine_detail(client):
    medicine_id = find_id(client, "GLUCOPHAGE 850", "850MG")
    body = client.get(f"/medicines/{medicine_id}").json()
    assert body["nom_marque"] == "GLUCOPHAGE 850"
    assert body["disponible_officine"] is True


def test_unknown_id_returns_404(client):
    assert client.get("/medicines/999999").status_code == 404
    assert client.get("/medicines/999999/equivalents").status_code == 404


def test_one_character_query_returns_422(client):
    assert client.get("/medicines/search", params={"q": "a"}).status_code == 422


def test_unverified_dose_is_flagged(client):
    medicine = next(m for m in client.app.state.store.records
                    if not m["dosage_verifie"] and m["dosage_norm"])
    body = client.get(f"/medicines/{medicine['id']}/equivalents").json()
    assert body["dosage_verifie"] is False
