"""Multilingual search: French, Arabic, Darija, arabizi and English.

GOLDEN RULE, guaranteed by this code and not only by the model's instructions:
the language model only understands and translates NAMES (a brand name or an
active ingredient). It never goes from a disease, a symptom or a use to a
medicine, and every result comes from the official nomenclature:

    1. disease and symptom words are caught here, BEFORE any call to the model
       (app/health_terms.py): no name recognized -> no result;
    2. a model answer "maladie_ou_symptome" -> no result, whatever else it says;
    3. a name proposed by the model must sound like what the patient typed
       (same sound key, app/transliteration.py), or it is ignored;
    4. a dose proposed by the model must be written in the query;
    5. only medicines found in the database are returned: never a made-up name.

While the patient types (interpret=false) the model is never called. When the
patient validates the search (interpret=true), the model is asked only when it
can help (ARABIC_SEARCH_MODE), with a 30-day cache and 20 calls per hour per
IP. If it is missing, slow, over quota or wrong, the search silently uses the
transliteration rules instead.
"""

import logging
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from datetime import timedelta

from limits import parse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .db import utcnow
from .limiter import limiter
from .llm.interpreter import (BRAND, DISEASE, FOREIGN_BRAND, MOLECULE, QueryReading,
                              interpret_query)
from .models import InterpretationCache
from .query_text import Query, analyze
from .recognition import brand_core, normalize_dose
from .search import normalize, split_words
from .transliteration import key_similarity

logger = logging.getLogger("medradar")

CONFIDENT = 80          # a result at least this sure (0-100) needs no help from the model
RECOGNIZED = 90         # next to a disease word, a medicine name must be this sure
# For a Latin query that is not arabizi, the normal search already tolerates typos:
# a transliteration match is "sure" only when nearly perfect ("glucofaj", "amlour"),
# so that a foreign name ("zocor") is not mistaken for a sound-alike word (SUCRE)
LATIN_RULES_SURE = 95
GROUNDED = 70           # a name from the model must sound like the query at least this much
MAX_NAME_WORDS = 5      # longer queries are sentences, not names: never sent to the model
MAX_UNGROUNDED_WORDS = 3  # "acetaminophen" -> PARACETAMOL: only for a short query
LLM_DEADLINE_SECONDS = 8
LLM_RATE_LIMIT = parse("20/hour")  # calls to the model per IP; cached answers do not count
CACHE_DAYS = 30
LLM_LANGUAGES = {"ar", "darija", "arabizi", "en"}
ARABIC_LIKE = {"ar", "darija", "arabizi"}

DISEASE_MESSAGE = (
    "MedRadar ne choisit pas de médicament à partir d'une maladie ou d'un symptôme. "
    "Tapez le nom inscrit sur la boîte ou l'ordonnance, ou demandez conseil à votre pharmacien.")
FOREIGN_MESSAGE = (
    "« {query} » n'est pas vendu en Algérie sous ce nom. Il contient {molecule} : voici les "
    "médicaments enregistrés en Algérie qui en contiennent. Demandez conseil à votre pharmacien.")
NO_RESULT_MESSAGE = ("Aucun médicament de la nomenclature ne correspond à « {query} ». "
                     "Essayez le nom écrit sur la boîte.")

# The model is called in a thread so that the search stops waiting after 8 s
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="query-interpreter")


@dataclass
class Hit:
    medicine: dict
    score: float          # 0-100
    source: str           # "search" (normal search) or "rules" (transliteration)


def merge(*lists):
    """Best score per medicine, best first. A medicine found by several lists keeps
    the source of the first one (the normal search) and the best score."""
    best = {}
    for hits in lists:
        for hit in hits:
            current = best.get(hit.medicine["id"])
            if current is None:
                best[hit.medicine["id"]] = hit
            elif hit.score > current.score:
                best[hit.medicine["id"]] = Hit(current.medicine, hit.score, current.source)
    return sorted(best.values(), key=lambda h: -h.score)


def dose_matches(dose, dosage_norm):
    """"850" matches 850MG; "850mg" matches 850MG exactly; "50" matches 50MCG."""
    number = re.match(r"\d+(?:[.,]\d+)?", dose)
    if not number:
        return False
    if re.search(r"[a-z%µμ]", dose):
        normalized = normalize_dose(dose.replace("μ", "µ"))[0]
        return dosage_norm == normalized or dosage_norm.startswith(normalized + "/")
    value = re.escape(number.group().replace(",", "."))
    return re.match(rf"{value}(?![\d.])", dosage_norm) is not None


def order_by_dose(hits, dose):
    """The presentations with the dose written by the patient come first."""
    if not dose:
        return hits
    return sorted(hits, key=lambda h: 0 if dose_matches(dose, h.medicine["dosage_norm"]) else 1)


def dose_label(dose, medicine=None):
    """"850mg" -> "850 MG"; "850" -> the matching dose of the medicine ("850 MG")."""
    if medicine is not None and dose_matches(dose, medicine["dosage_norm"]):
        text = medicine["dosage_norm"]
    elif re.search(r"[a-z%µμ]", dose):
        text = normalize_dose(dose.replace("μ", "µ"))[0]
    else:
        text = dose
    return re.sub(r"(\d)([A-Z%])", r"\1 \2", text)


def grounded_dose(model_dose, query: Query):
    """A dose from the model is kept only if its number is written in the query."""
    if not model_dose:
        return None
    number = re.match(r"\d+(?:[.,]\d+)?", model_dose.strip())
    if not number or number.group() not in re.findall(r"\d+(?:[.,]\d+)?", query.cleaned):
        return None
    return model_dose.strip().lower().replace(" ", "")


class SmartSearch:
    def __init__(self, store, index, phonetic):
        self.store = store
        self.index = index
        self.phonetic = phonetic
        # Substances of each medicine, to find every medicine with a given molecule
        self.molecules = [(m, set(split_words(normalize(m["molecule"]))), m["molecule"].count("+") + 1)
                          for m in store.records]

    # ----------------------------------------------------------------------
    # Without the model
    # ----------------------------------------------------------------------

    def rules(self, query: Query, limit, prefix=False):
        """Normal search, then the transliteration rules when they can help."""
        found = [Hit(m, s, "search")
                 for m, s in self.index.search(query.name, limit, with_scores=True)]
        exact = found and found[0].score >= 100
        # A typo ("levotirox"): the sound key tells LEVOTHYROX from LEVOTIRON
        if query.language in ARABIC_LIKE or not exact:
            by_sound = self.phonetic.search_scored(query.name, limit, prefix)
            if query.language not in ARABIC_LIKE:
                by_sound = [(m, sc if sc >= LATIN_RULES_SURE else min(sc, CONFIDENT - 1))
                            for m, sc in by_sound]
            found = merge(found, [Hit(m, sc, "rules") for m, sc in by_sound])
        return found

    def recognized(self, query: Query):
        """Is there clearly a medicine name in the query (besides disease words)?"""
        if not query.name_words:
            return False
        found = self.rules(query, 5)
        return bool(found) and found[0].score >= RECOGNIZED

    def suggest(self, text, limit):
        """While typing (interpret=false): never the model."""
        query = analyze(text)
        if query.health and not self.recognized(query):
            return []
        if not query.name_words:
            return self.index.search(text, limit)  # e.g. only a dose: unchanged behaviour
        hits = order_by_dose(self.rules(query, limit * 3, prefix=True), query.dose)
        return [h.medicine for h in hits[:limit]]

    # ----------------------------------------------------------------------
    # Validated search (interpret=true)
    # ----------------------------------------------------------------------

    def search(self, text, limit, db, ip, interpreter, mode):
        query = analyze(text)
        logger.info("Search: language=%s words=%d", query.language, len(query.words))

        # Safety net 1: a disease or a symptom, and no medicine name
        if query.health and not self.recognized(query):
            return self.refusal(query, "regles")
        if not query.name_words:
            return self.no_result(query)

        found = self.rules(query, limit * 3)
        sure = bool(found) and found[0].score >= CONFIDENT
        if mode == "llm_first":
            ask_model = query.language in LLM_LANGUAGES or not sure
        else:
            ask_model = not sure

        if ask_model and len(query.name_words) <= MAX_NAME_WORDS:
            reading, method = self.interpret(query, db, ip, interpreter)
            if reading is not None:
                # Safety net 2: the model says it is a disease or a symptom
                if reading.type == DISEASE:
                    return self.refusal(query, method)
                answer = self.from_reading(query, reading, method, limit, sure)
                if answer is not None:
                    return answer
                if not sure:
                    # The model understood a name that is not in the nomenclature, and
                    # the rules are not sure either: nothing, rather than a guess
                    return self.no_result(query)
        return self.from_rules(query, found, limit)

    def interpret(self, query: Query, db, ip, interpreter):
        """(QueryReading, "cache" or "llm"), or (None, None): the rules are used instead."""
        key = query.cleaned[:200]
        cached = self.read_cache(db, key)
        if cached is not None:
            return cached, "cache"
        if interpreter is None:
            return None, None
        if not limiter.limiter.hit(LLM_RATE_LIMIT, "query-interpreter", ip):
            logger.warning("Search: 20 model calls per hour reached for this IP, rules used")
            return None, None
        future = _executor.submit(interpret_query, interpreter, query.cleaned)
        try:
            reading = future.result(timeout=LLM_DEADLINE_SECONDS)
        except FutureTimeout:
            logger.warning("Search: the model took more than %d s, rules used", LLM_DEADLINE_SECONDS)
            return None, None
        except Exception as error:  # quota, overloaded, invalid answer, network...
            logger.warning("Search: model unavailable (%s), rules used", type(error).__name__)
            return None, None
        self.write_cache(db, key, reading)
        return reading, "llm"

    def from_reading(self, query: Query, reading: QueryReading, method, limit, rules_sure):
        """Check every name proposed by the model against the database.

        A substance the patient did not write (acetaminophen -> PARACETAMOL, a
        foreign brand -> its substance) is only accepted for a molecule or a
        foreign brand, in a short query, and when the rules did not already
        recognize a name sold in Algeria.
        """
        dose = query.dose or grounded_dose(reading.dosage, query)

        # Safety net 3: only names that sound like what the patient typed
        named, spelling = [], None
        for candidate in reading.orthographes:
            if key_similarity(candidate, query.name) < GROUNDED:
                logger.info("Search: a name proposed by the model was ignored (not in the query)")
                continue
            hits = [Hit(m, s, "llm")
                    for m, s in self.index.search(candidate, limit * 3, with_scores=True)
                    if s >= CONFIDENT]
            if hits:
                named = merge(named, hits)
                spelling = spelling or candidate

        molecule = reading.molecule_fr
        molecule_grounded = bool(molecule) and key_similarity(molecule, query.name) >= GROUNDED
        molecule_allowed = bool(molecule) and (molecule_grounded or (
            reading.type in (MOLECULE, FOREIGN_BRAND) and not rules_sure
            and len(query.name_words) <= MAX_UNGROUNDED_WORDS))

        if named and reading.type != MOLECULE:
            # A brand sold in Algeria (also when the model thought it was foreign)
            hits = order_by_dose(named, dose)[:limit]
            exact = hits[0].score >= 100
            return self.answer(query, hits, method, BRAND, self.understood(spelling, dose, hits),
                               a_verifier=not exact)

        if reading.type == MOLECULE and (named or molecule_allowed):
            hits = merge(named, self.with_molecule(molecule) if molecule_allowed else [])
            if hits:
                hits = order_by_dose(hits, dose)[:limit]
                name = molecule if molecule_allowed else spelling
                return self.answer(query, hits, method, MOLECULE, self.understood(name, dose, hits),
                                   a_verifier=not (molecule_grounded or named))

        if reading.type in (FOREIGN_BRAND, BRAND) and molecule_allowed:
            hits = order_by_dose(self.with_molecule(molecule), dose)[:limit]
            if hits:
                message = FOREIGN_MESSAGE.format(query=query.original.strip(), molecule=molecule)
                return self.answer(query, hits, method, FOREIGN_BRAND,
                                   self.understood(molecule, dose, hits), a_verifier=True,
                                   message=message)
        return None  # nothing usable: the rules decide

    def with_molecule(self, molecule):
        """Every medicine containing this substance, single-substance medicines first."""
        words = set(split_words(normalize(molecule)))
        if not words:
            return []
        found = [(m, n) for m, substance, n in self.molecules if words <= substance]
        found.sort(key=lambda f: (f[1], f[0]["nom_marque"], f[0]["id"]))
        return [Hit(m, 100, "llm") for m, _ in found]

    def from_rules(self, query: Query, found, limit):
        if not found:
            return self.no_result(query)
        hits = order_by_dose(found, query.dose)[:limit]
        top = found[0]
        if top.source == "search":
            return self.answer(query, hits, "recherche", self.kind(top.medicine, query), None,
                               a_verifier=top.score < 100)
        name = self.rules_name(top.medicine, query)
        return self.answer(query, hits, "regles", self.kind(top.medicine, query),
                           self.understood(name, query.dose, hits), a_verifier=top.score < 100)

    # ----------------------------------------------------------------------
    # Answers
    # ----------------------------------------------------------------------

    def rules_name(self, medicine, query: Query):
        """The brand or the substance that the transliteration matched."""
        brand = brand_core(medicine["nom_marque"])
        if key_similarity(brand, query.name) >= CONFIDENT:
            return brand
        return medicine["molecule"]

    def kind(self, medicine, query: Query):
        brand = brand_core(medicine["nom_marque"])
        return BRAND if key_similarity(brand, query.name) >= CONFIDENT else MOLECULE

    @staticmethod
    def understood(name, dose, hits):
        if not name:
            return None
        if dose:
            return f"{name} {dose_label(dose, hits[0].medicine if hits else None)}"
        return name

    @staticmethod
    def interpretation(query: Query, method, type_, understood, a_verifier):
        return {
            "requete_originale": query.original,
            "langue_detectee": query.language,
            "methode": method,
            "compris_comme": understood,
            "type": type_,
            "a_verifier": a_verifier,
        }

    def answer(self, query, hits, method, type_, understood, a_verifier, message=None):
        return {
            "results": [h.medicine for h in hits],
            "interpretation": self.interpretation(query, method, type_, understood, a_verifier),
            "message": message,
        }

    def refusal(self, query: Query, method):
        return {
            "results": [],
            "interpretation": self.interpretation(query, method, DISEASE, None, False),
            "message": DISEASE_MESSAGE,
        }

    def no_result(self, query: Query):
        return {
            "results": [],
            "interpretation": self.interpretation(query, "recherche", "inconnu", None, False),
            "message": NO_RESULT_MESSAGE.format(query=query.original.strip()),
        }

    # ----------------------------------------------------------------------
    # Cache: a query is never sent to the model twice (30 days)
    # ----------------------------------------------------------------------

    @staticmethod
    def read_cache(db, key):
        try:
            row = db.scalar(select(InterpretationCache)
                            .where(InterpretationCache.requete_normalisee == key))
        except SQLAlchemyError:
            logger.exception("Search: cache unavailable")
            return None
        if row is None or utcnow() - row.cree_le > timedelta(days=CACHE_DAYS):
            return None
        try:
            return QueryReading.model_validate_json(row.reponse_json)
        except ValidationError:
            return None

    @staticmethod
    def write_cache(db, key, reading: QueryReading):
        try:
            row = db.scalar(select(InterpretationCache)
                            .where(InterpretationCache.requete_normalisee == key))
            if row is None:
                db.add(InterpretationCache(requete_normalisee=key,
                                           reponse_json=reading.model_dump_json()))
            else:  # expired: replaced
                row.reponse_json, row.cree_le = reading.model_dump_json(), utcnow()
            db.commit()
        except SQLAlchemyError:
            db.rollback()  # e.g. the same query saved at the same time by another request
            logger.warning("Search: the interpretation could not be cached")
