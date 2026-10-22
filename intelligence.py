"""Deterministic Python summaries + optional LLM wording (Gemini first, OpenRouter fallback).

All numbers are computed here in Python. LLMs only receive these computed facts and are asked
to rephrase them in plain language - never to produce readings, forecasts or diagnoses.
"""
from __future__ import annotations

import requests

from data_provider import POLLUTANT_NAMES, Reading, aqi_category, get_secret

TIMEOUT = 20


def rank_hotspots(readings: list[Reading]) -> list[Reading]:
    """Rank only readings on the same scale (numeric US-EPA AQI from the same source type)."""
    comparable = [r for r in readings if r.aqi is not None]
    return sorted(comparable, key=lambda r: r.aqi, reverse=True)


def facts(readings: list[Reading]) -> dict:
    ranked = rank_hotspots(readings)
    if not ranked:
        return {"count": 0}
    vals = [r.aqi for r in ranked]
    dom = {}
    for r in ranked:
        if r.dominant:
            dom[r.dominant] = dom.get(r.dominant, 0) + 1
    top_dom = max(dom, key=dom.get) if dom else None
    return {
        "count": len(ranked),
        "is_live": all(r.is_live for r in ranked),
        "source": ", ".join(sorted({r.source for r in ranked})),
        "max_station": ranked[0].station, "max_aqi": ranked[0].aqi,
        "min_station": ranked[-1].station, "min_aqi": ranked[-1].aqi,
        "mean_aqi": round(sum(vals) / len(vals), 1),
        "above_100": sum(v > 100 for v in vals),
        "above_150": sum(v > 150 for v in vals),
        "dominant": POLLUTANT_NAMES.get(top_dom, top_dom) if top_dom else None,
        "max_category": aqi_category(ranked[0].aqi)[0],
    }


def python_summary(f: dict) -> str:
    if not f.get("count"):
        return "No comparable AQI readings are available, so no summary can be calculated."
    label = "live" if f["is_live"] else "DEMO (synthetic, not live)"
    s = (
        f"Across {f['count']} {label} stations ({f['source']}), the average AQI is {f['mean_aqi']}. "
        f"The highest reading is {f['max_aqi']:.0f} at {f['max_station']} ({f['max_category']}); "
        f"the lowest is {f['min_aqi']:.0f} at {f['min_station']}. "
        f"{f['above_100']} station(s) exceed AQI 100 and {f['above_150']} exceed AQI 150."
    )
    if f.get("dominant"):
        s += f" The most frequent dominant pollutant is {f['dominant']}."
    if f["above_100"]:
        s += (" At AQI above 100, sensitive groups (children, older adults, people with heart or lung"
              " conditions, pregnancy) are generally advised to reduce prolonged outdoor exertion.")
    return s


PROMPT = """You are writing a short, calm, plain-language air-quality note for the public.
Use ONLY the facts below. Do not add, estimate or change any number. Do not forecast.
Do not diagnose, and do not recommend medicines or treatments. Mention that people with
symptoms should consult a clinician and seek emergency care for severe symptoms.
If data is marked DEMO, say clearly it is demonstration data and not live.
Write at most 120 words.

FACTS:
{summary}
"""


def _gemini(prompt: str, key: str) -> str:
    model = get_secret("GEMINI_MODEL") or "gemini-3.8-flash"
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def _openrouter(prompt: str, key: str) -> str:
    model = get_secret("OPENROUTER_MODEL") or "openrouter/auto"
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "X-Title": "BreatheWise"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


def _err(e: Exception) -> str:
    resp = getattr(e, "response", None)
    return f"HTTP {resp.status_code}" if resp is not None else type(e).__name__


def llm_explain(summary: str) -> tuple[str | None, str]:
    """Returns (text, provider_or_error). Gemini first; OpenRouter only if Gemini fails/absent."""
    prompt = PROMPT.format(summary=summary)
    errors = []
    gk = get_secret("GEMINI_API_KEY")
    if gk:
        try:
            return _gemini(prompt, gk), "Gemini"
        except Exception as e:
            errors.append(f"Gemini failed ({_err(e)})")
    ok = get_secret("OPENROUTER_API_KEY")
    if ok:
        try:
            return _openrouter(prompt, ok), "OpenRouter"
        except Exception as e:
            errors.append(f"OpenRouter failed ({_err(e)})")
    if not gk and not ok:
        return None, "No LLM key configured"
    return None, "; ".join(errors)
