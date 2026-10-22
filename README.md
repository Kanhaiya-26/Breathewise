# BreatheWise 🌿

Air quality, explained kindly. A Streamlit MVP that shows live AQI (WAQI), nearby pollutant
concentrations (OpenAQ v3), comparable hotspot rankings, a searchable health guide built from
`AQI_Health_Database_100_Expanded.xlsx`, and Python-calculated summaries with optional AI wording.

**Not medical advice.** The health guide is an educational draft that requires clinical review.
BreatheWise does not diagnose or recommend treatment.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional - add your keys
python -m streamlit run app.py
```

The app runs **without any keys** in demo mode. Demo values are synthetic and labelled
**DEMO DATA - NOT LIVE**.

## Keys (all optional)

| Variable | Used for |
|---|---|
| `WAQI_API_TOKEN` | Live AQI + hotspot ranking (https://aqicn.org/data-platform/token/) |
| `OPENAQ_API_KEY` | Nearby raw concentrations, sent as `X-API-Key` (https://explore.openaq.org/register) |
| `GEMINI_API_KEY` | Optional plain-language wording (tried first) |
| `OPENROUTER_API_KEY` | Optional wording, only if Gemini is absent or fails |

Locally keys come from `.env` (python-dotenv). On Streamlit Community Cloud put them in
**App settings → Secrets** as TOML, e.g. `WAQI_API_TOKEN = "..."`. Never commit `.env`.

## Data honesty rules

- WAQI values are US-EPA AQI (and AQI sub-indices per pollutant). OpenAQ values are raw
  concentrations (µg/m³, ppm…) and are never converted to or mixed with AQI.
- Hotspots rank only numeric AQI values from the same source.
- Every reading shows source, station time, fetch time and stale-data warnings.
- All numbers are computed in Python; the LLM only rephrases those facts and is told not to
  add numbers, forecasts, diagnoses or treatments.
- If a provider fails, the app shows the error, not a guess.

## Files

- `app.py` – Streamlit UI (Overview, Hotspots, Health Guide, Insights)
- `data_provider.py` – WAQI, OpenAQ v3, demo data, secrets
- `health_guide.py` – read-only workbook loading and search
- `intelligence.py` – hotspot ranking, Python summaries, Gemini → OpenRouter fallback
