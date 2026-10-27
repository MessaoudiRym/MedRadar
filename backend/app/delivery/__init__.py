"""Delivery note scan for pharmacists: the model reads, our code matches, the
pharmacist confirms. To add a provider: write a class with name and read()
(see reader.DeliveryNoteReader), then add it to make_delivery_reader()."""

import logging

from ..config import (DELIVERY_TIMEOUT_SECONDS, LLM_API_KEY, LLM_FALLBACK_MODEL, LLM_MODEL,
                      LLM_PROVIDER)
from .reader import DeliveryNoteReader

logger = logging.getLogger("medradar")


def make_delivery_reader() -> DeliveryNoteReader | None:
    """The configured reader, or None when the scan is off (the history still works)."""
    if LLM_PROVIDER == "fake":
        from .fake import FakeDeliveryReader
        logger.warning("Delivery note scan uses the FAKE reader (tests and demo only).")
        return FakeDeliveryReader()
    if not LLM_API_KEY:
        logger.info("Delivery note scan is off: LLM_API_KEY is not set.")
        return None
    if LLM_PROVIDER == "gemini":
        from .reader import GeminiDeliveryReader
        return GeminiDeliveryReader(LLM_API_KEY, LLM_MODEL, DELIVERY_TIMEOUT_SECONDS,
                                    LLM_FALLBACK_MODEL)
    logger.error("Delivery note scan is off: unknown LLM_PROVIDER %r.", LLM_PROVIDER)
    return None
