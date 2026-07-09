"""Constants for AI search URL building (matches roa-website route contract)."""

TYPEAHEAD_URL = "https://staging-v2.realtyofamerica.com/api/typeahead/v2/autocomplete/"

# Staging website — Next.js listing/search pages (Vercel).
WEB_HOST = "https://roa-website-staging.vercel.app"

LOCATION_TYPE_NUM = {
    "city": 1,
    "neighborhood": 2,
    "zipcode": 3,
}

PATH_PREFIX = {
    "city": "city",
    "neighborhood": "neighborhood",
    "zipcode": "zipcode",
}

TYPEAHEAD_ENTITIES = "zip,address,city,neighborhood"
TYPEAHEAD_SIZE = 10

LIST_TYPE_ROUTE_SUFFIX = {
    "For rent": "rent",
    "Sold": "sold",
}

# Gemini 3.x — best structured JSON for extraction tasks.
GEMINI_MODEL = "gemini-3.5-flash"
GEMINI_MODEL_FALLBACKS = ["gemini-2.5-flash"]
