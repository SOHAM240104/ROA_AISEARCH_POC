"""Canonical home feature labels from roa-website search filters."""

HOME_FEATURES = [
    "Air Conditioning",
    "Basement",
    "Water front",
    "Washer / dryer",
    "Has a view",
    "Pets allowed",
    "Fireplace",
    "Primary bedroom on main floor",
    "Fixer-upper",
    "RV parking",
    "Guest house",
    "Green home",
    "Elevator",
    "Accessible home",
]


def build_text_query_param(home_features: list[str], free_text: str | None = None) -> str | None:
    """Merge home_features + free_text into the frontend `text` query param."""
    parts = list(home_features)
    if free_text:
        cleaned = free_text.strip()
        if cleaned and cleaned not in parts:
            parts.append(cleaned)
    return ",".join(parts) if parts else None
