from tests.conftest import find_medicine, register_pharmacist


def test_pending_pharmacy_cannot_declare_stock(client, store):
    headers, _, _ = register_pharmacist(client)
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    response = client.post("/pharmacist/stock", headers=headers,
                           json={"medicament_id": medicine["id"], "statut": "en_stock"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Votre pharmacie est en cours de vérification."


def test_validated_pharmacy_declares_and_tracks(client, store, validated_pharmacist):
    headers, _ = validated_pharmacist()
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    response = client.post("/pharmacist/stock", headers=headers,
                           json={"medicament_id": medicine["id"], "statut": "en_stock"})
    assert response.status_code == 201
    tracked = client.get("/pharmacist/stock", headers=headers).json()
    assert [t["medicament"]["id"] for t in tracked] == [medicine["id"]]
    assert tracked[0]["statut"] == "en_stock"


def test_unknown_medicine_returns_404(client, validated_pharmacist):
    headers, _ = validated_pharmacist()
    response = client.post("/pharmacist/stock", headers=headers,
                           json={"medicament_id": "000000000000", "statut": "en_stock"})
    assert response.status_code == 404


def test_pharmacist_cannot_choose_the_pharmacy(client, store, validated_pharmacist):
    """There is no pharmacy field: sending one is refused, so nobody writes for another pharmacy."""
    headers_a, _ = validated_pharmacist()
    _, pharmacy_b = validated_pharmacist()
    medicine = find_medicine(store, "GLUCOPHAGE 850", "850MG")
    response = client.post("/pharmacist/stock", headers=headers_a, json={
        "medicament_id": medicine["id"], "statut": "rupture", "pharmacie_id": pharmacy_b})
    assert response.status_code == 422


def test_bulk_declaration(client, store, validated_pharmacist):
    headers, _ = validated_pharmacist()
    ids = [m["id"] for m in store.records[:3]]
    response = client.post("/pharmacist/stock/bulk", headers=headers, json={
        "declarations": [{"medicament_id": i, "statut": "en_stock"} for i in ids]})
    assert response.status_code == 201
    assert len(client.get("/pharmacist/stock", headers=headers).json()) == 3


def test_bulk_is_all_or_nothing_and_limited_to_50(client, store, validated_pharmacist):
    headers, _ = validated_pharmacist()
    bad = [{"medicament_id": store.records[0]["id"], "statut": "en_stock"},
           {"medicament_id": "000000000000", "statut": "en_stock"}]
    assert client.post("/pharmacist/stock/bulk", headers=headers,
                       json={"declarations": bad}).status_code == 404
    assert client.get("/pharmacist/stock", headers=headers).json() == []

    too_many = [{"medicament_id": m["id"], "statut": "en_stock"} for m in store.records[:51]]
    assert client.post("/pharmacist/stock/bulk", headers=headers,
                       json={"declarations": too_many}).status_code == 422


def test_untrack(client, store, validated_pharmacist):
    headers, _ = validated_pharmacist()
    medicine_id = store.records[0]["id"]
    client.post("/pharmacist/stock", headers=headers,
                json={"medicament_id": medicine_id, "statut": "en_stock"})
    assert client.delete(f"/pharmacist/tracked/{medicine_id}", headers=headers).status_code == 204
    assert client.get("/pharmacist/stock", headers=headers).json() == []
    assert client.delete(f"/pharmacist/tracked/{medicine_id}", headers=headers).status_code == 404


def test_moving_the_pharmacy_needs_a_new_check(client, validated_pharmacist):
    headers, _ = validated_pharmacist()
    phone_only = client.patch("/pharmacist/pharmacy", headers=headers,
                              json={"telephone": "0661 00 00 00", "horaires": "9h-18h"})
    assert phone_only.json()["statut"] == "validee"
    moved = client.patch("/pharmacist/pharmacy", headers=headers,
                         json={"adresse": "Nouvelle adresse, Oran"})
    assert moved.json()["statut"] == "en_attente"


def test_pharmacist_cannot_change_own_status(client):
    headers, _, _ = register_pharmacist(client)
    response = client.patch("/pharmacist/pharmacy", headers=headers, json={"statut": "validee"})
    assert response.status_code == 422
