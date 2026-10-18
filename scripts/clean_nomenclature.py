"""Clean the Algerian national nomenclature and build equivalence keys.

Reads data/raw/clean_NOMENCLATURE.VERSION.AOUT_.2026-.xlsx (never modified)
and writes data/clean/medicaments.csv.

Two medicines are equivalent when they share the same equivalence_key:
same active substance (dci_cle) + same normalized dose + same form group.

Usage:
    python scripts/clean_nomenclature.py
"""

import hashlib
import re
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "data" / "raw" / "clean_NOMENCLATURE.VERSION.AOUT_.2026-.xlsx"
OUT_FILE = ROOT / "data" / "clean" / "medicaments.csv"

SHEET_MAIN = "Nomenclature Aout 2026"
SHEET_NOT_RENEWED = "Non Renouvelés "  # the trailing space is in the official file
SHEET_WITHDRAWN = "Retraits"

# Original column name -> name in the clean file
COLUMNS = {
    "N°ENREGISTREMENT": "num_enregistrement",
    "DENOMINATION COMMUNE INTERNATIONALE": "dci",
    "NOM DE MARQUE": "nom_marque",
    "FORME": "forme",
    "DOSAGE": "dosage",
    "CONDITIONNEMENT": "conditionnement",
    "LISTE": "liste",
    "P2": "p2",
    "OBS": "obs",
    "LABORATOIRES DETENTEUR DE LA DECISION D'ENREGISTREMENT": "laboratoire",
    "PAYS DU LABORATOIRE DETENTEUR DE LA DECISION D'ENREGISTREMENT": "pays_laboratoire",
    "TYPE": "type",
    "STATUT": "statut",
}

OUTPUT_COLUMNS = [
    "id", "num_enregistrement", "nom_marque", "dci", "dci_cle", "molecule",
    "forme", "forme_groupe", "voie", "dosage", "dosage_norm", "dosage_verifie",
    "conditionnement", "laboratoire", "pays_laboratoire", "type", "origine",
    "liste", "disponible_officine", "exclu", "equivalence_key", "nb_equivalents",
]

TYPES = {"GE": "générique", "RE": "référence", "BIO": "biosimilaire"}
ORIGINS = {"F": "fabriqué en Algérie", "I": "importé"}


# --------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------

def read_sheet(sheet_name):
    """Read one sheet, skipping the administrative block above the table.

    The header row is the first row that contains "NOM DE MARQUE".
    """
    raw = pd.read_excel(RAW_FILE, sheet_name=sheet_name, header=None, dtype=object)
    header_row = None
    for i, row in raw.iterrows():
        if any(str(v).strip() == "NOM DE MARQUE" for v in row):
            header_row = i
            break
    if header_row is None:
        raise ValueError(f"No 'NOM DE MARQUE' header found in sheet {sheet_name!r}")

    df = raw.iloc[header_row + 1:].copy()
    df.columns = [str(c).strip() if pd.notna(c) else f"_empty_{j}"
                  for j, c in enumerate(raw.iloc[header_row])]
    df = df.loc[:, ~df.columns.str.startswith("_empty_")]
    return df.dropna(subset=["NOM DE MARQUE"])


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------

def clean_text(value):
    """Uppercase, remove accents, collapse spaces and line breaks."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).replace("µ", "MC").replace("μ", "MC")  # micro sign, before accents go
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", text.upper()).strip()


# --------------------------------------------------------------------------
# Active substance key (dci_cle)
# --------------------------------------------------------------------------

STOP_WORDS = {"DE", "D", "DU", "DES"}


def split_top_level(text):
    """Split an association on "/", "+" or " ET ", ignoring separators inside parentheses."""
    parts, depth, current, i = [], 0, "", 0
    while i < len(text):
        c = text[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(depth - 1, 0)
        if depth == 0 and c in "/+":
            parts.append(current)
            current = ""
        elif depth == 0 and text.startswith(" ET ", i):
            parts.append(current)
            current = ""
            i += 3
            continue
        else:
            current += c
        i += 1
    parts.append(current)
    return [p.strip() for p in parts if p.strip()]


def words(text):
    """Words of a substance name, without punctuation."""
    return re.sub(r"[^A-Z0-9-]+", " ", text).split()


def active_substance(component):
    """Keep the active substance when the text names it.

    "X EXPRIME EN Y" -> Y, "Y SOUS FORME ..." -> Y, "X (Y)" -> Y.
    For "X (Y)", Y is kept only when it repeats a word of X
    ("AMLODIPINE BESILATE (AMLODIPINE)"); otherwise the parenthesis is a
    qualifier ("FENOFIBRATE (MICRONISE)") and is dropped.
    """
    text = component.replace("*", " ")
    match = re.search(r"\bEXPRIMEE?S? EN\b(.*)", text)
    if match:
        text = match.group(1)
    match = re.search(r"^(.*?)\(?\s*\bSOUS FORME\b", text)
    if match:
        text = match.group(1)
    while True:
        match = re.search(r"^(.*?)\(([^()]*)\)?(.*)$", text)
        if not match:
            break
        outside, inside, rest = match.groups()
        if set(words(inside)) & (set(words(outside)) | set(words(rest))) - STOP_WORDS:
            text = inside
        else:
            text = f"{outside} {rest}"
    return " ".join(words(text))


def dci_components(dci):
    text = clean_text(dci).replace("S/F", " SOUS FORME ").replace("'", " ")
    components = [active_substance(c) for c in split_top_level(text)]
    return sorted(c for c in components if c)


def make_dci_key(dci):
    """Order-independent key: words sorted inside each component, components sorted."""
    keys = []
    for component in dci_components(dci):
        kept = sorted(w for w in component.split() if w not in STOP_WORDS)
        if kept:
            keys.append(" ".join(kept))
    return "/".join(sorted(keys))


def make_molecule(dci):
    """Readable active substance(s), e.g. "AMLODIPINE + IRBESARTAN"."""
    return " + ".join(dci_components(dci))


# --------------------------------------------------------------------------
# Pharmaceutical form
# --------------------------------------------------------------------------

# Typos found in the file
FORM_TYPOS = [
    (r"\bCOMRIME\b|\bCOMRPIME\b|\bCOMPRIMPE\b|\bCOPRIME\b|\bCOMPRIM2\b|\bCOMPRIMES\b", "COMPRIME"),
    (r"GELLULE", "GELULE"),
    (r"\bBUVALE\b|\bBUVABE\b", "BUVABLE"),
    (r"SUSPENSSION", "SUSPENSION"),
    (r"EFFERVESSANT", "EFFERVESCENT"),
    (r"\bSIOLUTION\b|\bSOLOTION\b", "SOLUTION"),
    (r"GASTO-", "GASTRO-"),
]

# Abbreviations: each one becomes the full word followed by a space,
# so that "SOL.INJ." becomes "SOLUTION INJECTABLE"
FORM_ABBREVIATIONS = [
    (r"\bCOMP\.", "COMPRIME "),
    (r"\bCP\b\.?", "COMPRIME "),
    (r"\bDRG\.", "DRAGEE "),
    (r"\bGLES\.", "GELULE "),
    (r"\bBUV\b\.?", "BUVABLE "),
    (r"\bSOL\b\.?", "SOLUTION "),
    (r"\bSUSP?\b\.?", "SUSPENSION "),
    (r"\bINJ\b\.?", "INJECTABLE "),
    (r"\bPDRE\b\.?", "POUDRE "),
    (r"\bPERF\b\.?", "PERFUSION "),
    (r"\bINHAL\b\.?", "INHALATION "),
    (r"\bNAS\b\.?", "NASALE "),
    (r"\bRECT\b\.?", "RECTALE "),
    (r"\bOR\.", "ORALE "),
    (r"\bAPPL\b\.?", "APPLICATION "),
    (r"\bLYOPH\b\.?", "LYOPHILISAT "),
    (r"\bGTTES\b\.?", "GOUTTES "),
    (r"\bAURI?C\b\.?", "AURICULAIRE "),
    (r"\bLP\b", "LIBERATION PROLONGEE "),
    (r"\bLIB\.? PROL?\b", "LIBERATION PROLONGEE "),
]

MODIFIED_RELEASE = r"LIBERATION (PROLONGEE?|MODIFIEE|RETARDEE)|DOUBLE LIBERATION|DIFFUSION LENTE"
GASTRO_RESISTANT = r"GASTRO[- ]?RESIST|\bGR\b"

# (group, pattern), tested in this order: the first match wins
FORM_RULES = [
    ("autre", r"HEMODIALYSE|\bDIALYSE\b|HEMOFILTRATION|IRRIGATION"),
    ("injectable", r"INJECT|PERFUSION|PERFEUSION|PARENTERAL|SERINGUE|STYLO|IMPLANT|SOLVANT|\bIV\b"),
    ("ophtalmique", r"COLLYRE|\bCOLLY\b|OPHT|OCULAIRE"),
    ("voie nasale", r"NASAL"),
    ("inhalation", r"INHAL|NEBUL|\bNEB\b|AEROSOL|GAZ "),
    ("auriculaire", r"AURICULAIRE"),
    ("voie vaginale", r"VAGINAL|OVULE|GYNECO|INTRA-UTERIN"),
    ("suppositoire ou voie rectale", r"SUPPOSITOIRE|RECTAL|\bREC\b"),
    ("voie sublinguale", r"SUBLINGU"),
    ("bouche et gorge", r"BOUCHE|BUCCAL|COLLUTOIRE|GINGIVAL"),
    ("gélule", r"^GELULE"),  # "GELULE ... CONTENANT DES MINI-COMPRIMES"
    ("comprimé orodispersible", r"ORODISPERSIBLE"),
    ("effervescent", r"EFFERVESCENT"),
    ("dispersible", r"COMPRIME.*DISPERS"),
    ("à sucer", r"COMPRIME.*SUCER"),
    ("à croquer", r"COMPRIME.*CROQUER"),
    ("comprimé", r"COMPRIME|DRAGEE"),
    ("gélule", r"GELULE|CAPSULE DURE"),
    ("capsule molle", r"CAPSULE"),
    ("sirop", r"SIROP"),
    ("poudre ou granulés oraux", r"POUDRE|GRANULE|LYOPHILISAT|\bLAIT\b"),
    ("suspension buvable", r"SUSPENSION"),
    ("solution buvable", r"BUVABLE|ORAL|GOUTTES|AMP\b"),
    ("crème", r"CREME"),
    ("pommade", r"POMMADE|BAUME"),
    ("gel", r"\bGEL\b"),
    ("usage cutané", r"DERM|CUTANE|LOTION|SHAMPOING|VERNIS|PATCH|EXTERNE|LOCALE|MOUSSE|ANTISEPTIQUE"),
]

# Groups where both a vaginal/rectal and an oral use are written: keep the oral one
ORAL_HINT = r"BUVABLE|ORALE"

ROUTES = {
    "injectable": "injectable",
    "ophtalmique": "ophtalmique",
    "voie nasale": "nasale",
    "inhalation": "inhalée",
    "auriculaire": "auriculaire",
    "voie vaginale": "vaginale",
    "suppositoire ou voie rectale": "rectale",
    "voie sublinguale": "sublinguale",
    "bouche et gorge": "buccale",
    "crème": "cutanée",
    "pommade": "cutanée",
    "gel": "cutanée",
    "usage cutané": "cutanée",
    "autre": "autre",
}  # every other group is taken by mouth


def expand_form(form):
    """Clean the form text and fix typos and abbreviations."""
    text = clean_text(form)
    for pattern, replacement in FORM_TYPOS + FORM_ABBREVIATIONS:
        text = re.sub(pattern, replacement, text)
    return re.sub(r"\s+", " ", text).strip()


def form_group(form):
    """Map one of the ~680 form spellings to a group of about thirty.

    Modified/prolonged release and gastro-resistant forms are always kept in
    separate groups: they are never interchangeable with the immediate form.
    """
    text = expand_form(form)
    group = "autre"
    for name, pattern in FORM_RULES:
        if not re.search(pattern, text):
            continue
        if name in ("voie vaginale", "suppositoire ou voie rectale") and re.search(ORAL_HINT, text):
            continue
        group = name
        break

    if re.search(MODIFIED_RELEASE, text):
        group += " — libération modifiée"
    elif re.search(GASTRO_RESISTANT, text):
        group += " — gastro-résistant"
    return group


def route(group):
    base = group.split(" — ")[0]
    return ROUTES.get(base, "orale")


# --------------------------------------------------------------------------
# Dose
# --------------------------------------------------------------------------

UNIT_ALIASES = {"UG": "MCG", "MEG": "MCG", "MCG": "MCG"}
UNITS = ["MCG", "MG", "NG", "G", "MUI", "KUI", "UI", "U", "ML", "L", "MMOL", "MEQ",
         "%", "DOSE", "SACHET"]
PART_RE = re.compile(r"^(\d+(?:\.\d+)?)?(" + "|".join(UNITS) + r")?$")


def format_number(x):
    x = round(x, 6)
    if x == int(x):
        return str(int(x))
    return f"{x:.6f}".rstrip("0").rstrip(".")


def normalize_part(part):
    """Normalize one side of a dose, e.g. "0.5G" -> "500MG". Returns None if unreadable."""
    match = PART_RE.match(part)
    if not match or not part:
        return None
    number, unit = match.groups()
    if unit is None:
        return None
    if number is None:
        return unit  # denominator without a number: "1MG/ML"
    value = float(number)
    if unit == "G":
        value, unit = value * 1000, "MG"
    elif unit == "L":
        value, unit = value * 1000, "ML"
    if unit == "MCG" and value >= 1000:
        value, unit = value / 1000, "MG"
    return format_number(value) + unit


def normalize_dose(value):
    """Return (normalized dose, verified).

    When the dose cannot be read, the cleaned text is kept and verified is False.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "", False

    # Excel stored some percentages as plain numbers: 0.01 means 1 %
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 0 < value < 1:
            return format_number(value * 100) + "%", True
        return format_number(float(value)), False

    text = clean_text(value)
    fallback = text
    text = re.sub(r"\([^)]*\)?", " ", text)   # remove text in parentheses
    text = re.split(r" OU ", text)[0]          # keep what comes before " OU "
    text = text.replace(",", ".").replace(" ", "").replace("*", "")
    for alias, unit in UNIT_ALIASES.items():
        text = re.sub(alias + r"(?=/|$|\d)", unit, text)
    text = re.sub(r"(?<=\d)O|O(?=\d)", "0", text)  # "1OOOUI" written with the letter O
    while re.search(r"(?<=\d)O", text):
        text = re.sub(r"(?<=\d)O", "0", text)

    if re.fullmatch(r"\d+(\.\d+)?", text):
        number = float(text)
        if 0 < number < 1:
            return format_number(number * 100) + "%", True
        return fallback, False

    parts = [normalize_part(p) for p in text.split("/")]
    if not parts or any(p is None for p in parts):
        return fallback, False
    return "/".join(parts), True


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------

def clean_registration(value):
    return re.sub(r"\s+", " ", str(value)).strip().upper() if pd.notna(value) else ""


ID_FIELDS = ["num_enregistrement", "nom_marque", "dosage_norm", "forme", "conditionnement"]


def make_id(row):
    """Stable id: the same presentation keeps the same id when the script is run again.

    Pharmacies' stock declarations point to this id, so it must not be a row number.
    """
    text = "|".join(row[f] for f in ID_FIELDS)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def build():
    """Clean the nomenclature and return (medicines, eligible mask)."""
    main_sheet = read_sheet(SHEET_MAIN)
    df = main_sheet[[c for c in COLUMNS if c in main_sheet.columns]].rename(columns=COLUMNS)

    excluded_numbers = set()
    for sheet in (SHEET_NOT_RENEWED, SHEET_WITHDRAWN):
        other = read_sheet(sheet)
        excluded_numbers |= {clean_registration(v) for v in other["N°ENREGISTREMENT"]}
    excluded_numbers.discard("")

    # The dose is normalized from the original cell, so that numbers stored by
    # Excel (0.01 = 1 %) can be recognized before they become text.
    dose = df["dosage"].map(normalize_dose)
    df["dosage_norm"] = dose.map(lambda d: d[0])
    df["dosage_verifie"] = dose.map(lambda d: d[1])

    for col in COLUMNS.values():
        if col in df.columns:
            df[col] = df[col].map(clean_text)
    df["num_enregistrement"] = df["num_enregistrement"].map(clean_registration)

    df = df.drop_duplicates().reset_index(drop=True)

    df["dci_cle"] = df["dci"].map(make_dci_key)
    df["molecule"] = df["dci"].map(make_molecule)
    df["forme_groupe"] = df["forme"].map(form_group)
    df["voie"] = df["forme_groupe"].map(route)
    df["type"] = df["type"].map(lambda t: TYPES.get(t, ""))
    df["origine"] = df["statut"].map(lambda s: ORIGINS.get(s, ""))
    df["disponible_officine"] = (df["p2"] == "OFF") & ~df["obs"].str.contains(
        "HOPITA|HOSPITALIERE", regex=True)
    df["exclu"] = df["num_enregistrement"].isin(excluded_numbers)

    df["equivalence_key"] = df["dci_cle"] + "|" + df["dosage_norm"] + "|" + df["forme_groupe"]

    # Medicines that can be suggested: sold in pharmacies, not withdrawn, with a dose
    eligible = df["disponible_officine"] & ~df["exclu"] & (df["dosage_norm"] != "")
    brands_by_key = df[eligible].groupby("equivalence_key")["nom_marque"].agg(set)
    df["nb_equivalents"] = [
        len(brands_by_key.get(key, set()) - {brand})
        for key, brand in zip(df["equivalence_key"], df["nom_marque"])
    ]

    df.insert(0, "id", df.apply(make_id, axis=1))
    duplicates = df[df["id"].duplicated(keep=False)]
    if not duplicates.empty:
        raise ValueError(f"Duplicate ids:\n{duplicates[['id'] + ID_FIELDS]}")
    return df, eligible


def main():
    df, eligible = build()
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df[OUTPUT_COLUMNS].to_csv(OUT_FILE, index=False, encoding="utf-8")

    print_summary(df, eligible)


def print_summary(df, eligible):
    n = len(df)
    pct = lambda part, total: f"{100 * part / total:.1f} %" if total else "-"
    print(f"Fichier écrit : {OUT_FILE.relative_to(ROOT)}")
    print(f"Médicaments                 : {n}")
    print(f"Vendus en pharmacie         : {int(df['disponible_officine'].sum())}")
    print(f"Exclus (non renouvelés/retirés) : {int(df['exclu'].sum())}")
    print(f"Dosages analysés            : {pct(df['dosage_verifie'].sum(), n)}")
    print(f"Groupes de forme            : {df['forme_groupe'].nunique()}")
    with_equivalent = (df.loc[eligible, "nb_equivalents"] > 0).sum()
    print(f"Avec au moins un équivalent : {pct(with_equivalent, eligible.sum())}"
          f" (sur {int(eligible.sum())} médicaments proposables)")


if __name__ == "__main__":
    main()
