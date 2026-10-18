from tests.conftest import PASSWORD, auth, login, register_pharmacist, registration

from app.routers.auth import BAD_CREDENTIALS, REGISTERED


def test_valid_registration_creates_pending_pharmacy(client):
    response = client.post("/auth/register-pharmacist", json=registration())
    assert response.status_code == 201
    body = response.json()
    assert body["message"] == REGISTERED
    assert body["pharmacie"]["statut"] == "en_attente"
    assert body["pharmacie"]["telephone"] == "041234567"  # normalized


def test_password_is_never_returned_or_stored_in_clear(client):
    data = registration()
    response = client.post("/auth/register-pharmacist", json=data)
    assert PASSWORD not in response.text
    me = client.get("/auth/me", headers=login(client, data["email"]))
    assert PASSWORD not in me.text and "mot_de_passe" not in me.text and "hash" not in me.text


def test_email_already_taken_returns_409(client):
    data = registration()
    assert client.post("/auth/register-pharmacist", json=data).status_code == 201
    again = registration(email=data["email"].upper())  # same email, other case
    assert client.post("/auth/register-pharmacist", json=again).status_code == 409


def test_weak_passwords_return_422(client):
    for weak in ["court1", "sanschiffre", "12345678"]:
        response = client.post("/auth/register-pharmacist", json=registration(mot_de_passe=weak))
        assert response.status_code == 422, weak
        assert weak not in response.text  # values sent are never echoed back


def test_invalid_phones_return_422(client):
    for phone in ["0812345678", "05501234", "12345", "0550 12 34 5x"]:
        response = client.post("/auth/register-pharmacist", json=registration(telephone=phone))
        assert response.status_code == 422, phone


def test_valid_phone_formats_are_accepted(client):
    for phone in ["0661234567", "+213 770 12 34 56", "041-23-45-67"]:
        response = client.post("/auth/register-pharmacist", json=registration(telephone=phone))
        assert response.status_code == 201, phone


def test_coordinates_outside_algeria_return_422(client):
    paris = {"latitude": 48.85, "longitude": 2.35}
    response = client.post("/auth/register-pharmacist", json=registration(pharmacie=paris))
    assert response.status_code == 422


def test_empty_required_field_returns_422(client):
    response = client.post("/auth/register-pharmacist", json=registration(nom="   "))
    assert response.status_code == 422


def test_cannot_register_as_admin(client):
    response = client.post("/auth/register-pharmacist", json=registration(role="admin"))
    assert response.status_code == 422  # unknown fields are refused


def test_login_returns_token_and_role(client):
    data = registration()
    client.post("/auth/register-pharmacist", json=data)
    response = client.post("/auth/login", json={"email": data["email"], "mot_de_passe": PASSWORD})
    assert response.status_code == 200
    assert response.json()["role"] == "pharmacien"
    assert response.json()["expires_in"] == 7 * 24 * 3600


def test_wrong_password_and_unknown_email_give_the_same_401(client):
    data = registration()
    client.post("/auth/register-pharmacist", json=data)
    wrong_password = client.post("/auth/login",
                                 json={"email": data["email"], "mot_de_passe": "Mauvais123"})
    unknown_email = client.post("/auth/login",
                                json={"email": "inconnu@example.com", "mot_de_passe": PASSWORD})
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json() == {"detail": BAD_CREDENTIALS}


def test_login_is_limited_to_5_attempts_per_minute(client):
    codes = [client.post("/auth/login", json={"email": "x@example.com", "mot_de_passe": "Abcdef12"})
             .status_code for _ in range(6)]
    assert codes == [401] * 5 + [429]


def test_me_shows_pharmacy_status(client):
    headers, _, email = register_pharmacist(client)
    body = client.get("/auth/me", headers=headers).json()
    assert body["utilisateur"]["email"] == email
    assert body["pharmacie"]["statut"] == "en_attente"


def test_no_token_returns_401(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/admin/pharmacies").status_code == 401


def test_invalid_token_returns_401(client):
    for token in ["abc", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature-fausse"]:
        assert client.get("/auth/me", headers=auth(token)).status_code == 401


def test_token_signed_with_another_secret_returns_401(client):
    import jwt
    forged = jwt.encode({"sub": "1", "role": "admin", "iat": 0, "exp": 4_000_000_000},
                        "another-secret-" + "y" * 40, algorithm="HS256")
    assert client.get("/admin/pharmacies", headers=auth(forged)).status_code == 401


def test_change_password(client):
    headers, _, email = register_pharmacist(client)
    wrong = client.post("/auth/change-password", headers=headers,
                        json={"ancien_mot_de_passe": "Faux1234", "nouveau_mot_de_passe": "Nouveau2026"})
    assert wrong.status_code == 400
    ok = client.post("/auth/change-password", headers=headers,
                     json={"ancien_mot_de_passe": PASSWORD, "nouveau_mot_de_passe": "Nouveau2026"})
    assert ok.status_code == 200
    login(client, email, "Nouveau2026")
    old = client.post("/auth/login", json={"email": email, "mot_de_passe": PASSWORD})
    assert old.status_code == 401
