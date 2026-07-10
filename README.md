# ROA AI Search POC

Natural-language property search for Realty of America. Users type a casual query; Gemini turns it into structured filters; the app resolves locations via RealStaq typeahead and redirects to the ROA website (search results or a property detail page).

## How it works

1. **Parse** — Gemini extracts intent (beds, price, list type, locations, address, etc.).
2. **Route**
   - **Area** — city / neighborhood / zip → search URL (supports multi-neighborhood when areas are nearby).
   - **Address** — street address → MLS lookup → property detail URL (falls back to sold if nothing active).
3. **Redirect** — opens staging ROA website with the built URL.

## Project layout

```
ai_search/
  app.py          # Streamlit UI
  service.py      # Orchestration (parse → route → URL)
  parser.py       # Gemini intent parsing
  schemas.py      # Pydantic models
  realstaq.py     # Typeahead + MLS APIs
  urls.py         # Search / detail URL builders
  config.py       # Endpoints, model, constants
  prompts.py      # Gemini system prompt
  features.py     # Feature → text query mapping
```

## Setup

### Prerequisites

- Python 3.10+
- A Gemini API key

### Local

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your-key-here
# or put GEMINI_API_KEY in a .env at the repo root
streamlit run ai_search/app.py
```

### Streamlit Cloud

- **Main file path:** `ai_search/app.py`
- **Secrets** (App settings → Secrets):

```toml
GEMINI_API_KEY = "your-key-here"
```

## Example queries

| Style | Example |
| --- | --- |
| Vague | looking for a place in chicago not too expensive |
| Family | we're moving to plano with 2 kids need a house under 450k |
| Multi-neighborhood | condo in lincoln park or lakeview chicago around 500k |
| Street address | is 355 pointing rock dr borrego springs still for sale |
| Sold comps | what did homes sell for on fairway lane borrego springs |
| Rent | 2 bed apartment to rent in chicago max 2200/month |

## Dependencies

- `streamlit` — UI
- `google-genai` — Gemini parsing
- `pydantic` — structured intent schema
- `requests` — RealStaq typeahead / MLS calls

## Notes

- Targets **staging** APIs and the staging ROA website (`config.py`).
- Location IDs come from typeahead only — never invented by the model.
- Multi-location searches require areas within ~12 miles of each other.
