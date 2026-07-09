import math
import re
from urllib.parse import quote, urlencode

from ai_search.config import LIST_TYPE_ROUTE_SUFFIX, LOCATION_TYPE_NUM, PATH_PREFIX, WEB_HOST
from ai_search.schemas import ParsedSearchIntent, ResolvedLocation

NUMERIC_QUERY_FIELDS = (
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

_INVALID_NUMERIC_STRINGS = frozenset({"", "nan", "null", "none"})


def _is_valid_query_value(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip().lower() not in _INVALID_NUMERIC_STRINGS
    if isinstance(value, float):
        return not (math.isnan(value) or math.isinf(value))
    return True


def _coerce_query_value(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def slugify(value: str) -> str:
    """Match roa-website path segments, e.g. Chicago -> Chicago, Chicago Ridge -> Chicago-Ridge."""
    value = re.sub(r"[^\w\s-]", "", value.strip())
    parts = [part for part in re.split(r"[-\s]+", value) if part]
    return "-".join(part.capitalize() for part in parts)


def _location_token(location: ResolvedLocation) -> str:
    type_num = LOCATION_TYPE_NUM[location.type]
    return f"{type_num}:{location.name}:{location.state}:{location.id}"


def _path_segment(location: ResolvedLocation) -> str:
    if location.type == "zipcode":
        return location.name
    if location.type == "neighborhood":
        return slugify(location.parent_city or location.name)
    return slugify(location.name)


def build_search_url(intent: ParsedSearchIntent, location: ResolvedLocation) -> tuple[str, dict]:
    prefix = PATH_PREFIX[location.type]
    token = quote(_location_token(location), safe=":")
    path = f"/{prefix}/{location.state}/{_path_segment(location)}/{token}"

    list_type = intent.list_type
    route_suffix = LIST_TYPE_ROUTE_SUFFIX.get(list_type)
    if route_suffix:
        path = f"{path}/{route_suffix}"

    query_params: dict[str, str | int | float] = {}

    if list_type:
        query_params["list_type"] = list_type

    for field in NUMERIC_QUERY_FIELDS:
        value = getattr(intent, field)
        if not _is_valid_query_value(value):
            continue
        query_params[field] = _coerce_query_value(value)

    if intent.property_types:
        query_params["property_types"] = ",".join(intent.property_types)

    if intent.text:
        query_params["text"] = intent.text

    query_string = urlencode(query_params, doseq=True) if query_params else ""
    path_with_query = f"{path}?{query_string}" if query_string else path
    full_url = f"{WEB_HOST.rstrip('/')}{path_with_query}"
    return full_url, query_params
