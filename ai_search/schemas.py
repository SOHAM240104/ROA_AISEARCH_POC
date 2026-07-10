import math
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from ai_search.features import build_text_query_param

_INVALID_NUMERIC_STRINGS = frozenset({"", "nan", "null", "none"})

_INT_FIELDS = (
    "min_bedrooms",
    "max_bedrooms",
    "min_price",
    "max_price",
    "min_sq_ft",
    "max_sq_ft",
    "min_year_built",
    "max_year_built",
)

_FLOAT_FIELDS = (
    "min_bathrooms",
    "max_bathrooms",
    "min_lot_size",
    "max_lot_size",
)


def _sanitize_number(value, *, as_int: bool):
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in _INVALID_NUMERIC_STRINGS:
            return None
        try:
            value = float(cleaned)
        except ValueError:
            return None
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if as_int:
        if isinstance(value, float) and not value.is_integer():
            return None
        return int(value)
    return float(value)


def _is_half_bath(value: float) -> bool:
    return abs(value % 1 - 0.5) < 1e-9


class LocationInquiry(BaseModel):
    """One named place from the user query — resolved to an ID via typeahead, never by AI."""

    name: str = Field(description="City, neighborhood, or zip name.")
    location_type: Literal["city", "neighborhood", "zipcode"] | None = Field(
        default=None,
        description="Set when clearly a neighborhood vs city vs zip.",
    )
    parent_city: str | None = Field(
        default=None,
        description="Parent city for disambiguation, e.g. Chicago for Lincoln Park.",
    )

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class ParsedSearchIntent(BaseModel):
    """Structured Gemini output — filters only, never location ids or URLs."""

    interpretation: str = Field(
        description="Plain-English summary of what the user wants and what was inferred from casual language.",
    )
    search_mode: Literal["area", "address"] = Field(
        default="area",
        description="area = city/zip/neighborhood search; address = specific street address or property.",
    )
    address_line: str | None = Field(
        default=None,
        description="Street address when search_mode is address, e.g. 355 Pointing Rock Dr.",
    )
    locations: list[LocationInquiry] = Field(
        default_factory=list,
        description="One or more nearby cities/neighborhoods when user names multiple areas.",
    )
    location_text: str = Field(
        default="",
        description="Primary city or single location name. For multi-neighborhood, the parent city.",
    )
    location_type: Literal["city", "neighborhood", "zipcode"] | None = Field(
        default=None,
        description="Location type when clearly inferable from the query (single-location).",
    )
    state: str | None = Field(
        default=None,
        description="Two-letter US state code when mentioned or strongly implied.",
    )
    zip_code: str | None = Field(
        default=None,
        description="Five-digit zip when mentioned (especially useful for address mode).",
    )
    min_bedrooms: int | None = None
    max_bedrooms: int | None = None
    min_bathrooms: float | None = None
    max_bathrooms: float | None = None
    min_price: int | None = None
    max_price: int | None = None
    min_sq_ft: int | None = None
    max_sq_ft: int | None = None
    min_lot_size: float | None = None
    max_lot_size: float | None = None
    min_year_built: int | None = None
    max_year_built: int | None = None
    property_types: list[str] = Field(default_factory=list)
    list_type: Literal["For sale", "For rent", "Sold"]
    home_features: list[str] = Field(default_factory=list)
    text: str | None = Field(
        default=None,
        description="Optional free-text keywords not covered by home_features.",
    )

    @field_validator("state")
    @classmethod
    def normalize_state(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        return value if len(value) == 2 else None

    @field_validator("zip_code")
    @classmethod
    def normalize_zip(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = "".join(ch for ch in value.strip() if ch.isdigit())
        return cleaned if len(cleaned) == 5 else None

    @field_validator("address_line")
    @classmethod
    def normalize_address_line(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.strip().split())
        return cleaned or None

    @field_validator(*_INT_FIELDS, mode="before")
    @classmethod
    def sanitize_int_fields(cls, value):
        return _sanitize_number(value, as_int=True)

    @field_validator(*_FLOAT_FIELDS, mode="before")
    @classmethod
    def sanitize_float_fields(cls, value):
        return _sanitize_number(value, as_int=False)

    @model_validator(mode="after")
    def normalize_filter_ranges(self) -> "ParsedSearchIntent":
        # "built after 1990" must not become only homes from exactly 1990.
        if (
            self.min_year_built is not None
            and self.max_year_built is not None
            and self.min_year_built == self.max_year_built
        ):
            self.max_year_built = None

        if (
            self.min_year_built is not None
            and self.max_year_built is not None
            and self.min_year_built > self.max_year_built
        ):
            self.max_year_built = None

        if (
            self.min_bedrooms is not None
            and self.max_bedrooms is not None
            and self.min_bedrooms > self.max_bedrooms
        ):
            self.max_bedrooms = None

        # 2.5 baths -> min=2, max=3 (never min=2.5 in the URL).
        if self.min_bathrooms is not None and _is_half_bath(self.min_bathrooms):
            base = int(self.min_bathrooms)
            self.min_bathrooms = float(base)
            self.max_bathrooms = float(base + 1)

        if self.min_bathrooms is not None and self.max_bathrooms is not None:
            if self.min_bathrooms > self.max_bathrooms:
                self.max_bathrooms = None
            # Gemini misparse e.g. min=2 max=2.5 — drop invalid fractional max only.
            elif _is_half_bath(self.max_bathrooms):
                self.max_bathrooms = None

        return self

    @model_validator(mode="after")
    def merge_features_into_text(self) -> "ParsedSearchIntent":
        self.text = build_text_query_param(self.home_features, self.text)
        return self

    @model_validator(mode="after")
    def normalize_locations(self) -> "ParsedSearchIntent":
        if not self.locations and self.location_text.strip():
            self.locations = [
                LocationInquiry(
                    name=self.location_text.strip(),
                    location_type=self.location_type,
                )
            ]
        elif self.locations and not self.location_text.strip():
            parent_cities = {loc.parent_city for loc in self.locations if loc.parent_city}
            if len(parent_cities) == 1:
                self.location_text = parent_cities.pop()
            else:
                self.location_text = self.locations[0].name
        return self


class ResolvedLocation(BaseModel):
    type: Literal["city", "neighborhood", "zipcode"]
    name: str
    state: str
    id: str
    parent_city: str | None = None
    longitude: float | None = None
    latitude: float | None = None
