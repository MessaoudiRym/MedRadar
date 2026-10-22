"""Simulated query interpreter: answers given in advance, no network call.

Used by the tests, and by the end-to-end tests (LLM_PROVIDER=fake), where it
knows a few queries (DEMO_ANSWERS) and answers "inconnu" to the others.
"""

import json

from ..query_text import clean


def answer(type_, spellings=(), molecule=None, dose=None, language="ar"):
    return {"type": type_, "langue": language, "orthographes": list(spellings),
            "molecule_fr": molecule, "dosage": dose}


UNKNOWN_ANSWER = answer("inconnu", language="autre")
DEMO_ANSWERS = {
    "غلوكوفاج": answer("nom_marque", ["GLUCOPHAGE"], "METFORMINE"),
    "ميتفورمين": answer("molecule", ["METFORMINE"], "METFORMINE"),
    "metformin": answer("molecule", ["METFORMINE"], "METFORMINE", language="en"),
    "tylenol": answer("marque_etrangere", ["TYLENOL"], "PARACETAMOL", language="en"),
}


class FakeInterpreter:
    name = "fake"

    def __init__(self, *answers, by_query=None):
        """Each answer is a dict (sent as JSON), a raw string, or an exception to raise.
        The last answer is repeated once the others are used. Without answers, the
        answer is looked up in by_query (default DEMO_ANSWERS), else "inconnu"."""
        self.answers = list(answers)
        self.by_query = DEMO_ANSWERS if by_query is None else by_query
        self.calls = 0
        self.queries = []

    def interpret(self, query: str) -> str:
        self.calls += 1
        self.queries.append(query)
        if self.answers:
            result = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        else:
            result = self.by_query.get(clean(query), UNKNOWN_ANSWER)
        if isinstance(result, Exception):
            raise result
        return json.dumps(result) if isinstance(result, dict) else result
