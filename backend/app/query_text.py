"""What a patient typed, prepared WITHOUT any AI.

    "Dwa ta3 Glucophage ٨٥٠" -> words ["dwa", "ta3", "glucophage", "850"]
                             -> name words ["glucophage"], dose "850",
                                language "arabizi" (dwa, ta3)
"""

import re
import unicodedata
from dataclasses import dataclass, field

from .health_terms import health_words

# Arabic letters (all Unicode blocks, including presentation forms)
ARABIC = re.compile("[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")
# Arabic-Indic and Persian digits -> 0-9: "٨٥٠" -> "850"
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# Letter variants written interchangeably
ARABIC_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي",
                                "ـ": None})  # tatweel (stretching)

# Linking words that are never part of a medicine name
FILLER_WORDS = {
    # "medicine" in every language of the patients
    "dwa", "dwaa", "dawa", "دوا", "دواء", "الدوا", "الدواء",
    "medicament", "medicaments", "medoc", "medicine", "medicines", "medication", "drug", "drugs",
    "pill", "pills",
    # "of / for" in Darija, French and English
    "ta3", "taa3", "ta", "تاع", "نتاع", "ديال", "dyal", "ntaa3", "nta3",
    "de", "du", "des", "le", "la", "les", "l", "d", "un", "une", "pour", "et",
    "the", "of", "for", "a", "an", "my", "and",
    # "is there / do you have"
    "kayen", "kayn", "كاين", "3andkom", "عندكم", "wach", "wesh", "واش", "chi", "شي",
}

# Words that only Darija uses (Arabic script)
DARIJA_WORDS = {"تاع", "نتاع", "ديال", "واش", "كاين", "عندكم", "بزاف", "راس", "سخانة", "كرش", "شي"}
# Darija in Latin letters ("arabizi"), even without digits
ARABIZI_WORDS = {"dwa", "dwaa", "ta3", "taa3", "dyal", "wach", "wesh", "kayen", "kayn", "3andkom",
                 "rass", "sokar", "soukar", "skhana", "s5ana", "kerch"}
ENGLISH_WORDS = {"the", "for", "of", "medicine", "medicines", "medication", "drug", "drugs", "pill",
                 "pills", "tablet", "tablets", "syrup", "headache", "pain", "fever", "cough",
                 "blood", "pressure", "diabetes", "stomach", "ache", "my", "what", "and"}

# A dose written in the query: "850", "850mg", "0,5 g", "100 µg"
UNITS = r"(?:mg|g|mcg|µg|μg|ug|ml|ui|%)"
DOSE_WORD = re.compile(rf"^\d+(?:[.,]\d+)?{UNITS}?$")
UNIT_WORD = re.compile(rf"^{UNITS}$")


@dataclass
class Query:
    original: str
    cleaned: str                 # lowercase, no accents, Arabic digits and letters normalized
    words: list[str]
    name_words: list[str]        # without linking words, disease words and dose
    health: list[str] = field(default_factory=list)
    dose: str | None = None      # "850" or "850mg"
    language: str = "fr"

    @property
    def name(self) -> str:
        return " ".join(self.name_words)


def clean(text: str) -> str:
    """Lowercase, no accents or Arabic diacritics, single spaces, digits 0-9."""
    text = unicodedata.normalize("NFKC", str(text)).translate(DIGITS).translate(ARABIC_LETTERS)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))  # é -> e, Arabic vowel marks
    text = text.lower()
    text = re.sub(r"[^\w%.,/µμ]+", " ", text)  # punctuation -> space (keeps "0,5" and "%")
    return re.sub(r"\s+", " ", text).strip(" .,/")


def is_arabizi_word(word: str) -> bool:
    """Latin letters mixed with the digits Darija uses for Arabic sounds (3, 7, 9...)."""
    return (bool(re.search(r"[a-z]", word)) and bool(re.search(r"[235-9]", word))
            and not DOSE_WORD.match(word))


def is_english_molecule(word: str) -> bool:
    """English names of molecules drop the final "e" of the French name:
    metformin(e), atorvastatin(e), ibuprofen(e), acetaminophen."""
    return len(word) >= 6 and word.isalpha() and (
        (word.endswith("in") and not word.endswith("ine")) or word.endswith("en"))


def detect_language(words: list[str], text: str) -> str:
    if ARABIC.search(text):
        return "darija" if any(w in DARIJA_WORDS for w in words) else "ar"
    if any(is_arabizi_word(w) or w in ARABIZI_WORDS for w in words):
        return "arabizi"
    if any(w in ENGLISH_WORDS or is_english_molecule(w) for w in words):
        return "en"
    return "fr"


def split_dose(words: list[str]) -> tuple[str | None, list[str]]:
    """("850mg", other words): the first dose written, with its unit if any."""
    dose, rest, i = None, [], 0
    while i < len(words):
        word = words[i]
        if dose is None and DOSE_WORD.match(word):
            dose = word
            if i + 1 < len(words) and UNIT_WORD.match(words[i + 1]) and not re.search(r"[a-z%µμ]", word):
                dose += words[i + 1]
                i += 1
        else:
            rest.append(word)
        i += 1
    return dose, rest


def analyze(text: str) -> Query:
    cleaned = clean(text)
    words = [w for w in (w.strip(".,/") for w in cleaned.split()) if w]
    language = detect_language(words, cleaned)
    dose, rest = split_dose(words)
    health = health_words(rest)
    name_words = [w for w in rest
                  if w not in FILLER_WORDS and w not in health and not UNIT_WORD.match(w)]
    return Query(original=text, cleaned=cleaned, words=words, name_words=name_words,
                 health=health, dose=dose, language=language)
