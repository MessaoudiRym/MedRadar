"""Generate FICTIONAL pharmacies and stock history in Oran, for the demo.

- 40 validated demo pharmacies + 2 pending ones, in real Oran districts,
  300 to 900 m from the district centre. Names, addresses and phone numbers
  are clearly fake ("Pharmacie Démo ...", 0550 00 00 XX).
- 6 weeks of stock history for about 40 chronic-treatment medicines found in
  the cleaned nomenclature, with realistic shortages on 9 of them.
- 3 demo pharmacist accounts (pharmacien1@medradar.demo ...), password read
  from DEMO_PHARMACIST_PASSWORD.

Only rows with is_demo = True (and the demo accounts) are deleted and
recreated: pharmacies registered by real pharmacists are never touched.
The random seed is fixed, so every run produces the same pharmacies.

Usage (after `alembic upgrade head`):
    python scripts/generate_demo_data.py
"""

import math
import os
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import delete, insert, select  # noqa: E402

from app.data import load_store  # noqa: E402
from app.db import SessionLocal, utcnow  # noqa: E402  (also loads .env)
from app.geo import ORAN_DISTRICTS  # noqa: E402
from app.models import (PHARMACY_PENDING, PHARMACY_VALIDATED, ROLE_PHARMACIST,  # noqa: E402
                        STOCK_IN, STOCK_OUT, Pharmacy, StockDeclaration, TrackedMedicine,
                        User)
from app.schemas import check_password  # noqa: E402
from app.security import hash_password  # noqa: E402

SEED = 2026
NB_VALIDATED = 40
NB_PENDING = 2
NB_MEDICINES = 40
NB_SHORTAGES = 9
HISTORY_DAYS = 42
SHORTAGE_DAYS = 14
DEMO_EMAIL_DOMAIN = "@medradar.demo"

COMMUNES = {
    "Bir El Djir": "Bir El Djir", "USTO": "Bir El Djir", "Canastel": "Bir El Djir",
    "Hai Sabah": "Bir El Djir", "Es Senia": "Es Senia",
}  # every other district: Oran

MOLECULES = ["METFORMINE", "GLICLAZIDE", "LEVOTHYROXINE", "AMLODIPINE", "BISOPROLOL",
             "LOSARTAN", "ATORVASTATINE", "VALPROATE", "CARBAMAZEPINE", "OMEPRAZOLE",
             "ESOMEPRAZOLE", "ROSUVASTATINE", "RAMIPRIL"]

OPENING_HOURS = ["8h00 – 20h00, tous les jours", "8h30 – 19h30, fermé le vendredi",
                 "8h00 – 22h00", "24h/24 (pharmacie de garde fictive)", None]


def offset_position(rng, lat, lng):
    """Random point 300 to 900 m from (lat, lng)."""
    distance_m = rng.uniform(300, 900)
    angle = rng.uniform(0, 2 * math.pi)
    d_lat = distance_m * math.cos(angle) / 111_320
    d_lng = distance_m * math.sin(angle) / (111_320 * math.cos(math.radians(lat)))
    return round(lat + d_lat, 6), round(lng + d_lng, 6)


def pick_medicines(store):
    """About 40 presentations: for each molecule, a reference brand and two of its equivalents.

    Returns (medicines, shortage ids). Shortages hit reference brands, so the
    demo shows a brand out of stock while its generics are available.
    """
    by_molecule = {}
    for m in store.records:
        if "/" in m["dci_cle"] or not m["dosage_verifie"]:
            continue
        words = m["molecule"].replace("+", " ").split()
        for molecule in MOLECULES:
            if any(w.startswith(molecule) for w in words):
                by_molecule.setdefault(molecule, []).append(m)
    for candidates in by_molecule.values():
        candidates.sort(key=lambda m: (m["type"] != "référence", -m["nb_equivalents"],
                                       m["nom_marque"], m["id"]))

    chosen, chosen_ids, leaders = [], set(), []
    for round_number in range(3):
        for molecule in MOLECULES:
            candidates = [m for m in by_molecule.get(molecule, []) if m["id"] not in chosen_ids]
            if not candidates or len(chosen) >= NB_MEDICINES:
                continue
            leader = candidates[0]
            group = [leader] + [e for e in store.equivalents(leader)
                                if e["id"] not in chosen_ids][:2]
            for m in group[:NB_MEDICINES - len(chosen)]:
                chosen.append(m)
                chosen_ids.add(m["id"])
            if round_number == 0:
                leaders.append(leader["id"])
    return chosen, set(leaders[:NB_SHORTAGES])


def delete_demo_data(db):
    demo_ids = select(Pharmacy.id).where(Pharmacy.is_demo.is_(True))
    db.execute(delete(StockDeclaration).where(StockDeclaration.pharmacy_id.in_(demo_ids)))
    db.execute(delete(TrackedMedicine).where(TrackedMedicine.pharmacy_id.in_(demo_ids)))
    db.execute(delete(Pharmacy).where(Pharmacy.is_demo.is_(True)))
    db.execute(delete(User).where(User.email.like(f"%{DEMO_EMAIL_DOMAIN}"),
                                  User.role == ROLE_PHARMACIST))


def create_pharmacies(db, rng):
    districts = list(ORAN_DISTRICTS)
    pharmacies = []
    for n in range(1, NB_VALIDATED + NB_PENDING + 1):
        district = districts[(n - 1) % len(districts)]
        lat, lng = offset_position(rng, *ORAN_DISTRICTS[district])
        validated = n <= NB_VALIDATED
        pharmacies.append(Pharmacy(
            name=f"Pharmacie Démo {district} {n:02d}",
            address=f"Adresse fictive n°{n}, {district}, Oran",
            commune=COMMUNES.get(district, "Oran"),
            district=district,
            latitude=lat, longitude=lng,
            phone=f"05500000{n:02d}",  # 0550 00 00 XX: clearly fake
            professional_number=f"DEMO-{n:04d}",
            opening_hours=rng.choice(OPENING_HOURS),
            status=PHARMACY_VALIDATED if validated else PHARMACY_PENDING,
            is_demo=True,
            validated_at=utcnow() - timedelta(days=HISTORY_DAYS + 1) if validated else None,
        ))
    db.add_all(pharmacies)
    db.flush()
    return pharmacies


def create_accounts(db, pharmacies, password):
    # Two validated pharmacies, and one pending (to show "en cours de vérification")
    owned = [pharmacies[0], pharmacies[1], pharmacies[NB_VALIDATED]]
    users = []
    for n, pharmacy in enumerate(owned, start=1):
        user = User(email=f"pharmacien{n}{DEMO_EMAIL_DOMAIN}", password_hash=hash_password(password),
                    last_name=f"Démo {n}", first_name="Pharmacien",
                    phone=f"05500001{n:02d}", role=ROLE_PHARMACIST)
        db.add(user)
        db.flush()
        pharmacy.owner_id = user.id
        users.append(user)
    return users


def create_history(db, rng, pharmacies, medicines, shortages):
    now = utcnow()
    shortage_start = now - timedelta(days=SHORTAGE_DAYS)

    # Each pharmacy: how often it updates, and which medicines it follows.
    # Some stopped updating 8 to 12 days ago: their data is "à confirmer".
    profiles = []
    for pharmacy in pharmacies[:NB_VALIDATED]:
        profiles.append({
            "pharmacy": pharmacy,
            "every_days": rng.choice([1, 2, 3, 4]),
            "last_update": now - timedelta(days=rng.uniform(8, 12)) if rng.random() < 0.15 else now,
            "followed": rng.sample(medicines, round(len(medicines) * rng.uniform(0.6, 0.9))),
        })

    # For each shortage, 50 to 80 % of the pharmacies that follow it run out
    out_of_stock = {}
    for m_id in sorted(shortages):
        followers = [p["pharmacy"].id for p in profiles
                     if any(m["id"] == m_id for m in p["followed"])]
        out_of_stock[m_id] = set(rng.sample(followers, round(len(followers) * rng.uniform(0.5, 0.8))))

    tracked_rows, declaration_rows = [], []
    for profile in profiles:
        pharmacy, every_days = profile["pharmacy"], profile["every_days"]
        for medicine in profile["followed"]:
            tracked_rows.append({"pharmacy_id": pharmacy.id, "medicine_id": medicine["id"],
                                 "added_at": now - timedelta(days=HISTORY_DAYS)})
            t = now - timedelta(days=HISTORY_DAYS, hours=rng.uniform(0, 24 * every_days))
            while t <= profile["last_update"]:
                if t >= shortage_start and pharmacy.id in out_of_stock.get(medicine["id"], ()):
                    status = STOCK_OUT  # a shortage lasts: no stock comes back in 2 weeks
                else:
                    status = STOCK_IN if rng.random() < 0.95 else STOCK_OUT
                declaration_rows.append({
                    "pharmacy_id": pharmacy.id, "medicine_id": medicine["id"], "status": status,
                    "declared_by": pharmacy.owner_id, "declared_at": t})
                t += timedelta(days=every_days, hours=rng.uniform(-6, 6))

    db.execute(insert(TrackedMedicine), tracked_rows)
    db.execute(insert(StockDeclaration), declaration_rows)
    return len(tracked_rows), len(declaration_rows)


def main():
    password = os.environ.get("DEMO_PHARMACIST_PASSWORD", "")
    try:
        check_password(password)
    except ValueError as error:
        sys.exit(f"DEMO_PHARMACIST_PASSWORD is missing or too weak: {error}")

    rng = random.Random(SEED)
    store = load_store()
    medicines, shortages = pick_medicines(store)

    with SessionLocal() as db:
        delete_demo_data(db)
        pharmacies = create_pharmacies(db, rng)
        users = create_accounts(db, pharmacies, password)
        nb_tracked, nb_declarations = create_history(db, rng, pharmacies, medicines, shortages)
        db.commit()

    print(f"Demo pharmacies : {NB_VALIDATED} validated + {NB_PENDING} pending (all fictional)")
    print(f"Demo accounts   : {', '.join(u.email for u in users)}")
    print(f"Medicines       : {len(medicines)} ({nb_tracked} tracked pairs, "
          f"{nb_declarations} stock declarations over {HISTORY_DAYS} days)")
    print("Shortages       : " + ", ".join(
        f"{m['nom_marque']} {m['dosage_norm']}" for m in medicines if m["id"] in shortages))


if __name__ == "__main__":
    main()
