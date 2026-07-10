"""RealStaq staging API — typeahead location resolve and MLS listing search."""

import math

import requests

from ai_search.config import (
    HTTP_TIMEOUT,
    LIST_TYPE_TO_MLS_STATUSES,
    MAX_MULTI_LOCATION_DISTANCE_MILES,
    MLS_ADDRESS_PAGE_SIZE,
    MLS_LISTINGS_URL,
    TYPEAHEAD_ENTITIES,
    TYPEAHEAD_SIZE,
    TYPEAHEAD_URL,
)
from ai_search.schemas import LocationInquiry, ParsedSearchIntent, ResolvedLocation

_session = requests.Session()

_TYPEAHEAD_BUCKET = {"city": "cities", "neighborhood": "neighborhoods", "zipcode": "zips"}


class LocationResolveError(Exception):
    pass


class MlsSearchError(Exception):
    pass


def resolve_locations(intent: ParsedSearchIntent) -> tuple[list[ResolvedLocation], str | None]:
    """
    Resolve one or more locations via typeahead.
    Returns (locations, warning) — warning set when multi-location was downgraded.
    """
    inquiries = intent.locations
    if not inquiries:
        raise LocationResolveError("No location found in the query.")

    resolved = [_resolve_one(inquiry, intent.state) for inquiry in inquiries]

    if len(resolved) == 1:
        return resolved, None

    compatible, reason = _are_compatible(resolved)
    if compatible:
        return resolved, None

    primary = _pick_primary_location(resolved)
    return [primary], f"Locations are not close enough to combine ({reason}). Using {primary.name} only."


def resolve_location(intent: ParsedSearchIntent) -> ResolvedLocation:
    locations, _ = resolve_locations(intent)
    return locations[0]


def search_by_address(intent: ParsedSearchIntent) -> dict:
    """POST MLS search for a street address. Returns {total_elements, listings}."""
    address_line = (intent.address_line or "").strip()
    city = (intent.location_text or "").strip()
    state = (intent.state or "").strip().upper()
    zip_code = (intent.zip_code or "").strip()

    payload: dict = {
        "view": "summary",
        "size": MLS_ADDRESS_PAGE_SIZE,
        "number": 0,
        "statuses": LIST_TYPE_TO_MLS_STATUSES[intent.list_type],
    }
    if address_line:
        payload["text"] = address_line
        payload["street_address"] = address_line
    parts = [p for p in [address_line, city, state, zip_code] if p]
    if parts:
        payload["address"] = ", ".join(parts)
    if city:
        payload["city"] = city
    if state:
        payload["state"] = state
    if zip_code:
        payload["zip"] = zip_code

    try:
        response = _session.post(MLS_LISTINGS_URL, json=payload, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
    except Exception as exc:
        raise MlsSearchError(f"MLS search failed: {exc}") from exc

    body = response.json()
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        data = body if isinstance(body, dict) else {}

    content = data.get("content") or {}
    return {
        "total_elements": data.get("total_elements") or 0,
        "listings": content.get("listings") or [],
    }


def _resolve_one(inquiry: LocationInquiry, state_hint: str | None) -> ResolvedLocation:
    response = _session.get(
        TYPEAHEAD_URL,
        params={
            "size": TYPEAHEAD_SIZE,
            "input": inquiry.name,
            "mode": "extended",
            "entities": TYPEAHEAD_ENTITIES,
        },
        timeout=HTTP_TIMEOUT,
    )
    response.raise_for_status()
    data = (response.json().get("data") or {}) if response.content else {}

    if inquiry.location_type:
        order = [inquiry.location_type]
    elif inquiry.name.isdigit() and len(inquiry.name) == 5:
        order = ["zipcode", "city", "neighborhood"]
    else:
        order = ["neighborhood", "city", "zipcode"]

    for location_type in order:
        items = data.get(_TYPEAHEAD_BUCKET[location_type]) or []
        best = _best_match(items, inquiry, state_hint)
        if best:
            return _to_location(location_type, best)

    raise LocationResolveError(f"Could not resolve location: {inquiry.name}")


def _are_compatible(locations: list[ResolvedLocation]) -> tuple[bool, str]:
    states = {loc.state for loc in locations}
    if len(states) > 1:
        return False, "different states"

    if any(loc.type == "zipcode" for loc in locations):
        return False, "zip codes cannot be combined with other areas"

    city_names = {loc.name for loc in locations if loc.type == "city"}
    parent_cities = {loc.parent_city for loc in locations if loc.parent_city}

    if len(locations) > 1 and all(loc.type == "neighborhood" for loc in locations):
        if len(parent_cities) == 1:
            return True, ""
        if len(parent_cities) > 1:
            return False, "neighborhoods in different cities"

    coords = [loc for loc in locations if loc.latitude is not None and loc.longitude is not None]
    if len(coords) >= 2:
        if not _within_distance(coords):
            return False, f"areas more than {MAX_MULTI_LOCATION_DISTANCE_MILES} miles apart"

    return True, ""


def _within_distance(locations: list[ResolvedLocation]) -> bool:
    for i, a in enumerate(locations):
        for b in locations[i + 1 :]:
            miles = _haversine_miles(a.longitude, a.latitude, b.longitude, b.latitude)
            if miles > MAX_MULTI_LOCATION_DISTANCE_MILES:
                return False
    return True


def _haversine_miles(lng1: float, lat1: float, lng2: float, lat2: float) -> float:
    radius = 3958.8
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


def _pick_primary_location(locations: list[ResolvedLocation]) -> ResolvedLocation:
    for loc in locations:
        if loc.type == "city":
            return loc
    for loc in locations:
        if loc.parent_city:
            return loc
    return locations[0]


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _best_match(
    items: list[dict],
    inquiry: LocationInquiry,
    state_hint: str | None,
) -> dict | None:
    if not items:
        return None
    ranked = sorted(
        items,
        key=lambda item: _score_item(item, inquiry, state_hint),
        reverse=True,
    )
    return ranked[0] if _score_item(ranked[0], inquiry, state_hint) > 0 else None


def _score_item(item: dict, inquiry: LocationInquiry, state_hint: str | None) -> int:
    name = item.get("name") or item.get("city") or ""
    score = 0
    if _normalize(name) == _normalize(inquiry.name):
        score += 100
    elif _normalize(inquiry.name) in _normalize(name):
        score += 50
    elif _normalize(name) in _normalize(inquiry.name):
        score += 40

    state = (state_hint or "").upper()
    if state and (item.get("state") or "").upper() == state:
        score += 30

    parent = inquiry.parent_city
    if parent and _normalize(item.get("city") or "") == _normalize(parent):
        score += 40

    score += min(item.get("listing_count") or 0, 20)
    return score


def _to_location(location_type: str, item: dict) -> ResolvedLocation:
    name = item.get("name") or item.get("city") or ""
    coords = item.get("location") or []
    longitude = coords[0] if len(coords) >= 2 else None
    latitude = coords[1] if len(coords) >= 2 else None
    return ResolvedLocation(
        type=location_type,
        name=name if location_type != "zipcode" else (item.get("zip") or name),
        state=(item.get("state") or "").upper(),
        id=item["id"],
        parent_city=item.get("city") if location_type == "neighborhood" else None,
        longitude=longitude,
        latitude=latitude,
    )
