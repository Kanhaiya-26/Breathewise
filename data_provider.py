"""Air-quality data access for BreatheWise.

Providers:
  * WAQI (World Air Quality Index) - https://aqicn.org/json-api/doc/  (token: WAQI_API_TOKEN)
  * OpenAQ API v3                  - https://docs.openaq.org/          (header X-API-Key: OPENAQ_API_KEY)
  * Demo                           - synthetic, deterministic, ALWAYS labelled "DEMO DATA - NOT LIVE"

Every reading carries its source, the station timestamp and data-quality notes.
Nothing here invents a live value: if a provider fails, the caller gets an error, not a guess.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv is optional at runtime
    pass

TIMEOUT = 10
STALE_HOURS = 3
DEMO_LABEL = "DEMO DATA - NOT LIVE"

POLLUTANT_NAMES = {
    "pm25": "PM2.5",
    "pm10": "PM10",
    "o3": "Ozone (O3)",
    "no2": "Nitrogen dioxide (NO2)",
    "so2": "Sulphur dioxide (SO2)",
    "co": "Carbon monoxide (CO)",
}

# US EPA AQI bands (WAQI reports on the US EPA scale)
AQI_BANDS = [
    (50, "Good", "#5b8c5a"),
    (100, "Moderate", "#c9a227"),
    (150, "Unhealthy for Sensitive Groups", "#d08c4a"),
    (200, "Unhealthy", "#b5603f"),
    (300, "Very Unhealthy", "#8a4f6b"),
    (10_000, "Hazardous", "#6b2e2e"),
]


def aqi_category(aqi: float | None) -> tuple[str, str]:
    if aqi is None:
        return "Not available", "#9a9a8a"
    for upper, label, colour in AQI_BANDS:
        if aqi <= upper:
            return label, colour
    return "Hazardous", "#6b2e2e"


def get_secret(name: str) -> str | None:
    """Environment / .env first, then Streamlit secrets. Never logged or displayed."""
    val = os.getenv(name)
    if val:
        return val.strip()
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return None


@dataclass
class Reading:
    station: str
    source: str
    is_live: bool
    aqi: float | None = None              # US-EPA AQI (WAQI) - None if provider gives none
    dominant: str | None = None
    pollutants: dict = field(default_factory=dict)   # key -> (value, unit)
    measured_at: str | None = None        # station time as reported
    lat: float | None = None
    lon: float | None = None
    attribution: list = field(default_factory=list)
    quality_notes: list = field(default_factory=list)
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))


class ProviderError(Exception):
    pass


def _age_note(iso: str | None) -> list:
    if not iso:
        return ["Station did not report a measurement time."]
    try:
        ts = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            return []
        hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        if hours > STALE_HOURS:
            return [f"Reading is {hours:.0f} h old - may not reflect current conditions."]
    except ValueError:
        return ["Station timestamp could not be parsed."]
    return []


def _get(url: str, **kw) -> dict:
    try:
        r = requests.get(url, timeout=TIMEOUT, **kw)
    except requests.Timeout:
        raise ProviderError("Request timed out.")
    except requests.RequestException as e:
        raise ProviderError(f"Network error: {type(e).__name__}")
    if r.status_code == 401 or r.status_code == 403:
        raise ProviderError("API key rejected (401/403).")
    if r.status_code == 429:
        raise ProviderError("Rate limit / quota reached (429).")
    if r.status_code >= 400:
        raise ProviderError(f"HTTP {r.status_code}.")
    try:
        return r.json()
    except ValueError:
        raise ProviderError("Provider returned non-JSON response.")


# ---------------------------------------------------------------- WAQI
def waqi_city(city: str, token: str) -> Reading:
    data = _get(f"https://api.waqi.info/feed/{requests.utils.quote(city)}/", params={"token": token})
    if data.get("status") != "ok":
        raise ProviderError(f"WAQI: {data.get('data', 'unknown error')}")
    d = data["data"]
    aqi = d.get("aqi")
    aqi = float(aqi) if isinstance(aqi, (int, float)) else None
    pollutants = {}
    for k, v in (d.get("iaqi") or {}).items():
        if k in POLLUTANT_NAMES and isinstance(v, dict) and "v" in v:
            pollutants[k] = (float(v["v"]), "AQI sub-index")
    geo = (d.get("city") or {}).get("geo") or [None, None]
    t = d.get("time") or {}
    notes = _age_note(t.get("iso"))
    if aqi is None:
        notes.append("Station returned no numeric AQI ('-').")
    notes.append("WAQI pollutant values are US-EPA AQI sub-indices, not concentrations.")
    return Reading(
        station=(d.get("city") or {}).get("name", city),
        source="WAQI / aqicn.org",
        is_live=True,
        aqi=aqi,
        dominant=d.get("dominentpol"),
        pollutants=pollutants,
        measured_at=t.get("iso") or t.get("s"),
        lat=geo[0], lon=geo[1],
        attribution=[a.get("name") for a in d.get("attributions", []) if a.get("name")],
        quality_notes=notes,
    )


INDIA_BBOX = "6.5,68.0,35.7,97.5"  # lat1,lng1,lat2,lng2 - region view, may include neighbouring stations


def waqi_bounds(token: str, bbox: str = INDIA_BBOX) -> list[Reading]:
    """All WAQI stations WAQI returns for a bounding box, in one request. Non-numeric AQI is dropped."""
    data = _get("https://api.waqi.info/map/bounds/", params={"latlng": bbox, "token": token})
    if data.get("status") != "ok":
        raise ProviderError(f"WAQI: {data.get('data', 'unknown error')}")
    out = []
    for s in data.get("data", []):
        try:
            aqi = float(s.get("aqi"))
        except (TypeError, ValueError):
            continue
        if s.get("lat") is None or s.get("lon") is None:
            continue
        t = (s.get("station") or {}).get("time")
        out.append(Reading(station=(s.get("station") or {}).get("name", f"Station {s.get('uid')}"),
                           source="WAQI / aqicn.org", is_live=True, aqi=aqi, measured_at=t,
                           lat=float(s["lat"]), lon=float(s["lon"]), quality_notes=_age_note(t)))
    return out


# ---------------------------------------------------------------- OpenAQ v3
def openaq_near(lat: float, lon: float, key: str, radius_m: int = 25000) -> Reading:
    headers = {"X-API-Key": key}
    locs = _get(
        "https://api.openaq.org/v3/locations",
        headers=headers,
        params={"coordinates": f"{lat},{lon}", "radius": radius_m, "limit": 100},
    ).get("results", [])
    if not locs:
        raise ProviderError("OpenAQ: no monitoring locations within 25 km.")
    def _last(loc):
        return ((loc.get("datetimeLast") or {}).get("utc")) or ""

    cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
    locs = sorted([l for l in locs if _last(l) >= cutoff], key=_last, reverse=True)
    if not locs:
        raise ProviderError("OpenAQ: no nearby location has reported in the last 48 hours.")
    for loc in locs:
        sensors = {s["id"]: s.get("parameter", {}) for s in loc.get("sensors", [])}
        latest = _get(f"https://api.openaq.org/v3/locations/{loc['id']}/latest", headers=headers).get("results", [])
        pollutants, newest = {}, None
        for row in latest:
            p = sensors.get(row.get("sensorsId"), {})
            name = p.get("name")
            if name in POLLUTANT_NAMES and row.get("value") is not None and row["value"] >= 0:
                pollutants[name] = (float(row["value"]), p.get("units", ""))
                utc = (row.get("datetime") or {}).get("utc")
                if utc and (newest is None or utc > newest):
                    newest = utc
        if pollutants:
            notes = _age_note(newest)
            notes.append("OpenAQ reports raw concentrations; no AQI is computed from them here.")
            prov = (loc.get("provider") or {}).get("name")
            return Reading(
                station=loc.get("name") or f"OpenAQ location {loc['id']}",
                source="OpenAQ v3",
                is_live=True,
                pollutants=pollutants,
                measured_at=newest,
                lat=(loc.get("coordinates") or {}).get("latitude"),
                lon=(loc.get("coordinates") or {}).get("longitude"),
                attribution=[x for x in ["OpenAQ", prov] if x],
                quality_notes=notes,
            )
    raise ProviderError("OpenAQ: nearby locations have no recent pollutant values.")


PERIODS = {"Last 24 Hours": (1, "hours"), "Last 7 Days": (7, "hours"), "Last 1 Month": (30, "hours")}


def openaq_history(lat: float, lon: float, key: str, period: str, parameter: str = "pm25"):
    """Real historical concentrations from OpenAQ v3 /sensors/{id}/hours|days. Returns (station, unit, rows)."""
    days, res = PERIODS[period]
    headers = {"X-API-Key": key}
    locs = _get("https://api.openaq.org/v3/locations", headers=headers,
                params={"coordinates": f"{lat},{lon}", "radius": 25000, "limit": 100}).get("results", [])
    cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S")
    locs = sorted([l for l in locs if ((l.get("datetimeLast") or {}).get("utc") or "") >= cutoff],
                  key=lambda l: (l.get("datetimeLast") or {}).get("utc"), reverse=True)
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    for loc in locs[:5]:
        sensor = next((s for s in loc.get("sensors", []) if (s.get("parameter") or {}).get("name") == parameter), None)
        if not sensor:
            continue
        data = _get(f"https://api.openaq.org/v3/sensors/{sensor['id']}/{res}", headers=headers,
                    params={"datetime_from": start, "datetime_to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            "limit": 1000}).get("results", [])
        rows = [{"time": ((d.get("period") or {}).get("datetimeFrom") or {}).get("utc"), "value": d.get("value")}
                for d in data if d.get("value") is not None and d["value"] >= 0]
        rows = [r for r in rows if r["time"] and r["time"] >= start[:19]]
        if rows:
            return loc.get("name") or f"OpenAQ location {loc['id']}", sensor["parameter"].get("units", ""), rows
    raise ProviderError("Historical data unavailable for nearby OpenAQ stations for this period.")


# ---------------------------------------------------------------- Demo
DEMO_STATIONS = [
    ("Riverside (demo)", 42, "pm25"), ("Old Market (demo)", 87, "pm25"),
    ("Hill Park (demo)", 31, "o3"), ("Ring Road (demo)", 164, "pm25"),
    ("Mill District (demo)", 128, "pm10"), ("Lakeview (demo)", 58, "o3"),
    ("Station Square (demo)", 112, "no2"), ("Green Belt (demo)", 24, "pm25"),
]


def demo_readings() -> list[Reading]:
    """Fixed synthetic values for UI demonstration only. Never presented as live."""
    out = []
    for i, (name, aqi, dom) in enumerate(DEMO_STATIONS):
        pol = {"pm25": (aqi * 0.9, "AQI sub-index"), "pm10": (aqi * 0.6, "AQI sub-index"),
               "o3": (20 + i * 4, "AQI sub-index"), "no2": (10 + i * 3, "AQI sub-index")}
        pol[dom] = (float(aqi), "AQI sub-index")
        out.append(Reading(
            station=name, source=DEMO_LABEL, is_live=False, aqi=float(aqi), dominant=dom,
            pollutants={k: (round(v, 0), u) for k, (v, u) in pol.items()},
            measured_at=None, attribution=["Synthetic sample - no real station"],
            quality_notes=[f"{DEMO_LABEL}: synthetic value for demonstration only."],
        ))
    return out
