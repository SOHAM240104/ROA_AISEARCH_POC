from ai_search.gemini_parser import parse_search_intent
from ai_search.location_resolver import resolve_location
from ai_search.url_builder import build_search_url


def run_ai_search(query: str, api_key: str | None = None) -> dict:
    intent = parse_search_intent(query, api_key=api_key)
    location = resolve_location(intent)
    url, query_params = build_search_url(intent, location)

    return {
        "url": url,
        "query_params": query_params,
        "interpretation": intent.interpretation,
        "parsed_intent": intent.model_dump(),
        "resolved_location": location.model_dump(),
    }
