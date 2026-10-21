"""Errors of a language model provider, the same for every feature that uses one.

The messages are for the logs only, never for the client.
"""


class LLMError(Exception):
    """The model could not give a usable answer."""


class QuotaExceeded(LLMError):
    """The provider refused the request: too many requests (free tier quota, 429)."""


class ProviderBusy(LLMError):
    """The provider is overloaded for a moment (503), even with the fallback model."""


class LLMTimeout(LLMError):
    pass


class InvalidAnswer(LLMError):
    """The model did not answer with the expected JSON, even after a new try."""


class LLMUnavailable(LLMError):
    """Any other provider error (network, key refused, server error)."""
