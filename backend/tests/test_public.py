from datetime import timedelta

from tests.conftest import find_medicine, register_pharmacist

from app.db import SessionLocal, utcnow
from app.models import Pharmacy, Search, StockDeclaration, TrackedMedicine
from app.routers.public import DEMO_MESSAGE

ORAN = {"lat": 35.697, "lng": -0.633}


def declare(client, headers, medicine_id, statut):
    response = client.post("/pharmacist/stock", headers=headers,
                           json={"medicament_id": medicine_id, "statut": statut})
    assert response.status_code == 201, response.text


def availability(client, medicine_id, **params):
    response = client.get(f"/medicines/{medicine_id}/availability", params=ORAN | params)
    assert response.status_code == 200, response.text
    return response.json()


def requested(body):
    return next(g for g in body["resultats"] if g["est_demande"])


def test_pharmacies_contain_no_personal_data(client, validated_pharmacist):
    validated_pharmacist()
    pharmacies = client.get("/pharmacies").json()
    assert len(pharmacies) == 1
    for field in ("email", "numero_professionnel", "proprietaire", "professional_number",
                  "owner_id"):
        assert field not in pharmacies[0]
    assert "@" not in client.get("/pharmacies").text


def test_rupture_replaces_previous_in_stock(client, store, validated_pharmacist):
    headers, pharmacy_id = validated_pharmacist()
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    declare(client, headers, medicine["id"], "en_stock")
    assert [p["id"] for p in requested(availability(client, medicine["id"]))["en_stock"]] == [pharmacy_id]

    declare(client, headers, medicine["id"], "rupture")
    group = requested(availability(client, medicine["id"]))
    assert group["en_stock"] == []
    assert [p["id"] for p in group["rupture"]] == [pharmacy_id]


def test_sorted_by_distance(client, store, validated_pharmacist):
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    # Created far to near, to be sure the order comes from the sort
    for lat in (35.75, 35.72, 35.70):
        headers, _ = validated_pharmacist(pharmacie={"latitude": lat, "longitude": -0.633})
        declare(client, headers, medicine["id"], "en_stock")
    distances = [p["distance_km"] for p in requested(availability(client, medicine["id"]))["en_stock"]]
    assert len(distances) == 3
    assert distances == sorted(distances)


def test_radius_filters_far_pharmacies(client, store, validated_pharmacist):
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    headers, _ = validated_pharmacist(pharmacie={"latitude": 36.75, "longitude": 3.06})  # Alger
    declare(client, headers, medicine["id"], "en_stock")
    assert requested(availability(client, medicine["id"], radius_km=10))["en_stock"] == []


def test_equivalents_in_stock_are_shown(client, store, validated_pharmacist):
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    equivalent = store.equivalents(medicine)[0]
    headers, _ = validated_pharmacist()
    declare(client, headers, equivalent["id"], "en_stock")
    body = availability(client, medicine["id"])
    assert body["nb_pharmacies_en_stock"] == 1
    other = next(g for g in body["resultats"] if not g["est_demande"])
    assert other["medicament"]["id"] == equivalent["id"]


def test_declaration_older_than_7_days_must_be_confirmed(client, store, validated_pharmacist):
    _, pharmacy_id = validated_pharmacist()
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    with SessionLocal() as db:
        db.add(TrackedMedicine(pharmacy_id=pharmacy_id, medicine_id=medicine["id"]))
        db.add(StockDeclaration(pharmacy_id=pharmacy_id, medicine_id=medicine["id"],
                                status="en_stock", declared_at=utcnow() - timedelta(days=8)))
        db.commit()
    entry = requested(availability(client, medicine["id"]))["en_stock"][0]
    assert entry["a_confirmer"] is True


def test_recent_declaration_does_not_need_confirmation(client, store, validated_pharmacist):
    headers, _ = validated_pharmacist()
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    declare(client, headers, medicine["id"], "en_stock")
    assert requested(availability(client, medicine["id"]))["en_stock"][0]["a_confirmer"] is False


def test_pending_pharmacy_is_never_shown(client, store):
    _, pharmacy_id, _ = register_pharmacist(client)
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    with SessionLocal() as db:  # even if a declaration exists in the database
        db.add(TrackedMedicine(pharmacy_id=pharmacy_id, medicine_id=medicine["id"]))
        db.add(StockDeclaration(pharmacy_id=pharmacy_id, medicine_id=medicine["id"],
                                status="en_stock"))
        db.commit()
    assert availability(client, medicine["id"])["nb_pharmacies_en_stock"] == 0


def test_demo_flag_and_anonymous_search_log(client, store, validated_pharmacist):
    headers, pharmacy_id = validated_pharmacist()
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    declare(client, headers, medicine["id"], "en_stock")
    assert availability(client, medicine["id"])["demo_data"] is False

    with SessionLocal() as db:
        db.get(Pharmacy, pharmacy_id).is_demo = True
        db.commit()
    body = availability(client, medicine["id"])
    assert body["demo_data"] is True and body["demo_message"] == DEMO_MESSAGE

    with SessionLocal() as db:
        searches = db.query(Search).all()
    assert len(searches) == 2
    assert {s.district for s in searches} == {"Centre-ville"}


def test_default_position_is_oran(client, store):
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    body = client.get(f"/medicines/{medicine['id']}/availability").json()
    assert (body["latitude"], body["longitude"]) == (35.697, -0.633)


def test_availability_of_unknown_medicine_returns_404(client):
    assert client.get("/medicines/000000000000/availability").status_code == 404


def test_alert(client, store):
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    response = client.post("/alerts", json={"email": "patient@example.com",
                                            "medicament_id": medicine["id"]})
    assert response.status_code == 201


def test_alert_with_invalid_email_returns_422(client, store):
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    response = client.post("/alerts", json={"email": "pas-un-email", "medicament_id": medicine["id"]})
    assert response.status_code == 422


def test_alert_for_unknown_medicine_returns_404(client):
    response = client.post("/alerts", json={"email": "patient@example.com",
                                            "medicament_id": "000000000000"})
    assert response.status_code == 404


def test_alerts_limited_to_5_per_email(client, store):
    medicines = store.records[:6]
    codes = [client.post("/alerts", json={"email": "patient@example.com",
                                          "medicament_id": m["id"]}).status_code
             for m in medicines]
    assert codes == [201] * 5 + [409]
