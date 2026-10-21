"""Google Gemini reader (official google-genai SDK), free tier Flash model.

Structured output (response_mime_type + response_json_schema) makes the model
answer in the expected JSON shape; base.read_box still validates it.
"""

import httpx
from google import genai
from google.genai import errors, types

from .base import (INSTRUCTIONS, JSON_SCHEMA, QuotaExceeded, ReaderTimeout,
                   ReaderUnavailable)


class GeminiReader:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: int):
        self.model = model
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000,  # milliseconds
                # No automatic retry: on "quota exceeded" the patient is told at once
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        self.config = types.GenerateContentConfig(
            system_instruction=INSTRUCTIONS,
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=JSON_SCHEMA,
        )

    def read(self, image_jpeg: bytes) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=image_jpeg, mime_type="image/jpeg"),
                    "Copy what is printed on this image, as JSON.",
                ],
                config=self.config,
            )
        # "from None": the provider's error is replaced, never shown to the client
        except errors.APIError as error:
            if error.code == 429:
                raise QuotaExceeded("Gemini quota exceeded") from None
            if error.code in (408, 504):
                raise ReaderTimeout("Gemini timeout") from None
            raise ReaderUnavailable(f"Gemini error {error.code}") from None
        except (httpx.TimeoutException, TimeoutError):
            raise ReaderTimeout("Gemini timeout") from None
        except httpx.HTTPError as error:
            raise ReaderUnavailable(f"Gemini network error: {type(error).__name__}") from None
        # Empty when the answer was blocked: treated as an invalid answer
        return response.text or ""
