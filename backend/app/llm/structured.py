"""Ask a model for JSON and check it with Pydantic, whatever the provider."""

import logging
from collections.abc import Callable

from pydantic import BaseModel, ValidationError

from .errors import InvalidAnswer

logger = logging.getLogger("medradar")

# Invalid JSON from the model: one more try, then a clean error
RETRIES_ON_INVALID_ANSWER = 1


def ask_validated[T: BaseModel](produce: Callable[[], str], model: type[T], what: str) -> T:
    """Call produce() (the raw answer of the model) until it fits `model`.

    Provider errors (quota, timeout...) are never retried here.
    """
    for attempt in range(1 + RETRIES_ON_INVALID_ANSWER):
        raw = produce()
        try:
            return model.model_validate_json(raw)
        except ValidationError:
            # Never log the answer itself: it comes from a patient's photo or query
            logger.warning("%s: invalid answer from the model (attempt %d)", what, attempt + 1)
    raise InvalidAnswer(f"{what}: no valid answer from the model")
