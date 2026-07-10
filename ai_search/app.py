"""Streamlit POC — natural language property search → redirect URL."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from ai_search import (
    AddressNotFoundError,
    GeminiParseError,
    LocationResolveError,
    MlsSearchError,
    run_ai_search,
)

EXAMPLES = [
    ("Vague first search", "looking for a place in chicago not too expensive"),
    ("Family move", "we're moving to plano with 2 kids need a house under 450k"),
    ("Couple + dog", "something in dallas for me and my partner and our dog maybe 2 bed"),
    ("Two neighborhoods", "condo in lincoln park or lakeview chicago around 500k"),
    ("Specific street", "is 355 pointing rock dr borrego springs still for sale"),
    ("Browsing sold", "what did homes sell for on fairway lane borrego springs"),
    ("Renting", "2 bed apartment to rent in chicago max 2200/month"),
    ("Downsizing", "smaller place in phoenix 2 bed max no stairs bad knees"),
    ("Two nearby towns", "houses in waldorf or st charles md under 400k"),
    ("Fixer / investor", "fixer upper in austin under 300k with some land"),
]

st.set_page_config(page_title="ROA Smart Search", page_icon="🏠", layout="centered")
st.title("ROA Smart Search")
st.caption("Area queries open search results. Street addresses open the property page.")

query = st.text_input(
    "What are you looking for?",
    placeholder="Lincoln Park or Lakeview Chicago — or — 355 Pointing Rock Dr Borrego Springs",
)

if st.button("Search", type="primary", use_container_width=True):
    if not query.strip():
        st.warning("Enter a search query.")
    else:
        with st.spinner("Searching..."):
            try:
                result = run_ai_search(query.strip())
            except (GeminiParseError, AddressNotFoundError, LocationResolveError, MlsSearchError) as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
            else:
                is_detail = result["route_type"] == "detail"
                st.success("Property page ready" if is_detail else "Search URL ready")
                st.info(f"**Understood:** {result['interpretation']}")
                st.caption(f"**{result['route_type']}** → {' → '.join(result['routing_steps'])}")

                if result.get("location_warning"):
                    st.warning(result["location_warning"])

                label = "property page" if is_detail else "search results"
                st.link_button(f"Open {label}", result["url"], use_container_width=True)
                st.code(result["url"])

                preview = result.get("listing_preview")
                if preview:
                    col_img, col_info = st.columns([1, 2])
                    if preview.get("image"):
                        col_img.image(preview["image"], use_container_width=True)
                    col_info.markdown(f"**{preview.get('address', '')}**")
                    if preview.get("price"):
                        col_info.markdown(f"**{preview['price']}**")

                with st.expander("Parsed intent"):
                    st.json(result["parsed_intent"])
                if result.get("resolved_locations"):
                    with st.expander("Resolved locations"):
                        st.json(result["resolved_locations"])
                if result.get("query_params"):
                    with st.expander("Query params"):
                        st.json(result["query_params"])

st.divider()
st.subheader("Examples")
for label, text in EXAMPLES:
    st.markdown(f"**{label}**")
    st.code(text)
