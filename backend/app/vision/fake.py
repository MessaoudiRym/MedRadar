"""Simulated reader: answers given in advance, no network call.

Used by the tests, and by the end-to-end tests (LLM_PROVIDER=fake), where it
always "reads" a GLUCOPHAGE 850 box.
"""

import json

DEMO_ANSWER = {
    "type_image": "boite_medicament",
    "nom_marque": "GLUCOPHAGE",
    "dci": "Metformine chlorhydrate",
    "dosage": "850 mg",
    "forme": "comprimé pelliculé",
    "lisible": True,
}


class FakeReader:
    name = "fake"

    def __init__(self, *answers):
        """Each answer is a dict (sent as JSON), a raw string, or an exception to raise.
        The last answer is repeated once the others are used."""
        self.answers = list(answers) or [DEMO_ANSWER]
        self.calls = 0
        self.last_image = None  # checked by the tests (prepared JPEG); never written anywhere

    def read(self, image_jpeg: bytes) -> str:
        self.calls += 1
        self.last_image = image_jpeg
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return json.dumps(answer) if isinstance(answer, dict) else answer
