"""AI search orchestration — parse, route, resolve, return redirect URL."""

import re

from ai_search.parser import parse_intent
from ai_search.realstaq import resolve_locations, search_by_address
from ai_search.schemas import ParsedSearchIntent
from ai_search.urls import build_detail_url, build_search_url

_STREET_TYPES = (
    r"st\.?|street|dr\.?|drive|rd\.?|road|ave\.?|avenue|ln\.?|lane|"
    r"blvd\.?|boulevard|ct\.?|court|way|pl\.?|place|cir\.?|circle|"
    r"pkwy\.?|parkway|trl\.?|trail|hwy\.?|highway"
)
_STREET_PATTERN = re.compile(
    rf"\b(\d+\s+(?:[\w.'-]+\s+)*(?:{_STREET_TYPES}))(?:\s*(?:#|unit|apt|ste)\.?\s*[\w-]+)?\b",
    re.IGNORECASE,
)


class AddressNotFoundError(Exception):
    pass


def run_ai_search(query: str, api_key: str | None = None) -> dict:
    intent = _apply_routing(parse_intent(query, api_key=api_key), query)
    if intent.search_mode == "address":
        return _address_route(intent)
    return _area_route(intent)


def _apply_routing(intent: ParsedSearchIntent, raw_query: str) -> ParsedSearchIntent:
    match = _STREET_PATTERN.search(raw_query)
    if not match:
        return intent
    street = " ".join(match.group(1).split())
    if intent.search_mode == "address":
        if not intent.address_line:
            return intent.model_copy(update={"address_line": street})
        return intent
    return intent.model_copy(update={"search_mode": "address", "address_line": street})


def _address_route(intent: ParsedSearchIntent) -> dict:
    if not intent.address_line:
        raise AddressNotFoundError("No street address found in the query.")

    mls = search_by_address(intent)
    if not mls["listings"]:
        mls = search_by_address(intent.model_copy(update={"list_type": "Sold"}))
    if not mls["listings"]:
        parts = ", ".join(p for p in [intent.address_line, intent.location_text, intent.state] if p)
        raise AddressNotFoundError(f"No property found for: {parts}")

    listing = mls["listings"][0]
    return {
        "url": build_detail_url(listing),
        "route_type": "detail",
        "routing_steps": ["parse", "mls_search", "url_build"],
        "result_count": mls["total_elements"],
        "interpretation": intent.interpretation,
        "parsed_intent": intent.model_dump(),
        "resolved_location": None,
        "resolved_locations": None,
        "location_warning": None,
        "query_params": {},
        "listing_preview": _preview(listing),
    }


def _area_route(intent: ParsedSearchIntent) -> dict:
    locations, warning = resolve_locations(intent)
    url, query_params = build_search_url(intent, locations)
    is_multi = len(locations) > 1

    return {
        "url": url,
        "route_type": "search_multi" if is_multi else "search",
        "routing_steps": ["parse", "typeahead", "url_build"],
        "result_count": None,
        "interpretation": intent.interpretation,
        "parsed_intent": intent.model_dump(),
        "resolved_location": locations[0].model_dump(),
        "resolved_locations": [loc.model_dump() for loc in locations],
        "location_warning": warning,
        "query_params": query_params,
        "listing_preview": None,
    }


def _preview(listing: dict) -> dict:
    hero = listing.get("hero") or {}
    photos = listing.get("photos") or []
    image = hero.get("medium") or (photos[0].get("medium") if photos else None)
    price = listing.get("price_display")
    if listing.get("status") == "sold" and listing.get("sold_price"):
        price = f"${listing['sold_price']:,}"
    return {
        "id": listing.get("id"),
        "address": listing.get("formatted_address") or listing.get("address"),
        "price": price,
        "beds": listing.get("bedrooms"),
        "baths": listing.get("bathrooms"),
        "sqft": listing.get("square_feet"),
        "status": listing.get("status"),
        "image": image,
    }
