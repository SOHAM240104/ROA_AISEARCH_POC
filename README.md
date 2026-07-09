# ROA AI Search POC

Natural-language property search → structured filters (Gemini) → ROA website search URL.

## Streamlit Cloud

- **Main file path:** `ai_search/app.py`
- **Secrets** (App settings → Secrets):

```toml
GEMINI_API_KEY = "your-key-here"
```

## Local

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your-key-here
# or put GEMINI_API_KEY in a .env at the repo root
streamlit run ai_search/app.py
```
