"""AI search configuration — env, API endpoints, route constants."""

import os
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

# --- External APIs (staging) ---
STAGING_API_HOST = "https://staging-v2.realtyofamerica.com"
TYPEAHEAD_URL = f"{STAGING_API_HOST}/api/typeahead/v2/autocomplete/"
MLS_LISTINGS_URL = f"{STAGING_API_HOST}/api/mls-search/v1/listings/"
HTTP_TIMEOUT = 5

# --- Website redirect target ---
WEB_HOST = "https://roa-website-staging.vercel.app"

# --- Area search URL contract (roa-website) ---
LOCATION_TYPE_NUM = {"city": 1, "neighborhood": 2, "zipcode": 3}
PATH_PREFIX = {"city": "city", "neighborhood": "neighborhood", "zipcode": "zipcode"}
LIST_TYPE_ROUTE_SUFFIX = {"For rent": "rent", "Sold": "sold"}

TYPEAHEAD_ENTITIES = "zip,address,city,neighborhood"
TYPEAHEAD_SIZE = 10

# --- Gemini ---
GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_MODEL_FALLBACKS = ["gemini-2.5-flash"]

# --- MLS status groups (RealStaq cannot mix sold + active in one request) ---
LIST_TYPE_TO_MLS_STATUSES = {
    "For sale": ["active", "backup", "pending", "coming_soon"],
    "For rent": ["active", "backup", "pending", "coming_soon"],
    "Sold": ["sold"],
}
MLS_ADDRESS_PAGE_SIZE = 1

# Multi-location: max distance (miles) between resolved areas — must be nearby/adjacent.
MAX_MULTI_LOCATION_DISTANCE_MILES = 12
