import os

from google import genai
from google.genai import types

from ai_search.config import GEMINI_MODEL, GEMINI_MODEL_FALLBACKS
from ai_search.env_loader import load_dotenv
from ai_search.prompts import SEARCH_INTENT_SYSTEM_PROMPT
from ai_search.schemas import ParsedSearchIntent

load_dotenv()


class GeminiParseError(Exception):
    pass


def _parse_response(response) -> ParsedSearchIntent:
    if response.parsed is not None:
        if isinstance(response.parsed, ParsedSearchIntent):
            return response.parsed
        return ParsedSearchIntent.model_validate(response.parsed)

    if response.text:
        return ParsedSearchIntent.model_validate_json(response.text)

    raise GeminiParseError("Gemini returned an empty response.")


def parse_search_intent(query: str, api_key: str | None = None) -> ParsedSearchIntent:
    api_key = (api_key or os.environ.get("GEMINI_API_KEY", "")).strip()
    if not api_key:
        raise GeminiParseError("Gemini API key is required. Set GEMINI_API_KEY in .env.")

    client = genai.Client(api_key=api_key)
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
            return _parse_response(response)
        except GeminiParseError:
            raise
        except Exception as exc:
            last_error = exc

    raise GeminiParseError(f"Gemini request failed for all models ({', '.join(models)}): {last_error}")
