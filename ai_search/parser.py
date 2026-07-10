"""Parse natural-language queries into structured search intent via Gemini."""

import os

from google import genai
from google.genai import types

from ai_search.config import GEMINI_MODEL, GEMINI_MODEL_FALLBACKS
from ai_search.prompts import SEARCH_INTENT_SYSTEM_PROMPT
from ai_search.schemas import ParsedSearchIntent

_client: genai.Client | None = None
_client_key: str | None = None


class GeminiParseError(Exception):
    pass


def parse_intent(query: str, api_key: str | None = None) -> ParsedSearchIntent:
    api_key = _resolve_api_key(api_key)
    if not api_key:
        raise GeminiParseError("Set GEMINI_API_KEY in .env or Streamlit Secrets.")

    client = _get_client(api_key)
    models = [GEMINI_MODEL, *GEMINI_MODEL_FALLBACKS]
    last_error: Exception | None = None

    for model_name in models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=query.strip(),
                config=types.GenerateContentConfig(
                    system_instruction=SEARCH_INTENT_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ParsedSearchIntent,
                    temperature=0.1,
                ),
            )
            return _to_intent(response)
        except GeminiParseError:
            raise
        except Exception as exc:
            last_error = exc

    raise GeminiParseError(f"Gemini failed for all models ({', '.join(models)}): {last_error}")


def _to_intent(response) -> ParsedSearchIntent:
    if response.parsed is not None:
        if isinstance(response.parsed, ParsedSearchIntent):
            return response.parsed
        return ParsedSearchIntent.model_validate(response.parsed)
    if response.text:
        return ParsedSearchIntent.model_validate_json(response.text)
    raise GeminiParseError("Gemini returned an empty response.")


def _get_client(api_key: str) -> genai.Client:
    global _client, _client_key
    if _client is None or _client_key != api_key:
        _client = genai.Client(api_key=api_key)
        _client_key = api_key
    return _client


def _resolve_api_key(api_key: str | None) -> str:
    if api_key and api_key.strip():
        return api_key.strip()
    env_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        return env_key
    try:
        import streamlit as st

        secret = st.secrets.get("GEMINI_API_KEY", "")
        if secret:
            return str(secret).strip()
    except Exception:
        pass
    return ""
