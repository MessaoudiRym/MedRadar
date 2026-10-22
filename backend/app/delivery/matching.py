"""Match each line of a delivery note to a medicine of the official nomenclature.

The model only gives text ("GLUCOPH 850 CP B/30"). Our code decides, with fixed
rules and the existing search:
    1. split the wholesaler's text: brand (often cut: GLUCOPH), dose (850),
       form (CP = comprimé), pack size (B/30, ignored);
    2. find candidates with the typo-tolerant search, the cut brand counting
       as the start of the full name;
    3. score them: same name, then same dose (normalize_dose), then same form
       (form_group), with the functions that cleaned the nomenclature;
    4. say how sure the match is:
         "exacte"     name, dose and form agree: ticked by default;
         "a_verifier" a likely match: 3 candidates, NOT ticked until chosen;
         "non_trouve" nothing reliable (often parapharmacy): never ticked;
         "non_livre"  back order or missing: never ticked.
Nothing is declared here: the pharmacist confirms.
"""

import re

from rapidfuzz import fuzz

from ..recognition import brand_core, form_group, normalize_dose
from ..search import normalize
from ..smart_search import dose_matches

EXACT = "exacte"
TO_CHECK = "a_verifier"
NOT_FOUND = "non_trouve"
NOT_DELIVERED = "non_livre"

# Thresholds, easy to adjust (0-1)
SAME_NAME = 0.95          # brand names the same (or a wholesaler's cut of it)
CUT_NAME = 0.97           # "GLUCOPH" for GLUCOPHAGE: the start of the name, 5 letters or more
MIN_CUT_LETTERS = 5
LIKELY_NAME = 0.75        # below this, no candidate is proposed at all
MAX_CANDIDATES = 3
CANDIDATES_PER_SEARCH = 30

# Wholesalers' abbreviations of forms, written in full before form_group()
FORM_WORDS = {
    "CP": "COMPRIME", "CPR": "COMPRIME", "CPS": "COMPRIME", "COMP": "COMPRIME",
    "PELL": "PELLICULE", "SEC": "SECABLE", "EFF": "EFFERVESCENT", "DISP": "DISPERSIBLE",
    "ORODISP": "ORODISPERSIBLE", "LM": "LIBERATION MODIFIEE", "LP": "LIBERATION PROLONGEE",
    "GR": "GASTRO-RESISTANT",
    "GEL": "GELULE", "GELU": "GELULE", "GLES": "GELULE", "GELS": "GELULE", "CAPS": "CAPSULE",
    "SACH": "POUDRE ORALE EN SACHET", "SACHET": "POUDRE ORALE EN SACHET",
    "SACHETS": "POUDRE ORALE EN SACHET", "SCH": "POUDRE ORALE EN SACHET",
    "PDR": "POUDRE", "GRAN": "GRANULES",
    "SIR": "SIROP", "SP": "SIROP", "SUSP": "SUSPENSION", "SOL": "SOLUTION", "BUV": "BUVABLE",
    "INJ": "INJECTABLE", "SUPPO": "SUPPOSITOIRE", "SUPP": "SUPPOSITOIRE",
    "CR": "CREME", "CREME": "CREME", "POM": "POMMADE", "COLL": "COLLYRE",
    "EMULGEL": "GEL", "SPR": "SPRAY",
}
FORM_KEYS = set(FORM_WORDS) | {"COMPRIME", "COMPRIMES", "GELULE", "GELULES", "SIROP", "POUDRE",
                               "SUSPENSION", "SOLUTION", "BUVABLE", "INJECTABLE", "SUPPOSITOIRE",
                               "COLLYRE", "POMMADE", "SPRAY", "AMPOULE", "AMP"}
# Pack sizes and units that are not part of the name: B/30, BT30, X30, 50G (tube), 50ML
PACK = re.compile(r"^(B|BT|BTE|BOITE|BOIT|X|FL|TB|TUBE)/?\d*$|^\d+(G|ML)$|^/\d+$")
DOSE = re.compile(r"^\d+(?:[.,]\d+)?(MG|G|MCG|µG|UG|ML|UI|%)?(/\d*(ML|G|DOSE)?)?$")


def parse_designation(text: str):
    """("GLUCOPH", "850", "COMPRIME") from "GLUCOPH 850 CP B/30"."""
    words = normalize(text).replace("µ", "U").split()
    name, dose, forms = [], None, []
    i = 0
    while i < len(words):
        word = words[i]
        if word in ("B", "BT", "BTE", "BOITE") and i + 1 < len(words) and words[i + 1].lstrip("/").isdigit():
            i += 2  # "B 30": pack size
            continue
        if word in FORM_KEYS:
            forms.append(FORM_WORDS.get(word, word))
        elif dose is None and DOSE.match(word) and (name or forms):
            dose = word
        elif PACK.match(word) and (name or dose):
            pass
        elif not dose and not forms:
            name.append(word)  # the name comes first
        i += 1
    return " ".join(name), dose, " ".join(forms)


def name_similarity(read: str, medicine: dict) -> float:
    """0-1. A wholesaler's cut of the name ("GLUCOPH") counts as the full name."""
    core = brand_core(medicine["nom_marque"])
    read = brand_core(read)
    if not read or not core:
        return 0.0
    if read == core:
        return 1.0
    if core.startswith(read) and len(read) >= max(MIN_CUT_LETTERS, len(core) // 2):
        return CUT_NAME
    return max(fuzz.ratio(read, core), fuzz.ratio(read, normalize(medicine["nom_marque"]))) / 100


def _base(group: str) -> str:
    return group.split(" — ")[0]


def form_agrees(read_group: str | None, medicine: dict):
    """True / False, or None when the form was not read. "comprimé" agrees with
    "comprimé — gastro-résistant": wholesalers rarely write the coating."""
    if not read_group or read_group.startswith("autre"):
        return None
    return _base(read_group) == _base(medicine["forme_groupe"])


def summary(medicine: dict) -> dict:
    keys = ("id", "nom_marque", "molecule", "dosage_norm", "forme_groupe", "nb_equivalents")
    return {k: medicine[k] for k in keys}


class LineMatcher:
    def __init__(self, store, index):
        self.store = store
        self.index = index

    def candidates(self, names):
        found = {}
        for name in names:
            if name:
                for m in self.index.search(name, CANDIDATES_PER_SEARCH):
                    found[m["id"]] = m
        return list(found.values())

    def match(self, line):
        """{correspondance, medicament, candidats} for one line read by the model."""
        parsed_name, parsed_dose, parsed_form = parse_designation(line.designation)
        names = [n for n in (line.nom_marque, parsed_name) if n]
        # What the model put in its fields AND what our parser finds in the designation:
        # a model may write "1G CP DISP" as the dose; either reading may agree
        doses = [d.lower() for d in (line.dosage, parsed_dose) if d and re.search(r"\d", d)]
        model_form = " ".join(FORM_WORDS.get(w, w) for w in normalize(line.forme or "").split())
        groups = [form_group(f) for f in (model_form, parsed_form) if f]

        scored = []
        for medicine in self.candidates(names or [line.designation]):
            name = max((name_similarity(n, medicine) for n in names), default=0.0)
            if name < LIKELY_NAME:
                continue
            dose_ok = any(dose_matches(d, medicine["dosage_norm"]) for d in doses)
            agreements = [form_agrees(g, medicine) for g in groups]
            form_ok = True if True in agreements else (False if False in agreements else None)
            score = 0.6 * name + 0.25 * dose_ok + 0.15 * (0.5 if form_ok is None else form_ok)
            scored.append((score, name, dose_ok, form_ok, medicine))
        scored.sort(key=lambda s: (-s[0], s[4]["nom_marque"], s[4]["id"]))

        # Several packs of the same presentation: shown once
        best, seen = [], set()
        for item in scored:
            key = (item[4]["nom_marque"], item[4]["dosage_norm"], item[4]["forme_groupe"])
            if key not in seen:
                seen.add(key)
                best.append(item)

        not_delivered = line.statut_ligne in ("reliquat", "manquant") or line.quantite_livree == 0
        if not best:
            return {"correspondance": NOT_DELIVERED if not_delivered else NOT_FOUND,
                    "medicament": None, "candidats": []}

        score, name, dose_ok, form_ok, medicine = best[0]
        # Exact: same name and dose, the form agrees (or was not written but only one
        # presentation has this name and dose), and no other presentation as good
        same_score = [b for b in best[1:] if b[0] >= score]
        exact = (name >= SAME_NAME and dose_ok and form_ok is not False and not same_score
                 and line.lisible)
        if not_delivered:
            status = NOT_DELIVERED
        else:
            status = EXACT if exact else TO_CHECK
        return {
            "correspondance": status,
            "medicament": summary(medicine),
            "candidats": [summary(b[4]) for b in best[:MAX_CANDIDATES]],
        }


def merge_duplicates(lines):
    """The same medicine on two "exacte" lines: one line, quantities added."""
    merged, by_medicine = [], {}
    for line in lines:
        medicine = line["medicament"]
        if line["correspondance"] == EXACT and medicine:
            first = by_medicine.get(medicine["id"])
            if first is not None:
                if line["quantite"] is not None:
                    first["quantite"] = (first["quantite"] or 0) + line["quantite"]
                lots = [lot for lot in (first["numero_lot"], line["numero_lot"]) if lot]
                first["numero_lot"] = ", ".join(dict.fromkeys(lots))[:40] or None
                first["designations_regroupees"].append(line["designation"])
                continue
            by_medicine[medicine["id"]] = line
        merged.append(line)
    return merged


def analyse_lines(matcher: LineMatcher, reading):
    """The lines to show the pharmacist, and the summary."""
    lines = []
    for line in reading.lignes:
        result = matcher.match(line)
        lines.append({
            "designation": line.designation,
            "designations_regroupees": [],
            "quantite": line.quantite_livree,
            "numero_lot": line.numero_lot,
            "date_peremption": line.date_peremption,
            "statut_ligne": line.statut_ligne,
            **result,
        })
    lines = merge_duplicates(lines)
    for index, line in enumerate(lines):
        line["index"] = index
        line["coche"] = line["correspondance"] == EXACT
    counts = {status: sum(1 for line in lines if line["correspondance"] == status)
              for status in (EXACT, TO_CHECK, NOT_FOUND, NOT_DELIVERED)}
    resume = {
        "lignes_lues": len(reading.lignes),
        "exactes": counts[EXACT],
        "a_verifier": counts[TO_CHECK],
        "non_trouvees": counts[NOT_FOUND],
        "non_livrees": counts[NOT_DELIVERED],
        "regroupees": len(reading.lignes) - len(lines),
    }
    return lines, resume


__all__ = ["LineMatcher", "analyse_lines", "parse_designation", "normalize_dose",
           EXACT, TO_CHECK, NOT_FOUND, NOT_DELIVERED]
