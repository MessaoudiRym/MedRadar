"""Google Gemini access shared by every feature (official google-genai SDK).

One client per API key, the same error handling everywhere:
- structured output: response_mime_type="application/json" + a JSON schema;
- when the main model is overloaded (503 "high demand", frequent on the free
  tier), the fallback model is tried once;
- "quota exceeded" (429) is never retried.
"""

from functools import lru_cache

import httpx
from google import genai
from google.genai import errors, types

from .errors import LLMTimeout, LLMUnavailable, ProviderBusy, QuotaExceeded

OVERLOADED = 503
# The Gemini API refuses a shorter deadline ("Minimum allowed deadline is 10s"):
# a shorter wait is enforced by the caller (app/smart_search.py)
MIN_DEADLINE_SECONDS = 10
# No automatic retry by the SDK: on "quota exceeded" the patient is told at once
NO_RETRY = types.HttpRetryOptions(attempts=1)


@lru_cache(maxsize=4)
def get_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key, http_options=types.HttpOptions(retry_options=NO_RETRY))


def json_config(instructions: str, schema: dict, timeout_seconds: float,
                thinking: types.ThinkingLevel | None = None) -> types.GenerateContentConfig:
    """Settings of one kind of request: instructions, JSON schema, time limit."""
    return types.GenerateContentConfig(
        system_instruction=instructions,
        temperature=0,
        response_mime_type="application/json",
        response_json_schema=schema,
        thinking_config=types.ThinkingConfig(thinking_level=thinking) if thinking else None,
        http_options=types.HttpOptions(timeout=int(max(timeout_seconds, MIN_DEADLINE_SECONDS) * 1000),
                                       retry_options=NO_RETRY),
    )


def models_with_fallback(model: str, fallback_model: str) -> list[str]:
    return [model] + ([fallback_model] if fallback_model and fallback_model != model else [])


def generate(client: genai.Client, models: list[str], contents, config) -> str:
    """The raw answer (JSON text) of the first model that is not overloaded."""
    for model in models:
        try:
            return _generate_with(client, model, contents, config)
        except ProviderBusy:
            continue  # overloaded: try the fallback model once
    raise ProviderBusy("Gemini overloaded")


def _generate_with(client, model, contents, config) -> str:
    try:
        response = client.models.generate_content(model=model, contents=contents, config=config)
    # "from None": the provider's error is replaced, never shown to the client
    except errors.APIError as error:
        if error.code == 429:
            raise QuotaExceeded("Gemini quota exceeded") from None
        if error.code == OVERLOADED:
            raise ProviderBusy(f"{model} overloaded") from None
        if error.code in (408, 504):
            raise LLMTimeout("Gemini timeout") from None
        raise LLMUnavailable(f"Gemini error {error.code}") from None
    except (httpx.TimeoutException, TimeoutError):
        raise LLMTimeout("Gemini timeout") from None
    except httpx.HTTPError as error:
        raise LLMUnavailable(f"Gemini network error: {type(error).__name__}") from None
    # Empty when the answer was blocked: treated as an invalid answer
    return response.text or ""
