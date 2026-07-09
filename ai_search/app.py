"""Streamlit POC — smart conversational property search → redirect URL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from ai_search.gemini_parser import GeminiParseError
from ai_search.location_resolver import LocationResolveError
from ai_search.service import run_ai_search

EXAMPLE_QUERIES = [
    ("Exact beds + price cap", "3 bedroom condo in Chicago IL under $300000 with 2.5 bathrooms built after 1990"),
    ("At least beds + price range", "condo or townhouse in Chicago with at least 2 beds between 150 and 250k"),
    ("At most beds", "maximum 2 bedroom apartment for rent in Chicago under 2000 a month"),
    ("Bed range", "2 to 4 bed single family home in Dallas between 400k and 600k"),
    ("Exact baths", "exactly 3 bed 2 bath for sale in Plano TX under 500k"),
    ("At least baths + sqft", "at least 2 baths and 2000 sqft house in Austin TX"),
    ("Minimum price", "townhouse in Phoenix over 350k with minimum 3 bedrooms"),
    ("Year built range", "built after 2000 before 2020 condo in Seattle"),
    ("2.5 baths (range)", "3 bed 2.5 bath condo in Chicago under 300k built after 1990"),
    ("Casual / messy", "me and my wife 2 kids need house plano texas under 400k"),
]

st.set_page_config(page_title="ROA Smart Search POC", page_icon="🏠", layout="centered")

st.title("ROA Smart Search")
st.caption("Talk naturally — we'll figure out the filters and open the right search page.")

query = st.text_input(
    "What kind of home are you looking for?",
    placeholder="I have 2 kids and a dog, need something in Dallas with space for a home office",
)

if st.button("Search", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Tell us what you're looking for.")
    else:
        with st.spinner("Understanding your search..."):
            try:
                result = run_ai_search(query.strip())
            except GeminiParseError as exc:
                st.error(str(exc))
            except LocationResolveError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
            else:
                st.success("Search URL ready")
                st.info(f"**Understood:** {result.get('interpretation', '')}")
                st.link_button("Open search results", result["url"], use_container_width=True)
                st.code(result["url"], language=None)

                with st.expander("Parsed filters"):
                    st.json(result["parsed_intent"])

                with st.expander("Resolved location"):
                    st.json(result["resolved_location"])

                with st.expander("Query params"):
                    st.json(result["query_params"])

st.divider()

st.subheader("Example queries you can copy")
st.caption("Each box shows a query type and the exact text to paste into the search field above.")

for index, (label, example) in enumerate(EXAMPLE_QUERIES, start=1):
    st.markdown(f"**{index}. {label}**")
    st.code(example, language=None)

st.divider()
st.markdown(
    """
**How it works**
- Understands casual conversation, not just keywords
- Infers beds, features, and property type from lifestyle clues
- Opens the matching search on [roa-website-staging.vercel.app](https://roa-website-staging.vercel.app/)
"""
)
