"""Load data/clean/medicaments.csv into memory, once, at startup.

The CSV is produced by scripts/clean_nomenclature.py. Its path can be changed
with the MEDICINES_CSV environment variable.
"""

from pathlib import Path

import pandas as pd

from .config import MEDICINES_CSV

BOOL_COLUMNS = ["dosage_verifie", "disponible_officine", "exclu"]
INT_COLUMNS = ["nb_equivalents"]


class MedicineStore:
    """Medicines that can be shown to patients, indexed by id and by equivalence key."""

    def __init__(self, records):
        self.records = records
        self.by_id = {m["id"]: m for m in records}
        self.by_key = {}
        for m in records:
            self.by_key.setdefault(m["equivalence_key"], []).append(m)

    def __len__(self):
        return len(self.records)

    def get(self, medicine_id):
        return self.by_id.get(medicine_id)

    def same_key(self, medicine):
        """Every presentation with the same key, including other packs of the same brand."""
        if not medicine["dosage_norm"]:
            return [medicine]
        return self.by_key.get(medicine["equivalence_key"], [medicine])

    def equivalents(self, medicine):
        """Same equivalence key, another brand name, one result per brand name.

        A medicine without any dose is never matched: its key would only say
        "same substance, same form".
        """
        if not medicine["dosage_norm"]:
            return []
        seen = {medicine["nom_marque"]}
        result = []
        for other in sorted(self.by_key.get(medicine["equivalence_key"], []),
                            key=lambda m: (m["nom_marque"], m["id"])):
            if other["nom_marque"] in seen:
                continue
            seen.add(other["nom_marque"])
            result.append(other)
        return result


def load_store(path=None):
    """Read the CSV and keep only medicines sold in pharmacies and not withdrawn."""
    path = Path(path) if path else MEDICINES_CSV
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python scripts/clean_nomenclature.py")

    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    for col in BOOL_COLUMNS:
        df[col] = df[col] == "True"
    for col in INT_COLUMNS:
        df[col] = df[col].astype(int)

    df = df[df["disponible_officine"] & ~df["exclu"]]
    return MedicineStore(df.to_dict(orient="records"))
