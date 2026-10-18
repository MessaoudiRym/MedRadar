from tests.conftest import register_pharmacist


def test_admin_lists_pending_pharmacies(client, admin_headers):
    _, pharmacy_id, email = register_pharmacist(client)
    body = client.get("/admin/pharmacies", params={"statut": "en_attente"},
                      headers=admin_headers).json()
    assert [p["id"] for p in body] == [pharmacy_id]
    assert body[0]["proprietaire"]["email"] == email
    assert body[0]["numero_professionnel"]


def test_reject_and_suspend_need_a_reason(client, admin_headers):
    _, pharmacy_id, _ = register_pharmacist(client)
    url = f"/admin/pharmacies/{pharmacy_id}"
    assert client.post(f"{url}/reject", json={}, headers=admin_headers).status_code == 422
    rejected = client.post(f"{url}/reject", json={"motif": "Numéro professionnel introuvable"},
                           headers=admin_headers)
    assert rejected.json()["statut"] == "refusee"
    assert rejected.json()["motif"] == "Numéro professionnel introuvable"


def test_pharmacist_cannot_call_admin_routes(client):
    headers, pharmacy_id, _ = register_pharmacist(client)
    assert client.get("/admin/pharmacies", headers=headers).status_code == 403
    response = client.post(f"/admin/pharmacies/{pharmacy_id}/approve", headers=headers)
    assert response.status_code == 403
    me = client.get("/auth/me", headers=headers).json()
    assert me["utilisateur"]["role"] == "pharmacien"
    assert me["pharmacie"]["statut"] == "en_attente"


def test_unknown_pharmacy_returns_404(client, admin_headers):
    assert client.post("/admin/pharmacies/999999/approve",
                       headers=admin_headers).status_code == 404
