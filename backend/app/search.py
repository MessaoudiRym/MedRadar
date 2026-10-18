"""Typo-tolerant search on brand name and active substance.

Results are ranked in tiers, so that an exact start always beats a guess:
    1. the brand name starts with the query         ("gluco"      -> GLUCOPHAGE)
    2. a word of the molecule starts with the query ("metformine" -> METFORMINE ...)
    3. the brand name or molecule contains the query
    4. approximate match with rapidfuzz             ("glucofage"  -> GLUCOPHAGE)
Inside a tier, the highest similarity score comes first.
"""

import re
import unicodedata

from rapidfuzz import fuzz, process

# Similarity (0-100) needed for an approximate match. "GLUCOFAGE" vs "GLUCOPHAGE" = 84.
MIN_FUZZY_SCORE = 75

TIER_BRAND_PREFIX = 0
TIER_MOLECULE_PREFIX = 1
TIER_CONTAINS = 2
TIER_FUZZY = 3


def normalize(text):
    """Uppercase, no accents, single spaces: "Métformine " -> "METFORMINE"."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text.upper()).strip()


def split_words(text):
    return [w for w in re.split(r"[ +/-]+", text) if w]


class SearchIndex:
    def __init__(self, medicines):
        self.medicines = medicines
        self.brands = [normalize(m["nom_marque"]) for m in medicines]
        self.molecules = [normalize(m["molecule"]) for m in medicines]
        self.molecule_words = [split_words(mol) for mol in self.molecules]

        # Every searchable term (full names and single words) -> medicines that contain it.
        # Comparing the query with single words lets "glucofage" match "GLUCOPHAGE 850".
        self.term_to_medicines = {}
        for i, (brand, molecule) in enumerate(zip(self.brands, self.molecules)):
            for term in {brand, molecule, *split_words(brand), *split_words(molecule)}:
                self.term_to_medicines.setdefault(term, set()).add(i)
        self.terms = list(self.term_to_medicines)

    def search(self, query, limit=10):
        q = normalize(query)
        best = {}  # medicine index -> (tier, -score)

        def keep(i, tier, score):
            rank = (tier, -score)
            if i not in best or rank < best[i]:
                best[i] = rank

        for i, (brand, molecule, words) in enumerate(
                zip(self.brands, self.molecules, self.molecule_words)):
            if brand.startswith(q):
                keep(i, TIER_BRAND_PREFIX, 100)
            elif molecule.startswith(q) or any(w.startswith(q) for w in words):
                keep(i, TIER_MOLECULE_PREFIX, 100)
            elif q in brand or q in molecule:
                keep(i, TIER_CONTAINS, 100)

        # Typos: similarity between the query and each term (edit distance, in %)
        matches = process.extract(q, self.terms, scorer=fuzz.ratio,
                                  score_cutoff=MIN_FUZZY_SCORE, limit=None)
        for term, score, _ in matches:
            for i in self.term_to_medicines[term]:
                keep(i, TIER_FUZZY, score)

        ranked = sorted(best, key=lambda i: (best[i], self.brands[i], self.medicines[i]["id"]))
        return [self.medicines[i] for i in ranked[:limit]]
