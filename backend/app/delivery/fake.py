"""Simulated delivery note reader: answers given in advance, no network call.

Used by the tests, and by the end-to-end tests (LLM_PROVIDER=fake), where it
always "reads" the demo note (app/delivery/demo_note.py).
"""

import json

from .demo_note import reader_answer


class FakeDeliveryReader:
    name = "fake"

    def __init__(self, *answers):
        """Each answer is a dict (sent as JSON), a raw string, or an exception to raise.
        The last answer is repeated once the others are used."""
        self.answers = list(answers) or [reader_answer()]
        self.calls = 0
        self.last_pages = None  # checked by the tests (prepared JPEG pages)

    def read(self, pages_jpeg: list[bytes]) -> str:
        self.calls += 1
        self.last_pages = pages_jpeg
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if isinstance(answer, Exception):
            raise answer
        return json.dumps(answer) if isinstance(answer, dict) else answer
