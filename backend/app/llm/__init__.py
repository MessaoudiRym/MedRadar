"""Language model access shared by the features (Gemini, or a fake one for the tests).

To add a provider: write a class with name and interpret() (see
interpreter.QueryInterpreter), then add it to make_interpreter().
"""

import logging

from ..config import LLM_API_KEY, LLM_FALLBACK_MODEL, LLM_MODEL, LLM_PROVIDER
from .interpreter import QueryInterpreter

logger = logging.getLogger("medradar")

# Server-side deadline of one call (the Gemini minimum); the search itself
# stops waiting earlier (app/smart_search.py)
INTERPRETER_TIMEOUT_SECONDS = 10


def make_interpreter() -> QueryInterpreter | None:
    """The configured query interpreter, or None: the search then uses rules only."""
    if LLM_PROVIDER == "fake":
        from .fake import FakeInterpreter
        logger.warning("Multilingual search uses the FAKE interpreter (tests and demo only).")
        return FakeInterpreter()
    if not LLM_API_KEY:
        logger.info("Multilingual search uses rules only: LLM_API_KEY is not set.")
        return None
    if LLM_PROVIDER == "gemini":
        from .interpreter import GeminiInterpreter
        return GeminiInterpreter(LLM_API_KEY, LLM_MODEL, INTERPRETER_TIMEOUT_SECONDS,
                                 LLM_FALLBACK_MODEL)
    logger.error("Multilingual search uses rules only: unknown LLM_PROVIDER %r.", LLM_PROVIDER)
    return None
