import requests

from ai_search.config import TYPEAHEAD_ENTITIES, TYPEAHEAD_SIZE, TYPEAHEAD_URL
from ai_search.schemas import ParsedSearchIntent, ResolvedLocation


class LocationResolveError(Exception):
    pass


TYPEAHEAD_BUCKET = {
    "city": "cities",
    "neighborhood": "neighborhoods",
    "zipcode": "zips",
}


def _fetch_typeahead(input_text: str) -> dict:
    response = requests.get(
        TYPEAHEAD_URL,
        params={
            "size": TYPEAHEAD_SIZE,
            "input": input_text,
            "mode": "extended",
            "entities": TYPEAHEAD_ENTITIES,
        },
        timeout=15,
    )
    response.raise_for_status()
    body = response.json()
    return body.get("data") or {}


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _score_candidate(item: dict, intent: ParsedSearchIntent) -> tuple[int, int]:
    name = item.get("name") or item.get("city") or ""
    score = 0

    if _normalize(name) == _normalize(intent.location_text):
        score += 100
    elif _normalize(intent.location_text) in _normalize(name):
        score += 50

    if intent.state and (item.get("state") or "").upper() == intent.state.upper():
        score += 30

    listing_count = item.get("listing_count") or 0
    if listing_count > 0:
        score += min(listing_count, 20)

    return score, listing_count


def _pick_best(candidates: list[dict], intent: ParsedSearchIntent) -> dict | None:
    if not candidates:
        return None

    ranked = sorted(candidates, key=lambda item: _score_candidate(item, intent), reverse=True)
    best = ranked[0]
    best_score, _ = _score_candidate(best, intent)
    if best_score <= 0:
        return None
    return best


def _to_resolved(location_type: str, item: dict) -> ResolvedLocation:
    name = item.get("name") or item.get("city") or ""
    return ResolvedLocation(
        type=location_type,
        name=name if location_type != "zipcode" else (item.get("zip") or name),
        state=(item.get("state") or "").upper(),
        id=item["id"],
        parent_city=item.get("city") if location_type == "neighborhood" else None,
    )


def resolve_location(intent: ParsedSearchIntent) -> ResolvedLocation:
    if not intent.location_text.strip():
        raise LocationResolveError("No location found in the query.")

    data = _fetch_typeahead(intent.location_text)

    search_order: list[str]
    if intent.location_type:
        search_order = [intent.location_type]
    elif intent.location_text.strip().isdigit() and len(intent.location_text.strip()) == 5:
        search_order = ["zipcode", "city", "neighborhood"]
    else:
        search_order = ["city", "neighborhood", "zipcode"]

    for location_type in search_order:
        bucket_key = TYPEAHEAD_BUCKET[location_type]
        items = data.get(bucket_key) or []
        if not items:
            continue
        best = _pick_best(items, intent)
        if best:
            return _to_resolved(location_type, best)

    raise LocationResolveError(f"Could not resolve location: {intent.location_text}")
