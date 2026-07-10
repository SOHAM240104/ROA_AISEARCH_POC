"""Build roa-website redirect URLs for area search and property detail pages."""

import math
import re
from urllib.parse import quote, urlencode

from ai_search.config import LIST_TYPE_ROUTE_SUFFIX, LOCATION_TYPE_NUM, PATH_PREFIX, WEB_HOST
from ai_search.schemas import ParsedSearchIntent, ResolvedLocation

_NUMERIC_QUERY_FIELDS = (
    "min_bedrooms",
    "max_bedrooms",
    "min_bathrooms",
    "max_bathrooms",
    "min_price",
    "max_price",
    "min_sq_ft",
    "max_sq_ft",
    "min_lot_size",
    "max_lot_size",
    "min_year_built",
    "max_year_built",
)
_INVALID_NUMERIC = frozenset({"", "nan", "null", "none"})


def slugify(value: str) -> str:
    """Match roa-website path segments: Chicago Ridge -> Chicago-Ridge."""
    value = re.sub(r"[^\w\s-]", "", value.strip())
    parts = [part for part in re.split(r"[-\s]+", value) if part]
    return "-".join(part.capitalize() for part in parts)


def build_search_url(
    intent: ParsedSearchIntent,
    locations: ResolvedLocation | list[ResolvedLocation],
) -> tuple[str, dict]:
    if isinstance(locations, ResolvedLocation):
        locations = [locations]
    if len(locations) > 1:
        return _build_multi_url(intent, locations)
    return _build_single_url(intent, locations[0])


def _location_token(location: ResolvedLocation) -> str:
    type_num = LOCATION_TYPE_NUM[location.type]
    return f"{type_num}:{location.name}:{location.state}:{location.id}"


def _primary_path_slug(locations: list[ResolvedLocation]) -> str:
    for location in locations:
        if location.type == "city":
            return slugify(location.name)
    for location in locations:
        if location.parent_city:
            return slugify(location.parent_city)
    return slugify(locations[0].name)


def _build_multi_url(intent: ParsedSearchIntent, locations: list[ResolvedLocation]) -> tuple[str, dict]:
    """Multi-area URL: /city/{state}/{slug}/{token1+token2}?filters"""
    state = locations[0].state
    slug = _primary_path_slug(locations)
    tokens = "+".join(_location_token(loc) for loc in locations)
    token_segment = quote(tokens, safe=":+")
    path = f"/city/{state}/{slug}/{token_segment}"
    return _finalize_path(intent, path)


def _build_single_url(intent: ParsedSearchIntent, location: ResolvedLocation) -> tuple[str, dict]:
    token = quote(_location_token(location), safe=":")

    if location.type == "zipcode":
        segment = location.name
    elif location.type == "neighborhood":
        segment = slugify(location.parent_city or location.name)
    else:
        segment = slugify(location.name)

    path = f"/{PATH_PREFIX[location.type]}/{location.state}/{segment}/{token}"
    return _finalize_path(intent, path)


def _finalize_path(intent: ParsedSearchIntent, path: str) -> tuple[str, dict]:
    suffix = LIST_TYPE_ROUTE_SUFFIX.get(intent.list_type)
    if suffix:
        path = f"{path}/{suffix}"

    query_params: dict[str, str | int | float] = {}
    if intent.list_type:
        query_params["list_type"] = intent.list_type

    for field in _NUMERIC_QUERY_FIELDS:
        value = getattr(intent, field)
        if value is None:
            continue
        if isinstance(value, str) and value.strip().lower() in _INVALID_NUMERIC:
            continue
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            continue
        query_params[field] = int(value) if isinstance(value, float) and value.is_integer() else value

    if intent.property_types:
        query_params["property_types"] = ",".join(intent.property_types)
    if intent.text:
        query_params["text"] = intent.text

    query_string = urlencode(query_params, doseq=True) if query_params else ""
    full_path = f"{path}?{query_string}" if query_string else path
    return f"{WEB_HOST.rstrip('/')}{full_path}", query_params


def build_detail_url(listing: dict) -> str:
    state = (listing.get("state") or "").strip().upper()
    city = (listing.get("city") or "").strip()
    address = (listing.get("address") or "").strip()
    if not address and listing.get("formatted_address"):
        address = listing["formatted_address"].split(",")[0].strip()
    listing_id = listing.get("id")
    if not all([state, city, address, listing_id]):
        raise ValueError("Listing is missing fields required for a detail URL.")
    return f"{WEB_HOST.rstrip('/')}/detail/{state}/{slugify(city)}/{slugify(address)}/{listing_id}"
