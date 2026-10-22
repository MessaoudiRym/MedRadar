"""Find a medicine written in Arabic letters or in arabizi, WITHOUT any AI.

Arabic does not write short vowels and has no "p", "v" or hard "c", so
"غلوكوفاج" can be read GLOUKOUFAJ, GLUCOFAJ, GLUCOPHAGE... Instead of trying
every spelling one by one, every name of the nomenclature and the query are
written in the same "sound key": consonants only, one letter per sound.

    GLUCOPHAGE -> G L K F J        (C before O = K, PH = F, GE = J)
    غلوكوفاج   -> G L K F J        (غ = G, ك = K, ف = F, ج = J)
    glucofaj   -> G L K F J

Each Arabic letter stands for all its Latin spellings at once:
    ف = F / PH / V      ك ق = K / C / Q / CK     ج = J / G (before E, I)
    ش = CH / SH         خ = KH                    ت ط ث = T / TH
    ب = B / P           ز س ص = S / Z / C (before E, I)
    و ي ا ة = vowels (o / ou / u, i / y / e, a / e), not part of the key
Letters whose sound varies in Algeria (ق = K or G, ج = J or G) give several
keys. Keys are compared with the same typo tolerance as the normal search.
"""

import itertools
import re
import unicodedata

from rapidfuzz import fuzz, process

from .query_text import clean

# --------------------------------------------------------------------------
# Sound keys
# --------------------------------------------------------------------------

# Ordered: digraphs before single letters. Lowercase "g" = hard G kept apart.
LATIN_RULES = [
    (r"PH", "F"), (r"TH", "T"), (r"CH(?=[LR])", "K"), (r"SCH", "X"), (r"CH", "X"), (r"SH", "X"),
    (r"KH", "K"), (r"GH", "g"), (r"DJ", "J"), (r"QU", "K"), (r"CK", "K"),
    (r"GU(?=[EIY])", "g"), (r"G(?=[EIY])", "J"), (r"C(?=[EIY])", "S"), (r"C", "K"), (r"Q", "K"),
    (r"X", "KS"), (r"V", "F"), (r"W", ""), (r"P", "B"), (r"Z", "S"), (r"H", ""),
    (r"[AEIOUY]", ""), (r"g", "G"),
]
# Same rules keeping the vowels (A, I for E/I/Y, O for O/U): to choose between
# names with the same consonants, e.g. AMLOR and HUMLOR for "أملور"
SPELLING_RULES = [rule for rule in LATIN_RULES if rule[0] != r"[AEIOUY]"] + [
    (r"[EIY]", "I"), (r"U", "O")]

# Arabizi digits: 3 = ع, 7 = ح (no key), 5 = خ, 9 = ق, 6 = ط, 8 = غ, 2 = ء
ARABIZI_DIGITS = str.maketrans({"2": "", "3": "", "7": "", "5": "K", "9": "K", "6": "T", "8": "G"})

ARABIC_KEYS = {
    "ب": "B", "پ": "B", "ت": "T", "ط": "T", "ث": "T", "ج": "J", "خ": "K", "د": "D", "ذ": "D",
    "ض": "D", "ظ": "D", "ر": "R", "ز": "S", "س": "S", "ص": "S", "ش": "X", "غ": "G", "ف": "F",
    "ڤ": "F", "ق": "K", "ڨ": "G", "ك": "K", "گ": "G", "ل": "L", "م": "M", "ن": "N",
    # Vowels, ع, ح, ه, hamza: no key
}
ARABIC_VOWELS = {"ا": "A", "ة": "A", "و": "O", "ي": "I", "ى": "I"}
# Letters pronounced two ways in Algeria
ARABIC_ALTERNATIVES = {"ق": ("K", "G"), "ج": ("J", "G")}
MAX_KEYS = 8


def _squeeze(key: str) -> str:
    return re.sub(r"(.)\1+", r"\1", key)


def _apply(rules, text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).upper())
    text = re.sub(r"[^A-Z]", "", "".join(c for c in text if not unicodedata.combining(c)))
    for pattern, replacement in rules:
        text = re.sub(pattern, replacement, text)
    return _squeeze(text)


def latin_key(text: str) -> str:
    """Sound key of a Latin name: "GLUCOPHAGE 850" -> "GLKFJ"."""
    return _apply(LATIN_RULES, text)


def spelling(text: str) -> str:
    """Sounds with vowels, in any script: "AMLOR" and "أملور" -> "AMLOR"."""
    if re.search("[؀-ۿ]", text):
        return _squeeze("".join(ARABIC_VOWELS.get(c) or ARABIC_KEYS.get(c, "") for c in text))
    return _apply(SPELLING_RULES, text.translate(ARABIZI_DIGITS))


def arabizi_key(word: str) -> str:
    return latin_key(word.translate(ARABIZI_DIGITS))


def arabic_keys(word: str) -> list[str]:
    """All the sound keys of a word in Arabic letters (several for ق and ج)."""
    options = []
    for char in word:
        if char in ARABIC_ALTERNATIVES:
            options.append(ARABIC_ALTERNATIVES[char])
        elif char in ARABIC_KEYS:
            options.append((ARABIC_KEYS[char],))
    keys = []
    for combination in itertools.islice(itertools.product(*options), MAX_KEYS):
        key = _squeeze("".join(combination))
        if key and key not in keys:
            keys.append(key)
    return keys


def query_keys(text: str) -> list[str]:
    """Sound keys of a query in any script, for the whole query and for each word."""
    words = clean(text).split()
    keys = []

    def add(*new):
        keys.extend(k for k in new if k and k not in keys)

    per_word = []
    for word in words:
        if re.search("[؀-ۿ]", word):
            per_word.append(arabic_keys(word))
        elif re.search(r"\d", word):
            per_word.append([arabizi_key(word)])
        else:
            per_word.append([latin_key(word)])
    if len(per_word) > 1:  # whole query, words joined: "ليفو تيروكس"
        for combination in itertools.islice(itertools.product(*per_word), MAX_KEYS):
            add("".join(combination))
    for word_keys in per_word:
        add(*word_keys)
    return keys


# --------------------------------------------------------------------------
# Search by sound key
# --------------------------------------------------------------------------

MIN_KEY_LENGTH = 3      # shorter keys ("TR") match too many names: never "sure"
SHORT_KEY_SCORE = 75
# Final score: consonants and vowels. Consonants alone are too loose for Latin
# words ("zocor" and SUCRE both give S K R); written vowels must agree too.
KEY_WEIGHT, VOWEL_WEIGHT = 0.4, 0.6
MIN_FUZZY_KEY = 4       # typo tolerance only on longer keys
MIN_KEY_SCORE = 80
EXACT, PREFIX = 100, 85


class PhoneticIndex:
    """Sound keys of every searchable term of the normal search."""

    def __init__(self, index):
        self.index = index
        self.key_to_terms = {}
        for term in index.term_to_medicines:
            key = latin_key(term)
            if len(key) >= 2:
                self.key_to_terms.setdefault(key, []).append(term)
        self.keys = [k for k in self.key_to_terms if len(k) >= MIN_KEY_LENGTH]

    def search_scored(self, text, limit=10, prefix=False):
        """[(medicine, score 0-100)], best first. prefix=True while the patient types.

        Ties (same consonants) are broken by the vowels: AMLOR before HUMLOR.
        """
        best = {}  # medicine index -> (score, vowel similarity)
        spellings = [spelling(w) for w in clean(text).split()] + [spelling(clean(text))]

        def keep(term, key_score, cap=100):
            vowels = max(fuzz.ratio(s, spelling(term)) for s in spellings)
            score = min(cap, round(KEY_WEIGHT * key_score + VOWEL_WEIGHT * vowels))
            for i in self.index.term_to_medicines[term]:
                if (score, vowels) > best.get(i, (0, 0)):
                    best[i] = (score, vowels)

        for key in query_keys(text):
            if len(key) < MIN_KEY_LENGTH:
                # "طاهور" -> "TR": only an exact key, never a sure result
                # (while typing, "ليفو" -> "LF" is only the start of a word: skipped)
                for term in self.key_to_terms.get(key, ()) if len(key) == 2 and not prefix else ():
                    keep(term, EXACT, cap=SHORT_KEY_SCORE)
                continue
            for term in self.key_to_terms.get(key, ()):
                keep(term, EXACT)
            if prefix:
                for term_key in self.keys:
                    if term_key != key and term_key.startswith(key):
                        for term in self.key_to_terms[term_key]:
                            keep(term, PREFIX)
            if len(key) >= MIN_FUZZY_KEY:
                for term_key, score, _ in process.extract(key, self.keys, scorer=fuzz.ratio,
                                                          score_cutoff=MIN_KEY_SCORE, limit=None):
                    for term in self.key_to_terms[term_key]:
                        keep(term, round(score))

        medicines = self.index.medicines
        ranked = sorted(best, key=lambda i: (-best[i][0], -best[i][1], self.index.brands[i],
                                             medicines[i]["id"]))
        return [(medicines[i], best[i][0]) for i in ranked[:limit]]


def key_similarity(name: str, text: str) -> int:
    """0-100: does `name` (Latin, e.g. proposed by the model) sound like `text` (any script)?"""
    target = latin_key(name)
    if not target:
        return 0
    return max((fuzz.ratio(target, key) for key in query_keys(text)), default=0)
