"""BreatheWise - air quality, explained kindly. Streamlit MVP."""
from __future__ import annotations

import html

import altair as alt
import pandas as pd
import streamlit as st

import data_provider as dp
import health_guide as hg
import intelligence as ai

st.set_page_config(page_title="BreatheWise", page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

LIGHT = dict(bg="#F7F7F2", card="#FFFFFF", ink="#24352D", brand="#245B45", sage="#E5EDE5", teal="#4F8980",
             terra="#B94E36", line="#E4E7DF", muted="#5F6F66", row="#EEF0EA", onbrand="#FFFFFF",
             note="#FBF1EC", noteink="#5A2A1D", emerg="#F8E3DC", emergink="#6A2512", stale="#F7EDD5", staleink="#6E5212")
DARK = dict(bg="#101C18", card="#192923", ink="#F3F3EA", brand="#75AD8A", sage="#24382E", teal="#6FB0A5",
            terra="#D9775E", line="#33483B", muted="#A9B8AD", row="#24382E", onbrand="#101C18",
            note="#2B231D", noteink="#F0D9CF", emerg="#3A201A", emergink="#FFD9CC", stale="#2F2A1A", staleink="#EBD9A6")


def _vars(t: dict) -> str:
    return "".join(f"--{k}:{v};" for k, v in t.items())


THEME = st.session_state.get("theme", "System")
if THEME == "Dark":
    TOKENS = f":root {{ {_vars(DARK)} }}"
elif THEME == "Light":
    TOKENS = f":root {{ {_vars(LIGHT)} }}"
else:
    TOKENS = f":root {{ {_vars(LIGHT)} }} @media (prefers-color-scheme: dark) {{ :root {{ {_vars(DARK)} }} }}"

# chart colours (Vega/deck.gl need real colours, not CSS variables)
_ct = DARK if THEME == "Dark" else LIGHT
CH_TXT, CH_MUT, CH_GRID = (_ct["ink"], _ct["muted"], _ct["line"]) if THEME != "System" else ("#7D8C83", "#7D8C83", "#8A968F55")
BASEMAP = "dark_no_labels" if THEME == "Dark" else "light_no_labels"

# HTML colour references follow the active theme
CARD, FOREST, MUTED, INK = "var(--card)", "var(--brand)", "var(--muted)", "var(--ink)"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Inter:wght@400;500;600&display=swap');
""" + TOKENS + """
html, body, .stApp, .stMarkdown, p, li, label, input, textarea, button { font-family:'Inter',sans-serif; }
.stApp { background: var(--bg); color: var(--ink); }
.stApp p, .stApp li, .stApp label, [data-testid="stWidgetLabel"] p, [data-testid="stMarkdownContainer"] { color: var(--ink); }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: var(--muted) !important; }
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, [data-testid="stMainMenu"], [data-testid="stToolbarActions"], [data-testid="stAppDeployButton"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"] { display:none !important; }
.block-container { max-width: 1240px; padding: 1.2rem 1.6rem 2.5rem 1.6rem !important; }

/* ---- sidebar shell ---- */
[data-testid="stSidebar"] { background: var(--card) !important; border-right:1px solid var(--line); min-width:232px !important; max-width:260px !important; }
[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top:.4rem; }
.bw-tag { color:var(--muted); font-size:.74rem; margin:-.25rem 0 .9rem 2.6rem; }
.bw-side-label { text-transform:uppercase; letter-spacing:.08em; font-size:.66rem; font-weight:600; color:var(--muted); margin:1rem 0 .3rem 0; }
.bw-side-status { font-size:.74rem; color:var(--muted); line-height:1.6; margin:.9rem 0 .6rem 0; padding:.6rem .7rem;
  border:1px solid var(--line); border-radius:10px; background:var(--bg); }
.bw-side-status .bw-pill { margin-bottom:.3rem; }
[data-testid="stSidebar"] [role="radiogroup"] { gap:2px; }
[data-testid="stSidebar"] [role="radiogroup"] label { width:100%; padding:.45rem .7rem; border-radius:9px; margin:0; cursor:pointer; }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display:none; }
[data-testid="stSidebar"] [role="radiogroup"] label p { font-size:.9rem; font-weight:500; color:var(--ink) !important; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:var(--sage); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background:var(--brand); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p { color:var(--onbrand) !important; }
.bw-hero { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin-bottom:.8rem; flex-wrap:wrap; }
.bw-hero h2 { margin:0 !important; }
.bw-sub { color:var(--muted); font-size:.85rem; }
h1,h2,h3,h4 { font-family:'Fraunces',serif !important; color: var(--brand) !important; letter-spacing:-0.01em; }
h2 { font-size:1.6rem !important; margin: .2rem 0 .1rem 0 !important; }
h4 { font-size:1.05rem !important; margin: 0 0 .5rem 0 !important; }

.bw-brand { display:flex; align-items:center; gap:.55rem; height:42px; }
.bw-logo { width:32px; height:32px; border-radius:9px; background:var(--brand); color:var(--onbrand);
  display:flex; align-items:center; justify-content:center; font-size:1rem; }
.bw-name { font-family:'Fraunces',serif; font-size:1.3rem; font-weight:700; color:var(--brand); }
.bw-navline { border-bottom:1px solid var(--line); margin:.3rem 0 1.1rem 0; }
[data-testid="stButtonGroup"] button {
  border:none !important; background:transparent !important; color:var(--muted) !important;
  font-weight:500 !important; border-radius:999px !important; padding:.3rem .85rem !important; }
[data-testid="stButtonGroup"] button[aria-checked="true"], [data-testid="stButtonGroup"] button[kind$="Active"] {
  background:var(--brand) !important; color:var(--onbrand) !important; }
[data-testid="stButtonGroup"] button[aria-checked="true"] p, [data-testid="stButtonGroup"] button[kind$="Active"] p {
  color:var(--onbrand) !important; }
[data-testid="stButtonGroup"] button p { font-size:.9rem !important; color:inherit !important; }

[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]),
div[data-testid="stLayoutWrapper"] > div[data-testid="stVerticalBlock"][class*="border"] {
  background: var(--card); border:1px solid var(--line) !important; border-radius:16px !important;
  box-shadow: 0 1px 2px rgba(16,28,24,.04), 0 4px 14px rgba(16,28,24,.04); }
.bw-eyebrow { text-transform:uppercase; letter-spacing:.09em; font-size:.68rem; font-weight:600; color:var(--muted); }
.bw-aqi { font-family:'Fraunces',serif; font-size:4rem; line-height:1; font-weight:700; margin:.3rem 0 .1rem 0; }
.bw-cat { display:inline-block; padding:.22rem .7rem; border-radius:999px; font-weight:600; font-size:.83rem; }
.bw-meta { color:var(--muted); font-size:.82rem; line-height:1.55; margin-top:.7rem; }
.bw-meta b { color:var(--ink); font-weight:600; }
.bw-pill { display:inline-block; padding:.16rem .6rem; border-radius:999px; font-size:.7rem; font-weight:600; letter-spacing:.03em; }
.bw-live { background:var(--sage); color:var(--brand); border:1px solid var(--line); }
.bw-demo { background:var(--note); color:var(--terra); border:1px solid var(--terra); }
.bw-stale { background:var(--stale); color:var(--staleink); border:1px solid var(--line); }
.bw-note { background:var(--note); border:1px solid var(--line); border-left:3px solid var(--terra); border-radius:12px;
  padding:.6rem .9rem; font-size:.85rem; color:var(--noteink); margin:.2rem 0 1rem 0; }
.bw-note b, .bw-note i { color:var(--noteink); }
.bw-emerg { background:var(--emerg); border-radius:10px; padding:.55rem .8rem; color:var(--emergink); font-size:.88rem;
  font-weight:500; margin-bottom:.6rem; }
.bw-emerg b { color:var(--emergink); }
.bw-row { display:flex; align-items:center; gap:.7rem; padding:.5rem 0; border-bottom:1px solid var(--row); color:var(--ink); }
.bw-row:last-child { border-bottom:none; }
.bw-rank { width:24px; color:var(--muted); font-size:.8rem; font-weight:600; }
.bw-city { flex:1; font-size:.9rem; font-weight:500; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--ink); }
.bw-num { font-family:'Fraunces',serif; font-weight:700; font-size:1.05rem; min-width:42px; text-align:right; }
.bw-dot { width:9px; height:9px; border-radius:50%; flex:none; }
.bw-tip { display:flex; gap:.6rem; padding:.4rem 0; font-size:.88rem; line-height:1.45; color:var(--ink); }
.bw-tip span:first-child { color:var(--teal); font-weight:700; }
.bw-empty { color:var(--muted); font-size:.86rem; padding:.5rem 0; }
.bw-kv { font-size:.86rem; line-height:1.5; margin:.25rem 0; color:var(--ink); }
.bw-kv b { color:var(--brand); font-weight:600; }
.bw-footer { color:var(--muted); font-size:.75rem; text-align:center; margin-top:2rem; padding-top:1rem; border-top:1px solid var(--line); }
[data-testid="stMetric"] { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:.7rem .9rem; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div { font-family:'Fraunces',serif; color:var(--brand) !important; }
[data-testid="stMetricLabel"] p { color:var(--muted) !important; }
[data-testid="stExpander"], [data-testid="stExpander"] details { background:var(--card) !important; border-color:var(--line) !important; border-radius:14px !important; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary p { color:var(--ink) !important; font-weight:500; }
.stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div, [data-baseweb="input"] {
  background:var(--card) !important; color:var(--ink) !important; border-color:var(--line) !important; border-radius:10px !important; }
[data-baseweb="select"] span, [data-baseweb="tag"] span { color:var(--ink) !important; }
.stButton button, .stLinkButton a { background:var(--brand) !important; color:var(--onbrand) !important; border:none !important; border-radius:999px !important; }
.stLinkButton a p, .stButton button p { color:var(--onbrand) !important; }
[data-testid="stAlert"] { border-radius:12px; }
@media (max-width: 740px) {
  .block-container { padding: .6rem .9rem 2rem .9rem !important; }
  .bw-aqi { font-size:3.2rem; }
  h2 { font-size:1.3rem !important; }
}
</style>
""", unsafe_allow_html=True)

esc = html.escape

# ------------------------------------------------------------------ cached data access


@st.cache_data(show_spinner=False)
def get_records():
    return hg.load_records(), hg.load_readme()


@st.cache_data(ttl=900, show_spinner=False)
def fetch_waqi(city: str, token: str):
    try:
        return dp.waqi_city(city, token), None
    except dp.ProviderError as e:
        return None, str(e)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_many(cities: tuple, token: str):
    """Parallel WAQI requests, cached as one unit so reruns make no API calls."""
    from concurrent.futures import ThreadPoolExecutor

    def one(c):
        try:
            return c, dp.waqi_city(c, token), None
        except dp.ProviderError as e:
            return c, None, str(e)

    with ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(one, cities))


@st.cache_data(ttl=900, show_spinner=False)
def fetch_bounds(token: str):
    try:
        return dp.waqi_bounds(token), None
    except dp.ProviderError as e:
        return [], str(e)


@st.cache_data(ttl=900, show_spinner=False)
def fetch_openaq(lat: float, lon: float, key: str):
    try:
        return dp.openaq_near(lat, lon, key), None
    except dp.ProviderError as e:
        return None, str(e)


@st.cache_data(show_spinner=False)
def india_boundaries():
    """State and national outlines from the bundled GeoJSON.

    The file mixes district polygons with whole-state polygons (``district`` is null). Only the
    whole-state polygons are used: a segment shared by two states is a state border, a segment used
    by one state is the national outline. No vertex is moved or added.
    """
    import json
    from collections import Counter
    from pathlib import Path

    g = json.loads((Path(__file__).parent / "data" / "india_districts.geojson").read_text(encoding="utf-8"))
    all_edges, labels = Counter(), {}
    for f in g["features"]:
        if f["properties"].get("district") is not None:
            continue
        st_nm = f["properties"]["state"]
        cs = f["geometry"]["coordinates"]
        polys = cs if f["geometry"]["type"] == "MultiPolygon" else [cs]
        edges = set()
        for poly in polys:
            for ring in poly:
                for a, b in zip(ring, ring[1:]):
                    edges.add((tuple(a), tuple(b)) if tuple(a) < tuple(b) else (tuple(b), tuple(a)))
            if st_nm in ("Jammu and Kashmir", "Ladakh"):
                labels.setdefault(st_nm, []).extend(poly[0])
        all_edges.update(edges)
    states = [{"path": [list(a), list(b)]} for (a, b), n in all_edges.items() if n == 2]
    nation = [{"path": [list(a), list(b)]} for (a, b), n in all_edges.items() if n == 1]
    # the two UTs are adjacent: short labels at each UT's vertex mean keep them inside and apart
    short = {"Jammu and Kashmir": "J&K", "Ladakh": "Ladakh"}
    lab = [{"text": short[k], "lon": sum(p[0] for p in v) / len(v), "lat": sum(p[1] for p in v) / len(v)}
           for k, v in labels.items()]
    xs = [p for e in all_edges for pt in e for p in pt[:1]]
    ys = [pt[1] for e in all_edges for pt in e]
    return states, nation, lab, (min(xs), min(ys), max(xs), max(ys))


def idw_grid(points: list[tuple[float, float, float]], step: float = 0.2, max_km: float = 60.0):
    """Inverse-distance-weighted AQI estimates on a grid, only within max_km of a real station."""
    import math

    if len(points) < 3:
        return []
    cells = []
    lat0, lat1 = min(p[1] for p in points) - 0.6, max(p[1] for p in points) + 0.6
    lon0, lon1 = min(p[0] for p in points) - 0.6, max(p[0] for p in points) + 0.6
    lat = lat0
    while lat <= lat1:
        lon = lon0
        kx = 111.0 * math.cos(math.radians(lat))
        while lon <= lon1:
            num = den = 0.0
            near = False
            for x, y, v in points:
                d = math.hypot((lon - x) * kx, (lat - y) * 111.0)
                if d <= max_km:
                    near = True
                w = 1.0 / max(d, 1.0) ** 2
                num += w * v
                den += w
            if near:
                cells.append({"lon": round(lon, 3), "lat": round(lat, 3), "aqi": round(num / den)})
            lon += step
        lat += step
    return cells


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_history(lat: float, lon: float, key: str, period: str):
    try:
        return dp.openaq_history(lat, lon, key, period), None
    except dp.ProviderError as e:
        return None, str(e)


def history_section(where: dp.Reading | None):
    """Time selector + genuine OpenAQ history. Never derived from current readings."""
    period = st.segmented_control("Period", list(dp.PERIODS), default="Last 24 Hours", key="period") or "Last 24 Hours"
    with st.container(border=True):
        st.markdown(f"#### Historical trend · {period}")
        if not use_live or where is None or where.lat is None:
            st.markdown("<div class='bw-empty'>Historical data unavailable in demo mode — no history is "
                        "generated.</div>", unsafe_allow_html=True)
            return
        if not openaq_key:
            st.markdown("<div class='bw-empty'>Historical data unavailable: WAQI's free API provides current "
                        "readings only, and no OpenAQ key is configured.</div>", unsafe_allow_html=True)
            return
        with st.spinner("Loading history…"):
            hist, herr = fetch_history(float(where.lat), float(where.lon), openaq_key, period)
        if not hist:
            st.markdown(f"<div class='bw-empty'>{esc(herr)}</div>", unsafe_allow_html=True)
            return
        station, unit, rows = hist
        hdf = pd.DataFrame(rows)
        hdf["time"] = pd.to_datetime(hdf["time"], utc=True)
        ch = alt.Chart(hdf).mark_area(line={"color": "#4F8980"}, color="#4F898055").encode(
            x=alt.X("time:T", title="Time (UTC)", axis=alt.Axis(labelColor=CH_MUT, titleColor=CH_MUT)),
            y=alt.Y("value:Q", title=f"PM2.5 ({unit})", axis=alt.Axis(labelColor=CH_MUT, titleColor=CH_MUT,
                                                                      gridColor=CH_GRID)),
            tooltip=[alt.Tooltip("time:T", format="%d %b %H:%M"), alt.Tooltip("value:Q", format=".1f")])
        st.altair_chart(ch.properties(height=230, background="transparent").configure_view(strokeWidth=0), width="stretch")
        m1, m2, m3 = st.columns(3)
        m1.metric("Average", f"{hdf['value'].mean():.1f} {unit}")
        m2.metric("Peak", f"{hdf['value'].max():.1f} {unit}")
        m3.metric("Data points", len(hdf))
        st.caption(f"{station} · OpenAQ v3 · hourly averages · "
                   f"{hdf['time'].min():%d %b %Y %H:%M} – {hdf['time'].max():%d %b %Y %H:%M} UTC. "
                   "These are raw PM2.5 concentrations, not AQI. WAQI's free API provides no history, so the "
                   "map shows current readings only.")


@st.cache_data(ttl=3600, show_spinner=False)
def cached_llm(summary: str):
    return ai.llm_explain(summary)


waqi_token = dp.get_secret("WAQI_API_TOKEN")
openaq_key = dp.get_secret("OPENAQ_API_KEY")
llm_ready = bool(dp.get_secret("GEMINI_API_KEY") or dp.get_secret("OPENROUTER_API_KEY"))

DEFAULT_CITIES = ["Delhi", "Mumbai", "Kolkata", "Chennai", "Bengaluru", "Hyderabad", "Lucknow", "Patna"]
PAGES = ["Overview", "Live Map", "Hotspots", "Health Guide", "Insights", "Medical Help"]

if "hotspot_text" not in st.session_state:
    st.session_state.hotspot_text = "\n".join(DEFAULT_CITIES)
if "demo" not in st.session_state:
    st.session_state.demo = not waqi_token

# ------------------------------------------------------------------ app shell (sidebar)
ICONS = {"Overview": "◉", "Live Map": "◎", "Hotspots": "▲", "Health Guide": "✚", "Insights": "◈",
         "Medical Help": "☎"}
if "page" not in st.session_state:
    qp = st.query_params.get("page")
    st.session_state.page = qp if qp in PAGES else "Overview"


def go(target: str):
    st.session_state.page = target


use_live = bool(waqi_token) and not st.session_state.demo
with st.sidebar:
    st.markdown("<div class='bw-brand'><div class='bw-logo'>🌿</div><div class='bw-name'>BreatheWise</div></div>"
                "<div class='bw-tag'>Air quality &amp; health</div>", unsafe_allow_html=True)
    page = st.radio("Navigation", PAGES, key="page", label_visibility="collapsed",
                    format_func=lambda p: f"{ICONS[p]}  {p}")
    st.markdown("<div class='bw-side-label'>Location</div>", unsafe_allow_html=True)
    if use_live:
        city = st.selectbox("Location", DEFAULT_CITIES, index=0, accept_new_options=True,
                            label_visibility="collapsed", placeholder="Type a city…")
    else:
        city = st.selectbox("Location", [s[0] for s in dp.DEMO_STATIONS], index=3, label_visibility="collapsed")
    st.markdown("<div class='bw-side-label'>Theme</div>", unsafe_allow_html=True)
    st.segmented_control("Theme", ["Light", "Dark", "System"], default="System", key="theme",
                         label_visibility="collapsed")
    status_slot = st.empty()
    with st.expander("Data settings"):
        st.toggle("Demo mode (synthetic data)", key="demo", disabled=not waqi_token,
                  help="Without a WAQI token the app always runs in demo mode.")
        st.text_area("Hotspot cities (one per line)", key="hotspot_text", height=150)
        st.caption(f"WAQI: {'connected' if waqi_token else 'no token'} · OpenAQ: "
                   f"{'connected' if openaq_key else 'no key'} · AI: {'on' if llm_ready else 'off'}")
        if st.button("Refresh data", width="stretch"):
            st.cache_data.clear()
            st.rerun()

# ------------------------------------------------------------------ data
errors = {}
hotspot_cities = [x.strip() for x in st.session_state.hotspot_text.splitlines() if x.strip()][:15]
if use_live:
    main, err = fetch_waqi((city or "Delhi").strip(), waqi_token)
    if err:
        errors[city] = err
    hotspots = []
    for c, r, e in fetch_many(tuple(hotspot_cities), waqi_token):
        if r:
            hotspots.append(r)
        else:
            errors[c] = e
    if main is not None and all(h.station != main.station for h in hotspots):
        hotspots.append(main)
else:
    hotspots = dp.demo_readings()
    main = next((r for r in hotspots if r.station == city), hotspots[0])

records, readme = get_records()
ranked = ai.rank_hotspots(hotspots)


def is_stale(r: dp.Reading) -> bool:
    return any(" h old" in n for n in r.quality_notes)


def status_pill(r: dp.Reading | None = None) -> str:
    if not use_live or (r is not None and not r.is_live):
        return f"<span class='bw-pill bw-demo'>{dp.DEMO_LABEL}</span>"
    if r is not None and is_stale(r):
        return "<span class='bw-pill bw-stale'>LIVE · POSSIBLY STALE</span>"
    return "<span class='bw-pill bw-live'>● LIVE · WAQI</span>"


def page_header(title: str, subtitle: str = ""):
    st.markdown(f"<div class='bw-hero'><div><h2>{esc(title)}</h2>"
                f"<div class='bw-sub'>{esc(subtitle)}</div></div></div>", unsafe_allow_html=True)


def safety_note():
    st.markdown(
        "<div class='bw-note'><b>Not medical advice.</b> Health content is an educational draft that "
        "<b>requires clinical review</b>; it does not diagnose or prescribe. Chest pain, severe breathlessness, "
        "confusion, fainting or blue lips — <b>call emergency services now</b>.</div>",
        unsafe_allow_html=True)


def tips_for(aqi: float | None) -> list[str]:
    """General public guidance by US-EPA AQI band (not personalised medical advice)."""
    if aqi is None:
        return ["No current AQI — check again later before planning long outdoor activity."]
    if aqi <= 50:
        return ["Air quality is good — a fine time for outdoor activity.",
                "Ventilate your home while outdoor air is clean."]
    if aqi <= 100:
        return ["Most people can be active outdoors.",
                "Unusually sensitive people may want to shorten long or intense outdoor exertion.",
                "Watch for symptoms such as coughing or shortness of breath."]
    if aqi <= 150:
        return ["Sensitive groups — children, older adults, pregnancy, heart or lung disease — reduce long or intense outdoor exertion.",
                "Prefer lighter activity and take more breaks.",
                "Keep reliever medicines you have been prescribed within reach."]
    if aqi <= 200:
        return ["Everyone should reduce prolonged or heavy outdoor exertion.",
                "Sensitive groups should move activities indoors or reschedule.",
                "Keep windows closed during peak pollution; use air filtration if available."]
    return ["Avoid outdoor physical activity; stay indoors with windows closed.",
            "Sensitive groups should remain indoors and keep activity levels low.",
            "Seek medical help promptly if breathing becomes difficult."]


def aqi_card(r: dp.Reading):
    cat, colour = dp.aqi_category(r.aqi)
    aqi_txt = f"{r.aqi:.0f}" if r.aqi is not None else "—"
    dom = dp.POLLUTANT_NAMES.get(r.dominant or "", r.dominant or "n/a")
    st.markdown(
        f"<div style='display:flex;justify-content:space-between;align-items:center'>"
        f"<span class='bw-eyebrow'>Current air quality</span>{status_pill(r)}</div>"
        f"<div class='bw-aqi' style='color:{colour}'>{aqi_txt}</div>"
        f"<span class='bw-cat' style='background:{colour}1f;color:{colour}'>{esc(cat)}</span>"
        f"<div class='bw-meta'><b>{esc(r.station)}</b><br>"
        f"Dominant pollutant: <b>{esc(dom)}</b> · US-EPA AQI scale<br>"
        f"Station time: {esc(r.measured_at or 'not reported')}<br>"
        f"Fetched: {esc(r.fetched_at)}<br>"
        f"Source: {esc(r.source)}{(' — ' + esc('; '.join(r.attribution[:2]))) if r.attribution else ''}</div>",
        unsafe_allow_html=True)
    for n in r.quality_notes:
        if "sub-indices" not in n:
            st.caption(f"⚠️ {n}")


def pollutant_chart(r: dp.Reading):
    if not r.pollutants:
        st.markdown("<div class='bw-empty'>This station reported no individual pollutant values.</div>",
                    unsafe_allow_html=True)
        return
    unit = next(iter(r.pollutants.values()))[1]
    df = pd.DataFrame([{"Pollutant": dp.POLLUTANT_NAMES.get(k, k).split(" (")[0] if k not in ("pm25", "pm10")
                        else dp.POLLUTANT_NAMES[k], "Value": v, "Unit": u,
                        "Colour": dp.aqi_category(v)[1] if u == "AQI sub-index" else "#4F8980"}
                       for k, (v, u) in r.pollutants.items()])
    base = alt.Chart(df).encode(
        y=alt.Y("Pollutant:N", sort="-x", title=None, axis=alt.Axis(labelFontSize=12, labelColor=CH_TXT)),
        x=alt.X("Value:Q", title=unit, axis=alt.Axis(labelColor=CH_MUT, titleColor=CH_MUT, gridColor=CH_GRID)),
    )
    bars = base.mark_bar(cornerRadiusEnd=5, height=16).encode(color=alt.Color("Colour:N", scale=None),
                                                               tooltip=["Pollutant", "Value", "Unit"])
    text = base.mark_text(align="left", dx=5, fontSize=12, color=CH_TXT).encode(text=alt.Text("Value:Q", format=".0f"))
    st.altair_chart((bars + text).properties(height=34 * len(df) + 30, background="transparent")
                    .configure_view(strokeWidth=0), width="stretch")
    if unit == "AQI sub-index":
        st.caption("Values are WAQI US-EPA AQI sub-indices per pollutant — not concentrations.")


def hotspot_rows(items: list[dp.Reading], limit: int = 8):
    if not items:
        st.markdown("<div class='bw-empty'>No comparable readings available.</div>", unsafe_allow_html=True)
        return
    rows = []
    for i, r in enumerate(items[:limit]):
        cat, colour = dp.aqi_category(r.aqi)
        name = r.station.split(",")[0]
        flag = " ⚠️" if is_stale(r) else ""
        rows.append(f"<div class='bw-row'><span class='bw-rank'>{i + 1}</span>"
                    f"<span class='bw-dot' style='background:{colour}'></span>"
                    f"<span class='bw-city' title='{esc(r.station)}'>{esc(name)}{flag}</span>"
                    f"<span style='color:{MUTED};font-size:.75rem'>{esc(cat)}</span>"
                    f"<span class='bw-num' style='color:{colour}'>{r.aqi:.0f}</span></div>")
    st.markdown("".join(rows), unsafe_allow_html=True)


def record_card(row: pd.Series):
    with st.expander(f"{row[hg.COL_TITLE]}  ·  {row[hg.COL_SYSTEM]}  ·  {row[hg.COL_TRIAGE]}"):
        if row.get(hg.COL_EMERGENCY):
            st.markdown(f"<div class='bw-emerg'>🚨 <b>Emergency warning signs:</b> {esc(row[hg.COL_EMERGENCY])}"
                        " — seek emergency care.</div>", unsafe_allow_html=True)
        cols = [c for c in records.columns if c not in (hg.COL_TITLE, hg.COL_EMERGENCY) and row[c]]
        left, right = st.columns(2)
        half = (len(cols) + 1) // 2
        for target, chunk in ((left, cols[:half]), (right, cols[half:])):
            with target:
                st.markdown("".join(f"<div class='bw-kv'><b>{esc(c)}</b><br>{esc(row[c])}</div>" for c in chunk),
                            unsafe_allow_html=True)


# ================================================================== pages
if page == "Overview":
    place = main.station.split(",")[0] if main else city
    page_header(place, "Live air quality · US-EPA AQI scale")
    if not use_live:
        st.markdown(f"<div class='bw-note'><b>{dp.DEMO_LABEL}</b> — synthetic sample stations. Configure a WAQI "
                    "token and turn off demo mode in Data settings for live readings.</div>", unsafe_allow_html=True)

    if main is None:
        st.error(f"No reading available for “{city}” ({errors.get(city)}). Nothing is shown rather than a guess.")
    else:
        c1, c2 = st.columns([1, 1.35], gap="medium")
        with c1:
            with st.container(border=True):
                aqi_card(main)
        with c2:
            with st.container(border=True):
                st.markdown("#### Pollutants")
                pollutant_chart(main)

        c3, c4, c5 = st.columns([1.25, 1, 1], gap="medium")
        with c3:
            with st.container(border=True):
                st.markdown("#### PM2.5 · last 24 hours")
                hist = None
                if use_live and openaq_key and main.lat is not None:
                    hist, herr = fetch_history(float(main.lat), float(main.lon), openaq_key, "Last 24 Hours")
                if hist:
                    station, unit, rows = hist
                    hdf = pd.DataFrame(rows)
                    hdf["time"] = pd.to_datetime(hdf["time"], utc=True)
                    ch = alt.Chart(hdf).mark_area(line={"color": "#4F8980"}, color="#4F898040").encode(
                        x=alt.X("time:T", title=None, axis=alt.Axis(format="%H:%M", labelColor=CH_MUT, tickCount=5)),
                        y=alt.Y("value:Q", title=unit, axis=alt.Axis(labelColor=CH_MUT, titleColor=CH_MUT,
                                                                      gridColor=CH_GRID, tickCount=4)),
                        tooltip=[alt.Tooltip("time:T", format="%d %b %H:%M"), alt.Tooltip("value:Q", format=".1f")])
                    st.altair_chart(ch.properties(height=150, background="transparent").configure_view(strokeWidth=0),
                                    width="stretch")
                    st.caption(f"{station} · OpenAQ · hourly concentrations (not AQI)")
                else:
                    st.markdown("<div class='bw-empty'>Historical data unavailable for this station/source.</div>",
                                unsafe_allow_html=True)
        with c4:
            with st.container(border=True):
                st.markdown("#### What to do today")
                st.markdown("".join(f"<div class='bw-tip'><span>✓</span><span>{esc(t)}</span></div>"
                                    for t in tips_for(main.aqi)), unsafe_allow_html=True)
                st.caption("General guidance by AQI band, not medical advice.")
        with c5:
            with st.container(border=True):
                st.markdown("#### Top hotspots")
                hotspot_rows(ranked, 5)

        q1, q2, q3, q4 = st.columns(4)
        q1.button("◎  Open live map", on_click=go, args=("Live Map",), width="stretch")
        q2.button("▲  All hotspots", on_click=go, args=("Hotspots",), width="stretch")
        q3.button("✚  Health guide", on_click=go, args=("Health Guide",), width="stretch")
        q4.button("☎  Medical help", on_click=go, args=("Medical Help",), width="stretch")
    safety_note()

elif page == "Live Map":
    page_header("Live map", "Real monitoring stations coloured by US-EPA AQI")
    region, berr = fetch_bounds(waqi_token) if use_live else ([], None)
    seen, pts = set(), []
    for r in ranked + region:  # city feeds first (richer), then region stations
        if r.lat is None or r.lon is None:
            continue
        k = (round(float(r.lat), 3), round(float(r.lon), 3))
        name = r.station.split(",")[0].strip().lower()
        if k not in seen and name not in seen:  # same station can come from the city feed and the region list
            seen.update({k, name})
            pts.append(r)
    if not use_live or not pts:
        with st.container(border=True):
            st.markdown("<div class='bw-empty'>The map needs live WAQI readings with station coordinates. "
                        "Demo stations are fictional and are deliberately not placed on a real map.</div>",
                        unsafe_allow_html=True)
    else:
        import pydeck as pdk

        def rgb(hexc):
            return [int(hexc[i:i + 2], 16) for i in (1, 3, 5)]

        mdf = pd.DataFrame([{
            "lat": float(r.lat), "lon": float(r.lon), "name": r.station, "aqi": f"{r.aqi:.0f}",
            "cat": dp.aqi_category(r.aqi)[0], "src": r.source, "time": r.measured_at or "not reported",
            "stale": " · possibly stale" if is_stale(r) else "", "fill": rgb(dp.aqi_category(r.aqi)[1]) + [215],
        } for r in pts])
        layer = pdk.Layer("ScatterplotLayer", mdf, get_position=["lon", "lat"], get_fill_color="fill",
                          get_line_color=[255, 253, 248], line_width_min_pixels=1.5, stroked=True,
                          # pydeck treats bare strings as JS expressions: string literals must be quoted
                          get_radius=5, radius_units='"pixels"', radius_min_pixels=4, radius_max_pixels=7,
                          pickable=True, auto_highlight=True)
        states, nation, geo_labels, (bx0, by0, bx1, by1) = india_boundaries()
        line_rgb = rgb(DARK["brand"]) if THEME == "Dark" else rgb(LIGHT["brand"])
        state_layer = pdk.Layer("PathLayer", states, get_path="path", get_color=line_rgb + [90],
                                width_units='"pixels"', get_width=0.7, pickable=False)
        nation_layer = pdk.Layer("PathLayer", nation, get_path="path", get_color=line_rgb + [220],
                                 width_units='"pixels"', get_width=1.6, pickable=False)
        names = pdk.Layer("TextLayer", geo_labels, get_position=["lon", "lat"], get_text="text", get_size=11,
                          font_family='"Inter, Arial, sans-serif"', get_color=line_rgb + [210], font_weight=600,
                          pickable=False)
        t1, t2, t3 = st.columns([1, 1, 2])
        show_heat = t1.toggle("Estimated overlay", value=True, key="heat",
                              help="Estimated AQI between monitoring stations; not a measurement.")
        show_base = t2.toggle("Basemap", value=True, key="basemap",
                              help="Basemap tiles draw their own borders underneath the India outline.")
        cells = idw_grid([(float(r.lon), float(r.lat), float(r.aqi)) for r in pts]) if show_heat else []
        # soft, overlapping translucent discs blend into a smooth estimated surface (no hard grid squares)
        heat = pdk.Layer("ScatterplotLayer", [dict(c, fill=rgb(dp.aqi_category(c["aqi"])[1]) + [55]) for c in cells],
                         get_position=["lon", "lat"], get_radius=26000, radius_units='"meters"', stroked=False,
                         get_fill_color="fill", pickable=False)
        import math

        def merc(lat):
            return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))

        mid_lat = math.degrees(math.atan(math.sinh((merc(by0) + merc(by1)) / 2)))
        # fit the full north-south extent (6.8°N–37.1°N) in the 560 px map with ~20% padding;
        # deck.gl's world is 512 px wide at zoom 0
        zoom = min(math.log2(560 / ((merc(by1) - merc(by0)) / (2 * math.pi) * 1.2 * 512)), 4.4)
        view = pdk.ViewState(latitude=mid_lat, longitude=(bx0 + bx1) / 2, zoom=round(zoom, 2))
        deck = pdk.Deck(
            layers=[heat, state_layer, nation_layer, names, layer], map_provider="carto" if show_base else None,
            map_style=BASEMAP if show_base else None,
            initial_view_state=view,
            tooltip={"html": "<b>{name}</b><br/>AQI <b>{aqi}</b> · {cat} (US-EPA scale)<br/>"
                             "Source: {src}<br/>Observed: {time}{stale}",
                     "style": {"backgroundColor": "#245B45", "color": "#f4eedf", "fontSize": "12px",
                               "borderRadius": "8px", "padding": "8px 10px"}})
        with st.container(border=True):
            st.pydeck_chart(deck, height=560, width="stretch")
            legend = "".join(f"<span style='margin-right:1rem;font-size:.8rem;white-space:nowrap'><span class='bw-dot' "
                             f"style='display:inline-block;background:{c};margin-right:.35rem'></span>{l} "
                             f"<span style='color:{MUTED}'>({lo}–{hi if hi < 10000 else '500'})</span></span>"
                             for (lo, (hi, l, c)) in zip([0, 51, 101, 151, 201, 301], dp.AQI_BANDS))
            st.markdown(f"<div class='bw-eyebrow' style='margin:.3rem 0'>AQI legend · US-EPA scale (used by WAQI)"
                        f"</div>{legend}", unsafe_allow_html=True)
            st.caption(f"{len(pts)} stations · hover or tap a marker · WAQI / aqicn.org · fetched {pts[0].fetched_at}"
                       + (" · shading = **estimated AQI between monitoring stations** (within 60 km of a real "
                          "station; not a measurement)" if cells else ""))
        with st.expander("About this map"):
            st.markdown(
                "<div class='bw-kv'><b>Scale</b><br>WAQI publishes AQI on the US-EPA scale, so US-EPA categories are "
                "used. India's CPCB scale uses different breakpoints and 24-hour averages and is not applied here.</div>"
                "<div class='bw-kv'><b>Boundaries</b><br>National and state outlines come from the whole-state polygons "
                "of the open <i>udit-001/india-maps-data</i> dataset, with no vertices moved. Its extent follows India's "
                "official depiction, including Gilgit-Baltistan, PoK and Aksai Chin, which are disputed and partly "
                "administered by Pakistan and China. It is community-curated, not an official Survey of India file. "
                "Basemap tiles © CARTO / OpenStreetMap contributors may show different lines underneath.</div>"
                "<div class='bw-kv'><b>Estimated shading</b><br>Inverse-distance weighting between real stations, "
                "drawn only within 60 km of one. Blank areas have no nearby monitor.</div>", unsafe_allow_html=True)
        history_section(main)
        if berr:
            st.caption(f"Region station list unavailable ({berr}); showing hotspot cities only.")

elif page == "Hotspots":
    page_header("Hotspots", "Where the air is heaviest right now, ranked on comparable US-EPA AQI readings.")
    if not ranked:
        st.info("No comparable readings available.")
    else:
        df = pd.DataFrame([{
            "Rank": i + 1, "Station": r.station.split(",")[0], "AQI": r.aqi, "Category": dp.aqi_category(r.aqi)[0],
            "Dominant": dp.POLLUTANT_NAMES.get(r.dominant or "", r.dominant or "n/a"),
            "Station time": r.measured_at or "n/a", "Source": r.source, "Colour": dp.aqi_category(r.aqi)[1],
            "Stale": "⚠️" if is_stale(r) else "",
        } for i, r in enumerate(ranked)])
        c1, c2 = st.columns([1.5, 1], gap="medium")
        with c1:
            with st.container(border=True):
                st.markdown(f"#### AQI by station &nbsp;{status_pill(ranked[0])}", unsafe_allow_html=True)
                base = alt.Chart(df).encode(
                    y=alt.Y("Station:N", sort="-x", title=None, axis=alt.Axis(labelColor=CH_TXT, labelFontSize=12)),
                    x=alt.X("AQI:Q", title="AQI (US-EPA scale)",
                            axis=alt.Axis(labelColor=CH_MUT, titleColor=CH_MUT, gridColor=CH_GRID)),
                )
                bars = base.mark_bar(cornerRadiusEnd=5, height=18).encode(
                    color=alt.Color("Colour:N", scale=None),
                    tooltip=["Station", "AQI", "Category", "Dominant", "Station time", "Source"])
                text = base.mark_text(align="left", dx=5, color=CH_TXT, fontSize=12).encode(text="AQI:Q")
                rule = alt.Chart(pd.DataFrame({"x": [100]})).mark_rule(strokeDash=[4, 4], color="#B94E36").encode(x="x:Q")
                st.altair_chart((bars + text + rule).properties(height=36 * len(df) + 40, background="transparent")
                                .configure_view(strokeWidth=0), width="stretch")
                st.caption("Dashed line: AQI 100, above which sensitive groups are affected.")
        with c2:
            with st.container(border=True):
                st.markdown("#### Ranking")
                hotspot_rows(ranked, 15)
        with st.expander("Full table with timestamps and sources"):
            st.dataframe(df.drop(columns="Colour"), hide_index=True, width="stretch")
        stale = [r.station for r in ranked if is_stale(r)]
        if stale:
            st.warning("Possibly stale readings: " + ", ".join(stale))
    if errors:
        with st.expander(f"{len(errors)} location(s) unavailable"):
            for k, v in errors.items():
                st.write(f"- **{k}**: {v}")

elif page == "Health Guide":
    page_header("Health guide", f"{len(records)} symptom and risk presentations from the AQI Health Database.")
    st.markdown(
        f"<div class='bw-note'>Source: <i>{esc(hg.WORKBOOK.name)}</i>. Every record is marked "
        "<b>“Educational draft — clinical review required”</b>. Medicine examples are generic illustrations, "
        "<b>not recommendations</b> — confirm with a clinician or pharmacist.</div>", unsafe_allow_html=True)
    with st.container(border=True):
        g1, g2, g3 = st.columns([2.2, 1, 1])
        q = g1.text_input("Search", placeholder="Search symptoms, conditions, groups — e.g. wheeze, asthma, pregnancy")
        systems = g2.multiselect("Body system", sorted(records[hg.COL_SYSTEM].unique()))
        triage = g3.multiselect("Triage level", sorted(records[hg.COL_TRIAGE].unique()))
    res = hg.search(records, q, systems, triage)
    st.markdown(f"<div style='color:{MUTED};font-size:.85rem;margin:.6rem 0'>{len(res)} matching record(s)</div>",
                unsafe_allow_html=True)
    for _, row in res.head(40).iterrows():
        record_card(row)
    if len(res) > 40:
        st.caption("Showing the first 40 — refine your search to see more.")
    with st.expander("About this database (Read Me sheet)"):
        st.dataframe(readme, hide_index=True, width="stretch")
    safety_note()

elif page == "Insights":
    page_header("Insights", "A summary of current readings across your monitored cities.")
    f = ai.facts(hotspots)
    summary = ai.python_summary(f)
    if f.get("count"):
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Stations", f["count"])
        m2.metric("Average AQI", f["mean_aqi"])
        m3.metric("Above AQI 100", f["above_100"])
        m4.metric("Above AQI 150", f["above_150"])
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown(f"#### Summary &nbsp;{status_pill(ranked[0] if ranked else None)}", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:.92rem;line-height:1.6'>{esc(summary)}</div>", unsafe_allow_html=True)
            if ranked:
                st.caption(f"Source: {ranked[0].source} · Fetched {ranked[0].fetched_at}")
            if llm_ready:
                if st.button("Explain in plain language"):
                    with st.spinner("Writing…"):
                        text, provider = cached_llm(summary)
                    if text:
                        st.markdown(text)
                        st.caption("AI-written wording of the summary above; the figures above take precedence. "
                                   "Not medical advice.")
                    else:
                        st.caption("A plain-language explanation isn't available right now.")
    with c2:
        with st.container(border=True):
            st.markdown("#### Station ranking")
            hotspot_rows(ranked, 8)
    if ranked:
        cat_df = pd.DataFrame([{"Category": dp.aqi_category(r.aqi)[0], "Colour": dp.aqi_category(r.aqi)[1]}
                               for r in ranked]).value_counts().reset_index(name="Stations")
        with st.container(border=True):
            st.markdown("#### Stations by AQI category")
            order = [b[1] for b in dp.AQI_BANDS]
            ch = alt.Chart(cat_df).mark_bar(cornerRadiusEnd=5, height=20).encode(
                y=alt.Y("Category:N", sort=order, title=None, axis=alt.Axis(labelColor=CH_TXT, labelLimit=260)),
                x=alt.X("Stations:Q", title="Number of stations", axis=alt.Axis(tickMinStep=1, labelColor=CH_MUT,
                                                                                 titleColor=CH_MUT, gridColor=CH_GRID)),
                color=alt.Color("Colour:N", scale=None), tooltip=["Category", "Stations"])
            st.altair_chart(ch.properties(height=40 * len(cat_df) + 40, background="transparent").configure_view(strokeWidth=0),
                            width="stretch")

elif page == "Medical Help":
    from urllib.parse import quote_plus

    page_header("Medical help", "Emergency numbers and quick links to find care near you.")
    st.markdown(
        "<div class='bw-emerg' style='font-size:1rem;padding:.9rem 1.1rem;border-left:4px solid #9b3b22'>🚨 "
        "<b>Severe breathlessness, chest pain, fainting, confusion or blue lips require immediate emergency "
        "medical help. Call 112.</b> Do not delay emergency care to check AQI or use this application.</div>",
        unsafe_allow_html=True)
    e1, e2 = st.columns(2, gap="medium")
    for col, num, title, desc in (
        (e1, "112", "Pan-India emergency response",
         "Emergency Response Support System (ERSS): a single number for police, fire and medical emergencies."),
        (e2, "102", "National Ambulance Service",
         "Ambulance service under the National Health Mission, run by state governments. Scope and coverage "
         "vary by state."),
    ):
        with col:
            st.markdown(
                f"<a href='tel:{num}' style='text-decoration:none'><div style='background:var(--card);color:var(--ink);"
                f"border:1px solid var(--line);border-radius:16px;padding:1.1rem 1.3rem;margin-bottom:.8rem;"
                f"box-shadow:0 1px 2px rgba(16,28,24,.04),0 4px 14px rgba(16,28,24,.04)'>"
                f"<div style='font-family:Fraunces,serif;font-size:2.6rem;font-weight:700;line-height:1;"
                f"color:#C43D32'>{num}</div>"
                f"<div style='font-weight:600;margin:.3rem 0 .2rem 0;color:var(--ink)'>{title}</div>"
                f"<div style='font-size:.84rem;color:var(--muted)'>{desc}</div>"
                f"<div style='margin-top:.6rem;font-size:.8rem;font-weight:600;color:var(--brand)'>📞 Tap to call {num}"
                f"</div></div></a>",
                unsafe_allow_html=True)
    st.caption("Availability and response times can vary by location and circumstances. Tap-to-call works on phones.")

    with st.container(border=True):
        st.markdown("#### Find healthcare nearby")
        loc = st.text_input("City, locality or PIN code", placeholder="e.g. Connaught Place, Delhi or 110001")
        cats = [("🏥 Hospitals", "hospitals"), ("🚑 Emergency departments", "hospital emergency department"),
                ("🩺 Clinics", "clinics"), ("💊 Pharmacies", "pharmacies"),
                ("🧪 Diagnostic laboratories", "diagnostic laboratories"),
                ("🫁 Pulmonologists", "pulmonologist respiratory specialist")]
        where = loc.strip()
        cols = st.columns(3)
        for i, (label, term) in enumerate(cats):
            query = f"{term} near {where}" if where else f"{term} near me"
            cols[i % 3].link_button(label, f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}",
                                    width="stretch")
        st.caption("Opens a Google Maps search in a new tab. " + (
            f"Searching near “{where}”." if where else
            "No location entered: Google Maps will use your device location only if you allow it in your browser.")
            + " BreatheWise does not verify opening hours, emergency services, beds, oxygen or equipment — "
              "call ahead when you can.")

    with st.container(border=True):
        st.markdown("#### Air-pollution warning signs from the health guide")
        urgent = records[records[hg.COL_TRIAGE].isin(["Emergency", "Urgent"]) &
                         records[hg.COL_SYSTEM].str.contains("Lung|Resp|Heart|Cardiac", regex=True)]
        st.markdown("".join(
            f"<div class='bw-row' style='align-items:flex-start'><span class='bw-city' style='white-space:normal;"
            f"flex:0 0 38%'><b>{esc(r[hg.COL_TITLE])}</b><br><span style='color:{MUTED};font-size:.75rem'>"
            f"{esc(r[hg.COL_TRIAGE])}</span></span><span style='flex:1;font-size:.85rem'>🚨 "
            f"{esc(r[hg.COL_EMERGENCY])}</span></div>" for _, r in urgent.head(10).iterrows()), unsafe_allow_html=True)
        st.caption(f"{len(urgent)} urgent/emergency respiratory or cardiac records from {hg.WORKBOOK.name}. "
                   "Educational draft — clinical review required. Not a diagnosis. See Health Guide for full records.")
    safety_note()

# ------------------------------------------------------------------ sidebar status + footer
with status_slot.container():
    fetched = ranked[0].fetched_at if ranked else "—"
    st.markdown(f"<div class='bw-side-status'>{status_pill(main)}<div>Updated {esc(fetched)}</div>"
                f"<div>{len(ranked)} stations · cached 15 min</div></div>", unsafe_allow_html=True)

st.markdown(
    "<div class='bw-footer'>Data: WAQI / aqicn.org · OpenAQ v3 · AQI Health Database workbook. "
    "Demo values are synthetic. BreatheWise does not provide diagnoses or treatment recommendations.</div>",
    unsafe_allow_html=True)
