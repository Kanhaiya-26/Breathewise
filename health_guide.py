"""Loads the supplied AQI health workbook (read-only) and provides search."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

WORKBOOK = Path(__file__).parent / "AQI_Health_Database_100_Expanded.xlsx"
RECORDS_SHEET = "100 Health Records"
README_SHEET = "Read Me"

COL_ID = "Record ID"
COL_TITLE = "Presentation / health concern"
COL_SYSTEM = "Body system"
COL_TRIAGE = "Triage level"
COL_EMERGENCY = "Emergency warning signs"
COL_REVIEW = "Clinical review status"
COL_POLLUTANT = "Pollutant relevance"


def load_records() -> pd.DataFrame:
    df = pd.read_excel(WORKBOOK, sheet_name=RECORDS_SHEET, dtype=str, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df.fillna("").apply(lambda s: s.str.strip())


def load_readme() -> pd.DataFrame:
    df = pd.read_excel(WORKBOOK, sheet_name=README_SHEET, header=None, dtype=str, engine="openpyxl")
    df = df.fillna("")
    return df.iloc[:, :2].set_axis(["Item", "Detail"], axis=1)


def search(df: pd.DataFrame, query: str = "", systems=None, triage=None) -> pd.DataFrame:
    out = df
    if systems:
        out = out[out[COL_SYSTEM].isin(systems)]
    if triage:
        out = out[out[COL_TRIAGE].isin(triage)]
    q = (query or "").strip().lower()
    if q:
        blob = out.astype(str).agg(" ".join, axis=1).str.lower()
        mask = pd.Series(True, index=out.index)
        for term in q.split():
            mask &= blob.str.contains(term, regex=False)
        out = out[mask]
    return out


def records_for_pollutant(df: pd.DataFrame, pollutant_label: str) -> pd.DataFrame:
    """Records whose 'Pollutant relevance' text mentions the pollutant (text match only)."""
    if not pollutant_label or COL_POLLUTANT not in df:
        return df.iloc[0:0]
    key = pollutant_label.split(" ")[0].upper()  # e.g. "PM2.5", "OZONE", "NITROGEN"
    aliases = {"OZONE": ["OZONE", "O3"], "NITROGEN": ["NO2"], "SULPHUR": ["SO2"], "CARBON": ["CO"]}
    terms = aliases.get(key, [key])
    text = df[COL_POLLUTANT].str.upper()
    mask = pd.Series(False, index=df.index)
    for t in terms:
        mask |= text.str.contains(t, regex=False)
    return df[mask]
