"""Google Gemini photo reader, free tier Flash model.

Uses the shared Gemini access (app/llm/gemini.py): structured output
(response_mime_type + response_json_schema), fallback model when the main one
is overloaded, no retry on "quota exceeded". base.read_box still validates
the answer.
"""

from google.genai import types

from ..llm.gemini import generate, get_client, json_config, models_with_fallback
from .base import INSTRUCTIONS, JSON_SCHEMA


class GeminiReader:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_seconds: int, fallback_model: str = ""):
        self.model = model
        self.models = models_with_fallback(model, fallback_model)
        self.client = get_client(api_key)
        self.config = json_config(INSTRUCTIONS, JSON_SCHEMA, timeout_seconds)

    def read(self, image_jpeg: bytes) -> str:
        contents = [
            types.Part.from_bytes(data=image_jpeg, mime_type="image/jpeg"),
            "Copy what is printed on this image, as JSON.",
        ]
        return generate(self.client, self.models, contents, self.config)
