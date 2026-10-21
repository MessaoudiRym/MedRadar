"""Vision readers. To add a provider: write a class with name and read()
(see base.VisionReader), then add it to make_reader()."""

import logging

from ..config import LLM_API_KEY, LLM_MODEL, LLM_PROVIDER, LLM_TIMEOUT_SECONDS
from .base import VisionReader

logger = logging.getLogger("medradar")


def make_reader() -> VisionReader | None:
    """The configured reader, or None when photo recognition is off."""
    if LLM_PROVIDER == "fake":
        from .fake import FakeReader
        logger.warning("Photo recognition uses the FAKE reader (tests and demo only).")
        return FakeReader()
    if not LLM_API_KEY:
        logger.info("Photo recognition is off: LLM_API_KEY is not set.")
        return None
    if LLM_PROVIDER == "gemini":
        from .gemini import GeminiReader
        return GeminiReader(LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT_SECONDS)
    logger.error("Photo recognition is off: unknown LLM_PROVIDER %r (supported: gemini).",
                 LLM_PROVIDER)
    return None
