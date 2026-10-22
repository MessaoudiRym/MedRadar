"""Delivery note scan and history, with the simulated reader: no call to a real model."""

import csv
import io
import os
import sys
from datetime import timedelta
from io import BytesIO

import pytest
from PIL import Image
from sqlalchemy import func, inspect, select, text

from app.db import SessionLocal, engine, utcnow
from app.delivery.demo_note import NOTE_NUMBER, SUPPLIER
from app.delivery.history import PHOTO_PAGES_PER_MONTH, purge_expired_scans, purge_history
from app.llm.errors import LLMTimeout, QuotaExceeded
from app.models import (DeliveryLine, DeliveryNote, DeliveryPhoto, DeliveryScan, Pharmacy,
                        StockDeclaration, TrackedMedicine)
from app.routers import delivery
from tests.conftest import find_medicine, register_pharmacist

SCAN = "/pharmacist/delivery-scan"


def page(fmt="JPEG", size=(1200, 1600)):
    out = BytesIO()
    Image.new("RGB", size, "white").save(out, fmt)
    return out.getvalue()


def scan(client, headers, pages=None):
    pages = pages if pages is not None else [page()]
    return client.post(SCAN, headers=headers,
                       files=[("pages", (f"p{i}.jpg", data, "image/jpeg")) for i, data in enumerate(pages)])


def note(*lines, type_document="bon_de_livraison", **document):
    """A model answer: lines are (designation, quantity, status) or dicts."""
    rows = []
    for line in lines:
        if isinstance(line, tuple):
            designation, quantity, status = (line + (20, "livre"))[:3] if len(line) == 1 else (
                line if len(line) == 3 else (line[0], line[1], "livre"))
            line = {"designation": designation, "quantite_livree": quantity, "statut_ligne": status}
        rows.append({"nom_marque": None, "dosage": None, "forme": None, "numero_lot": None,
                     "date_peremption": None, "lisible": True, **line})
    return {"document": {"type_document": type_document, "fournisseur": "Grossiste Test",
                         "numero_bon": "BL-1", "date_bon": "2026-10-20",
                         "nombre_lignes_visibles": len(rows), **document},
            "lignes": rows}


def default_confirm(result, **options):
    """What the review screen sends when the pharmacist changes nothing."""
    lines = [{"ligne": line["index"], "designation_lue": line["designation"],
              "medicament_id": line["medicament"]["id"] if line["medicament"] else None,
              "quantite": line["quantite"], "numero_lot": line["numero_lot"],
              "date_peremption": line["date_peremption"],
              "action": "en_stock" if line["coche"] else "ignoree"} for line in result["lignes"]]
    return {"fournisseur": result["document"]["fournisseur"],
            "numero_bon": result["document"]["numero_bon"],
            "date_bon": result["document"]["date_bon"], "lignes": lines, **options}


def confirm(client, headers, result, **options):
    return client.post(f"{SCAN}/{result['scan_id']}/confirm", headers=headers,
                       json=default_confirm(result, **options))


def by_designation(result, designation):
    return next(line for line in result["lignes"] if line["designation"] == designation)


@pytest.fixture
def pharmacist(validated_pharmacist, fake_delivery_reader):
    """A validated pharmacist and the simulated reader (demo note by default)."""
    fake_delivery_reader()
    headers, pharmacy_id = validated_pharmacist()
    return headers, pharmacy_id


# --------------------------------------------------------------------------
# Reading and matching
# --------------------------------------------------------------------------

def test_demo_note_is_matched_and_exact_lines_are_ticked(client, pharmacist, store):
    headers, _ = pharmacist
    response = scan(client, headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["document"]["fournisseur"] == SUPPLIER
    assert result["document"]["numero_bon"] == NOTE_NUMBER
    assert result["resume"] == {"lignes_lues": 20, "exactes": 15, "a_verifier": 1,
                                "non_trouvees": 1, "non_livrees": 2, "regroupees": 1}
    for line in result["lignes"]:
        assert line["coche"] == (line["correspondance"] == "exacte")
    tegretol = by_designation(result, "TEGRETOL 200MG CP B/50")
    assert tegretol["medicament"]["id"] == find_medicine(store, "TEGRETOL", "200MG")["id"]
    kardegic = by_designation(result, "KARDEGIC 160MG SACH B/30")
    assert kardegic["medicament"]["forme_groupe"] == "poudre ou granulés oraux"


def test_wholesaler_abbreviation_finds_glucophage_850(client, pharmacist):
    headers, _ = pharmacist
    line = by_designation(scan(client, headers).json(), "GLUCOPH 850 CP B/30")
    assert line["correspondance"] == "exacte"
    assert line["medicament"]["nom_marque"] == "GLUCOPHAGE 850"
    assert line["medicament"]["dosage_norm"] == "850MG"
    assert line["medicament"]["forme_groupe"] == "comprimé"
    # The same medicine on two lines: one line, quantities added
    assert line["quantite"] == 30
    assert line["designations_regroupees"] == ["GLUCOPH 850 CP B/30"]


def test_the_dose_read_comes_first(client, pharmacist, fake_delivery_reader):
    headers, _ = pharmacist
    fake_delivery_reader(note(("GLUCOPHAGE 500MG CP B/30", 10, "livre")))
    line = scan(client, headers).json()["lignes"][0]
    assert line["medicament"]["nom_marque"] == "GLUCOPHAGE 500"
    assert line["candidats"][0]["dosage_norm"] == "500MG"


def test_line_without_dose_is_to_check_with_candidates(client, pharmacist):
    headers, _ = pharmacist
    line = by_designation(scan(client, headers).json(), "TAHOR CP B/30")
    assert line["correspondance"] == "a_verifier"
    assert line["coche"] is False
    assert {c["dosage_norm"] for c in line["candidats"]} == {"10MG", "20MG", "40MG"}


def test_back_order_is_not_delivered_and_never_ticked(client, pharmacist, store):
    headers, pharmacy_id = pharmacist
    result = scan(client, headers).json()
    line = by_designation(result, "LEVOTHYROX 75MCG CP B/30")
    assert line["correspondance"] == "non_livre"
    assert line["coche"] is False
    assert confirm(client, headers, result).status_code == 200
    levothyrox_75 = find_medicine(store, "LEVOTHYROX", "75MCG")["id"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StockDeclaration).where(
            StockDeclaration.medicine_id == levothyrox_75)) == 0


def test_parapharmacy_is_not_found(client, pharmacist):
    headers, _ = pharmacist
    line = by_designation(scan(client, headers).json(), "ECRAN SOLAIRE SPF50+ 50ML")
    assert line["correspondance"] == "non_trouve"
    assert line["medicament"] is None and line["coche"] is False


def test_a_name_that_does_not_exist_is_not_invented(client, pharmacist, fake_delivery_reader):
    headers, _ = pharmacist
    fake_delivery_reader(note({"designation": "ZORBAXIL 10MG CP B/30", "nom_marque": "ZORBAXIL",
                               "dosage": "10MG", "forme": "CP", "quantite_livree": 5,
                               "statut_ligne": "livre"}))
    line = scan(client, headers).json()["lignes"][0]
    assert line["correspondance"] == "non_trouve"
    assert line["medicament"] is None and line["candidats"] == []


def test_other_document_gets_a_clear_message(client, pharmacist, fake_delivery_reader):
    headers, _ = pharmacist
    fake_delivery_reader(note(type_document="autre"))
    response = scan(client, headers)
    assert response.status_code == 422
    assert response.json() == {"detail": delivery.NOT_A_NOTE, "code": "pas_un_bon"}


# --------------------------------------------------------------------------
# Nothing without confirmation
# --------------------------------------------------------------------------

def test_analysis_alone_declares_nothing(client, pharmacist):
    headers, pharmacy_id = pharmacist
    assert scan(client, headers).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(StockDeclaration).where(
            StockDeclaration.pharmacy_id == pharmacy_id)) == 0
        assert db.scalar(select(func.count()).select_from(DeliveryNote)) == 0


def test_confirm_declares_with_source_and_shows_to_patients(client, pharmacist, store):
    headers, pharmacy_id = pharmacist
    result = scan(client, headers).json()
    response = confirm(client, headers, result)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["nb_en_stock"] == 15 and body["nb_rupture"] == 0
    assert body["duree_secondes"] >= 0 and body["bon_id"] is not None
    with SessionLocal() as db:
        sources = set(db.scalars(select(StockDeclaration.source).where(
            StockDeclaration.pharmacy_id == pharmacy_id)))
    assert sources == {"scan_bl"}
    tegretol = find_medicine(store, "TEGRETOL", "200MG")["id"]
    availability = client.get(f"/medicines/{tegretol}/availability",
                              params={"lat": 35.697, "lng": -0.633}).json()
    in_stock = [p["id"] for r in availability["resultats"] for p in r["en_stock"]]
    assert pharmacy_id in in_stock


def test_keeping_the_history_links_declarations_to_the_note(client, pharmacist):
    headers, pharmacy_id = pharmacist
    result = scan(client, headers).json()
    bon_id = confirm(client, headers, result, garder_historique=True).json()["bon_id"]
    with SessionLocal() as db:
        stored = db.get(DeliveryNote, bon_id)
        assert stored.pharmacie_id == pharmacy_id
        assert stored.fournisseur == SUPPLIER and stored.nb_mis_en_stock == 15
        assert stored.nb_non_livres == 2 and stored.nb_ignores == 4
        assert len(stored.lignes) == 19
        links = set(db.scalars(select(StockDeclaration.bon_id).where(
            StockDeclaration.pharmacy_id == pharmacy_id)))
    assert links == {bon_id}


def test_without_history_nothing_of_the_note_is_kept(client, pharmacist):
    headers, pharmacy_id = pharmacist
    result = scan(client, headers).json()
    body = confirm(client, headers, result, garder_historique=False, garder_photo=True).json()
    assert body["bon_id"] is None and body["nb_en_stock"] == 15
    with SessionLocal() as db:
        for model in (DeliveryNote, DeliveryLine, DeliveryPhoto):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        declarations = db.scalars(select(StockDeclaration).where(
            StockDeclaration.pharmacy_id == pharmacy_id)).all()
        assert len(declarations) == 15 and all(d.bon_id is None for d in declarations)
        # The scan's content is erased at once
        assert db.scalar(select(DeliveryScan.resultat_json)) == "{}"


def test_photo_kept_only_when_asked_and_only_for_the_owner(client, pharmacist, validated_pharmacist):
    headers, _ = pharmacist
    result = scan(client, headers, [page(), page("PNG")]).json()
    bon_id = confirm(client, headers, result, garder_photo=True).json()["bon_id"]
    photo = client.get(f"/pharmacist/deliveries/{bon_id}/photos/2", headers=headers)
    assert photo.status_code == 200
    assert photo.headers["content-type"] == "image/jpeg"
    assert photo.headers["cache-control"] == "private, no-store"
    assert len(photo.content) <= 300 * 1024
    assert Image.open(BytesIO(photo.content)).format == "JPEG"

    other, _ = validated_pharmacist()
    assert client.get(f"/pharmacist/deliveries/{bon_id}/photos/2", headers=other).status_code == 404

    result = scan(client, headers).json()
    no_photo = confirm(client, headers, result, garder_photo=False).json()["bon_id"]
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(DeliveryPhoto).where(
            DeliveryPhoto.bon_id == no_photo)) == 0


def test_no_price_is_stored_anywhere(client, pharmacist, fake_delivery_reader):
    headers, _ = pharmacist
    fake_delivery_reader(note({"designation": "TEGRETOL 200MG CP B/50 7777,77 DA",
                               "quantite_livree": 6, "statut_ligne": "livre",
                               "prix_unitaire": 7777.77, "montant": 46666.62},
                              total_ttc=99999.99, tva=8888.88))
    result = scan(client, headers).json()
    assert "7777" not in str(result)
    assert confirm(client, headers, result, garder_photo=True).status_code == 200
    with engine.connect() as connection:
        for table in inspect(engine).get_table_names():
            columns = [c["name"] for c in inspect(engine).get_columns(table)]
            assert not any(word in c for c in columns for word in ("prix", "montant", "price", "tva"))
            for row in connection.execute(text(f'SELECT * FROM "{table}"')):
                values = " ".join(str(v) for v in row if not isinstance(v, bytes))
                for amount in ("7777", "46666", "99999", "8888"):
                    assert amount not in values, (table, values)


# --------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------

def keep_demo_note(client, headers, **options):
    result = scan(client, headers).json()
    return confirm(client, headers, result, **options).json()["bon_id"]


def test_when_did_i_receive(client, pharmacist):
    headers, _ = pharmacist
    bon_id = keep_demo_note(client, headers)
    found = client.get("/pharmacist/deliveries", headers=headers, params={"q": "glucophage 850"})
    assert [b["id"] for b in found.json()["bons"]] == [bon_id]
    assert client.get("/pharmacist/deliveries", headers=headers,
                      params={"q": "zzzqqq"}).json()["bons"] == []
    by_supplier = client.get("/pharmacist/deliveries", headers=headers,
                             params={"fournisseur": "démo ouest"}).json()
    assert by_supplier["total"] == 1


def test_detail_shows_every_line_and_corrections(client, pharmacist, store):
    headers, _ = pharmacist
    result = scan(client, headers).json()
    tahor = by_designation(result, "TAHOR CP B/30")
    tahor_20 = find_medicine(store, "TAHOR", "20MG")["id"]
    body = default_confirm(result)
    for line in body["lignes"]:
        if line["ligne"] == tahor["index"]:
            line.update(medicament_id=tahor_20, action="en_stock")  # chosen by the pharmacist
    bon_id = client.post(f"{SCAN}/{result['scan_id']}/confirm", headers=headers,
                         json=body).json()["bon_id"]
    detail = client.get(f"/pharmacist/deliveries/{bon_id}", headers=headers).json()
    lines = {line["designation_lue"]: line for line in detail["lignes"]}
    assert lines["TAHOR CP B/30"]["corrigee_par_pharmacien"] is True
    assert lines["TAHOR CP B/30"]["medicament"]["dosage_norm"] == "20MG"
    assert lines["TEGRETOL 200MG CP B/50"]["corrigee_par_pharmacien"] is False
    assert lines["ECRAN SOLAIRE SPF50+ 50ML"]["action"] == "ignoree"
    assert detail["annulable"] is True


def test_correct_the_note(client, pharmacist):
    headers, _ = pharmacist
    bon_id = keep_demo_note(client, headers)
    response = client.patch(f"/pharmacist/deliveries/{bon_id}", headers=headers,
                            json={"fournisseur": "Grossiste Démo Centre", "date_bon": "2026-10-19"})
    assert response.status_code == 200
    assert response.json()["fournisseur"] == "Grossiste Démo Centre"
    assert response.json()["numero_bon"] == NOTE_NUMBER


def test_another_pharmacy_sees_nothing_and_the_admin_no_content(client, pharmacist,
                                                                validated_pharmacist, admin_headers):
    headers, _ = pharmacist
    bon_id = keep_demo_note(client, headers, garder_photo=True)
    other, _ = validated_pharmacist()
    assert client.get("/pharmacist/deliveries", headers=other).json()["total"] == 0
    for method, path, kwargs in [
            ("get", f"/pharmacist/deliveries/{bon_id}", {}),
            ("patch", f"/pharmacist/deliveries/{bon_id}", {"json": {"fournisseur": "X"}}),
            ("delete", f"/pharmacist/deliveries/{bon_id}/photos", {}),
            ("delete", f"/pharmacist/deliveries/{bon_id}", {}),
            ("post", f"/pharmacist/deliveries/{bon_id}/cancel", {}),
            ("get", f"/pharmacist/deliveries/{bon_id}/photos/1", {})]:
        assert getattr(client, method)(path, headers=other, **kwargs).status_code == 404, path
    export = client.get("/pharmacist/deliveries/export", headers=other).text
    assert "TEGRETOL" not in export

    assert client.get("/pharmacist/deliveries", headers=admin_headers).status_code == 403
    assert client.get(f"/pharmacist/deliveries/{bon_id}", headers=admin_headers).status_code == 403
    stats = client.get("/admin/stats/deliveries", headers=admin_headers).json()
    assert stats == {"bons_gardes": 1, "lignes": 19, "pages_photos": 1, "pharmacies_utilisatrices": 1}


def declare(client, headers, medicine_id, status):
    response = client.post("/pharmacist/stock", headers=headers,
                           json={"medicament_id": medicine_id, "statut": status})
    assert response.status_code == 201


def status_of(client, headers, medicine_id):
    for item in client.get("/pharmacist/stock", headers=headers).json():
        if item["medicament"]["id"] == medicine_id:
            return item["statut"]
    return None  # not followed: "no information"


def test_cancel_puts_previous_statuses_back(client, pharmacist, store):
    headers, pharmacy_id = pharmacist
    tegretol = find_medicine(store, "TEGRETOL", "200MG")["id"]   # out of stock before
    cozzar = find_medicine(store, "COZZAR", "50MG")["id"]        # declared again after
    detensiel = find_medicine(store, "DETENSIEL", "10MG")["id"]  # never declared before
    declare(client, headers, tegretol, "rupture")
    bon_id = keep_demo_note(client, headers)
    assert status_of(client, headers, tegretol) == "en_stock"
    declare(client, headers, cozzar, "rupture")
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(StockDeclaration))

    response = client.post(f"/pharmacist/deliveries/{bon_id}/cancel", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert [m["medicament_id"] for m in body["laisses"]] == [cozzar]
    assert tegretol in [m["medicament_id"] for m in body["retablis"]]
    assert status_of(client, headers, tegretol) == "rupture"
    assert status_of(client, headers, cozzar) == "rupture"      # left as declared since
    assert status_of(client, headers, detensiel) is None       # back to "no information"
    with SessionLocal() as db:
        # Nothing deleted: the history only grows
        assert db.scalar(select(func.count()).select_from(StockDeclaration)) > before
        assert db.scalar(select(func.count()).select_from(StockDeclaration).where(
            StockDeclaration.bon_id == bon_id)) == 15

    listed = client.get("/pharmacist/deliveries", headers=headers).json()["bons"]
    assert listed[0]["id"] == bon_id and listed[0]["annule_le"] is not None
    assert client.post(f"/pharmacist/deliveries/{bon_id}/cancel", headers=headers).status_code == 409


def test_cancel_after_24_hours_is_refused(client, pharmacist):
    headers, _ = pharmacist
    bon_id = keep_demo_note(client, headers)
    with SessionLocal() as db:
        db.get(DeliveryNote, bon_id).confirme_le = utcnow() - timedelta(hours=25)
        db.commit()
    response = client.post(f"/pharmacist/deliveries/{bon_id}/cancel", headers=headers)
    assert response.status_code == 409
    assert "24 heures" in response.json()["detail"]


def test_delete_note_keeps_declarations(client, pharmacist):
    headers, pharmacy_id = pharmacist
    bon_id = keep_demo_note(client, headers, garder_photo=True)
    assert client.delete(f"/pharmacist/deliveries/{bon_id}/photos", headers=headers).status_code == 204
    detail = client.get(f"/pharmacist/deliveries/{bon_id}", headers=headers).json()
    assert detail["pages_photos"] == [] and detail["photo_gardee"] is False and detail["lignes"]
    assert client.delete(f"/pharmacist/deliveries/{bon_id}", headers=headers).status_code == 204
    with SessionLocal() as db:
        for model in (DeliveryNote, DeliveryLine, DeliveryPhoto):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        declarations = db.scalars(select(StockDeclaration).where(
            StockDeclaration.pharmacy_id == pharmacy_id)).all()
        assert len(declarations) == 15 and all(d.bon_id is None for d in declarations)


def test_last_reception_on_the_dashboard(client, pharmacist, store):
    headers, _ = pharmacist
    bon_id = keep_demo_note(client, headers)
    tegretol = find_medicine(store, "TEGRETOL", "200MG")["id"]
    item = next(i for i in client.get("/pharmacist/stock", headers=headers).json()
                if i["medicament"]["id"] == tegretol)
    assert item["derniere_reception"] == {"bon_id": bon_id, "date": "2026-10-20",
                                          "fournisseur": SUPPLIER, "quantite": 6.0,
                                          "numero_lot": "TG2006", "date_peremption": "2028-02"}
    receptions = client.get(f"/pharmacist/medicines/{tegretol}/receptions", headers=headers).json()
    assert receptions[0]["bon_id"] == bon_id and receptions[0]["numero_lot"] == "TG2006"


def test_export_csv(client, pharmacist, validated_pharmacist):
    headers, _ = pharmacist
    keep_demo_note(client, headers)
    response = client.get("/pharmacist/deliveries/export", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(response.text.lstrip("﻿")), delimiter=";"))
    assert rows[0] == ["date", "fournisseur", "numero_bon", "medicament", "dosage", "quantite",
                       "numero_lot", "date_peremption", "action"]
    assert len(rows) == 1 + 19
    assert ["2026-10-20", SUPPLIER, NOTE_NUMBER, "TEGRETOL", "200MG", "6", "TG2006", "2028-02",
            "en_stock"] in rows


# --------------------------------------------------------------------------
# Retention and limits
# --------------------------------------------------------------------------

def test_cleanup_of_scans_photos_and_old_notes(client, pharmacist):
    headers, _ = pharmacist
    scan_id = scan(client, headers).json()["scan_id"]
    bon_id = keep_demo_note(client, headers, garder_photo=True)
    with SessionLocal() as db:
        db.get(DeliveryScan, scan_id).expire_le = utcnow() - timedelta(minutes=1)
        for photo in db.get(DeliveryNote, bon_id).photos:
            photo.cree_le = utcnow() - timedelta(days=91)
        db.commit()
        assert purge_expired_scans(db) >= 1
        assert db.get(DeliveryScan, scan_id) is None
        assert purge_history(db) == (1, 0)
        kept = db.get(DeliveryNote, bon_id)
        assert kept.photo_gardee is False and kept.lignes  # the detail stays
        kept.confirme_le = utcnow() - timedelta(days=31 * 25)
        db.commit()
        assert purge_history(db) == (0, 1)
        assert db.get(DeliveryNote, bon_id) is None


def test_monthly_photo_limit(client, pharmacist):
    headers, pharmacy_id = pharmacist
    with SessionLocal() as db:
        full = DeliveryNote(pharmacie_id=pharmacy_id, scanne_le=utcnow(), duree_secondes=1,
                            nb_lignes_lues=0, nb_mis_en_stock=0, nb_rupture=0, nb_non_livres=0,
                            nb_ignores=0, photo_gardee=True)
        full.photos = [DeliveryPhoto(page=i, image=b"x") for i in range(PHOTO_PAGES_PER_MONTH)]
        db.add(full)
        db.commit()
    result = scan(client, headers).json()
    assert result["photo_possible"] is False
    assert result["message_photo"] == delivery.PHOTO_LIMIT
    body = confirm(client, headers, result, garder_photo=True).json()
    assert body["photo_gardee"] is False and body["message_photo"] == delivery.PHOTO_LIMIT
    assert body["bon_id"] is not None and body["nb_en_stock"] == 15  # the rest works


def test_daily_scan_limit(client, pharmacist):
    headers, _ = pharmacist
    for _ in range(20):
        assert scan(client, headers).status_code == 200
    response = scan(client, headers)
    assert response.status_code == 429 and response.json()["code"] == "limite"


# --------------------------------------------------------------------------
# Confirmation checks
# --------------------------------------------------------------------------

def test_confirm_twice_other_pharmacy_and_expired(client, pharmacist, validated_pharmacist):
    headers, _ = pharmacist
    result = scan(client, headers).json()
    other, _ = validated_pharmacist()
    assert confirm(client, other, result).status_code == 404
    assert confirm(client, headers, result).status_code == 200
    assert confirm(client, headers, result).status_code == 409

    expired = scan(client, headers).json()
    with SessionLocal() as db:
        db.get(DeliveryScan, expired["scan_id"]).expire_le = utcnow() - timedelta(seconds=1)
        db.commit()
    assert confirm(client, headers, expired).status_code == 410


def test_confirm_refuses_an_unknown_medicine(client, pharmacist):
    headers, _ = pharmacist
    result = scan(client, headers).json()
    body = default_confirm(result)
    body["lignes"][0]["medicament_id"] = "000000000000"
    response = client.post(f"{SCAN}/{result['scan_id']}/confirm", headers=headers, json=body)
    assert response.status_code == 422
    body["lignes"][0].update(medicament_id=None, action="en_stock")
    response = client.post(f"{SCAN}/{result['scan_id']}/confirm", headers=headers, json=body)
    assert response.status_code == 422


def test_access_rules(client, fake_delivery_reader):
    fake_delivery_reader()
    pending, _, _ = register_pharmacist(client)  # not approved yet
    assert scan(client, pending).status_code == 403
    assert client.get("/pharmacist/deliveries", headers=pending).status_code == 403
    assert scan(client, {}).status_code == 401
    assert client.get("/pharmacist/deliveries").status_code == 401


def test_feature_off_without_key(client, validated_pharmacist):
    headers, _ = validated_pharmacist()
    assert client.get("/features").json()["delivery_scan"] is False
    response = scan(client, headers)
    assert response.status_code == 503 and response.json()["code"] == "desactivee"
    assert client.get("/pharmacist/deliveries", headers=headers).status_code == 200  # still readable


@pytest.mark.parametrize("pages, status", [
    ([b"%PDF-1.7 not an image"], 415),
    ([b"\xff\xd8\xff" + b"\0" * (8 * 1024 * 1024)], 413),
    ([page()] * 6, 413),
])
def test_bad_files(client, pharmacist, pages, status):
    headers, _ = pharmacist
    assert scan(client, headers, pages).status_code == status


def test_pages_are_prepared(client, pharmacist, fake_delivery_reader):
    headers, _ = pharmacist
    reader = fake_delivery_reader()
    scan(client, headers, [page("PNG", (4000, 3000)), page("WEBP")])
    assert len(reader.last_pages) == 2
    first = Image.open(BytesIO(reader.last_pages[0]))
    assert first.format == "JPEG" and max(first.size) == 2000


@pytest.mark.parametrize("error, status, code", [
    (QuotaExceeded("429"), 503, "saturee"), (LLMTimeout("slow"), 504, "delai"),
    ("not JSON", 502, "echec")])
def test_model_problems(client, pharmacist, fake_delivery_reader, error, status, code):
    headers, _ = pharmacist
    fake_delivery_reader(error)
    response = scan(client, headers)
    assert response.status_code == status
    assert response.json()["code"] == code
    if code == "saturee":
        assert response.json()["detail"] == delivery.SATURATED


def test_deleting_the_pharmacy_deletes_its_history(client, pharmacist):
    headers, pharmacy_id = pharmacist
    keep_demo_note(client, headers, garder_photo=True)
    with SessionLocal() as db:
        db.execute(text("DELETE FROM stock_declarations WHERE pharmacy_id = :p"), {"p": pharmacy_id})
        db.execute(text("DELETE FROM tracked_medicines WHERE pharmacy_id = :p"), {"p": pharmacy_id})
        db.delete(db.get(Pharmacy, pharmacy_id))
        db.commit()
        for model in (DeliveryNote, DeliveryLine, DeliveryPhoto, DeliveryScan):
            assert db.scalar(select(func.count()).select_from(model)) == 0
        assert db.scalar(select(func.count()).select_from(TrackedMedicine)) == 0


_written = None


def _audit(event, args):
    if _written is not None and event == "open":
        path, mode, flags = args
        if (mode and any(c in mode for c in "wax+")) or (flags or 0) & (
                os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND):
            _written.append(str(path))
    elif _written is not None and event in ("tempfile.mkstemp", "tempfile.mkdtemp"):
        _written.append(event)


sys.addaudithook(_audit)


def test_no_image_is_written_to_disk(client, pharmacist):
    global _written
    headers, _ = pharmacist
    noise = Image.frombytes("RGB", (1200, 1000), os.urandom(1200 * 1000 * 3))
    out = BytesIO()
    noise.save(out, "PNG")  # 3.6 MB: over the 1 MB after which uploads usually go to disk
    _written = []
    try:
        response = scan(client, headers, [out.getvalue(), out.getvalue()])
        written = list(_written)
    finally:
        _written = None
    assert response.status_code == 200
    assert written == []
