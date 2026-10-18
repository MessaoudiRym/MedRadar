"""Medicine ids must not change when the cleaning script runs again:
stock declarations and alerts point to them."""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import clean_nomenclature  # noqa: E402


@pytest.fixture(scope="module")
def rebuilt():
    if not clean_nomenclature.RAW_FILE.exists():
        pytest.skip("raw nomenclature file not available")
    df, _ = clean_nomenclature.build()
    return df


def test_ids_are_unique_and_12_characters(rebuilt):
    assert rebuilt["id"].is_unique
    assert (rebuilt["id"].str.len() == 12).all()


def test_ids_are_the_same_as_in_the_published_csv(rebuilt):
    published = pd.read_csv(clean_nomenclature.OUT_FILE, dtype=str, keep_default_na=False)
    assert list(rebuilt["id"]) == list(published["id"])


def test_id_depends_only_on_the_presentation():
    row = {"num_enregistrement": "123/01 A 001/26", "nom_marque": "TEST",
           "dosage_norm": "10MG", "forme": "COMPRIME", "conditionnement": "B/30"}
    assert clean_nomenclature.make_id(row) == clean_nomenclature.make_id(dict(row))
    assert clean_nomenclature.make_id(row) != clean_nomenclature.make_id(row | {"dosage_norm": "20MG"})
