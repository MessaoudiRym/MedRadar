"""Turn what was read on a box into medicines of the official nomenclature.

The vision model only gives text. This module decides, with fixed rules:
    1. find candidates with the existing search (brand name first, then
       active ingredient);
    2. rank them: same name > same dose (normalize_dose) > same form (form_group),
       with the functions that cleaned the nomenclature, so "850 mg" read on a
       box is compared exactly like "850MG" in the official file;
    3. say how sure the match is: "exacte", "probable" or "à vérifier".
The patient then confirms the medicine; equivalents come from the usual rules.
"""

import importlib.util
import re

from rapidfuzz import fuzz

from .config import PROJECT_ROOT
from .search import normalize, split_words


def _load_cleaning_rules():
    """The functions of scripts/clean_nomenclature.py (one source of truth)."""
    path = PROJECT_ROOT / "scripts" / "clean_nomenclature.py"
    spec = importlib.util.spec_from_file_location("clean_nomenclature", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_rules = _load_cleaning_rules()
normalize_dose = _rules.normalize_dose
form_group = _rules.form_group
make_dci_key = _rules.make_dci_key

EXACT = "exacte"
LIKELY = "probable"
TO_CHECK = "à vérifier"

MAX_RESULTS = 3
CANDIDATES_PER_SEARCH = 40
MIN_IDENTITY = 0.5   # below this, a candidate is not shown at all
SAME_NAME = 0.95     # brand names "the same" (spacing, accents)
CLOSE_NAME = 0.75    # a reading mistake or a typo ("GLUCOFAGE")

# Doses printed next to the brand name: "GLUCOPHAGE 850 MG" -> "GLUCOPHAGE"
DOSE_WORD = re.compile(r"^(\d+([.,]\d+)?)?(MG|G|MCG|UG|ML|UI|%)?$")


def brand_core(name):
    return " ".join(w for w in split_words(normalize(name)) if not DOSE_WORD.match(w))


def brand_similarity(read, candidate):
    """0 to 1, with and without the dose written in the name."""
    full = fuzz.ratio(normalize(read), normalize(candidate))
    core = fuzz.ratio(brand_core(read), brand_core(candidate))
    return max(full, core) / 100


def same_substances(read_key, candidate_key):
    """Each substance read is in the medicine, and no substance is missing.

    "METFORMINE" matches "CHLORHYDRATE METFORMINE" (the salt is often not printed),
    but "AMLODIPINE" alone never matches "AMLODIPINE/VALSARTAN".
    """
    read = [set(c.split()) for c in read_key.split("/") if c]
    candidate = [set(c.split()) for c in candidate_key.split("/") if c]
    if not read or len(read) != len(candidate):
        return False
    remaining = list(candidate)
    for words in read:
        match = next((c for c in remaining if words <= c), None)
        if match is None:
            return False
        remaining.remove(match)
    return True


def find_candidates(reading, store, index):
    found = {}
    if reading.nom_marque:
        query = brand_core(reading.nom_marque) or reading.nom_marque
        for m in index.search(query, CANDIDATES_PER_SEARCH):
            found[m["id"]] = m
    if reading.dci:
        key = make_dci_key(reading.dci)
        if key:
            for m in store.records:
                if same_substances(key, m["dci_cle"]):
                    found[m["id"]] = m
        if not found:
            for m in index.search(reading.dci, CANDIDATES_PER_SEARCH):
                found[m["id"]] = m
    return list(found.values())


def match(reading, medicine, read_dci_key, read_dose, read_form):
    """(score, correspondance) of one candidate."""
    dci_ok = bool(read_dci_key) and same_substances(read_dci_key, medicine["dci_cle"])
    dose_ok = bool(read_dose) and read_dose == medicine["dosage_norm"]
    form_ok = bool(read_form) and read_form == medicine["forme_groupe"]

    if reading.nom_marque:
        name = brand_similarity(reading.nom_marque, medicine["nom_marque"])
        identity = 0.8 * name + 0.2 * dci_ok if read_dci_key else name
        same_name, close_name = name >= SAME_NAME, name >= CLOSE_NAME
    else:
        # Without the brand, several brands fit: never "exacte"
        identity = 1.0 if dci_ok else 0.0
        same_name, close_name = False, dci_ok

    score = 0.6 * identity + 0.25 * dose_ok + 0.15 * form_ok
    if identity < MIN_IDENTITY:
        return None
    if same_name and dose_ok and form_ok:
        level = EXACT
    elif close_name and dose_ok and (form_ok or not read_form):
        level = LIKELY
    else:
        level = TO_CHECK
    return score, level


def rank(reading, store, index):
    """The 3 best medicines for what was read, best first: [(medicine, correspondance)]."""
    read_dci_key = make_dci_key(reading.dci) if reading.dci else ""
    read_dose = normalize_dose(reading.dosage)[0] if reading.dosage else ""
    read_form = form_group(reading.forme) if reading.forme else ""

    scored = []
    for medicine in find_candidates(reading, store, index):
        result = match(reading, medicine, read_dci_key, read_dose, read_form)
        if result:
            scored.append((result, medicine))
    scored.sort(key=lambda r: (-r[0][0], r[1]["nom_marque"], r[1]["id"]))

    # Several packs of the same medicine: show it once
    seen, best = set(), []
    for (_, level), medicine in scored:
        key = (medicine["nom_marque"], medicine["dosage_norm"], medicine["forme_groupe"])
        if key in seen:
            continue
        seen.add(key)
        best.append((medicine, level))
        if len(best) == MAX_RESULTS:
            break
    return best
