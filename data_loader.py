"""
Data loader — reads the Excel workbook and returns clean DataFrames.

We deliberately re-read once per app boot, cache in module-level globals,
and expose accessor functions. Dash callbacks must never touch the file
system directly.
"""
from __future__ import annotations

import pandas as pd
from .config import RAW_DATA_PATH

# Module-level caches
_MONITORING: pd.DataFrame | None = None
_SCOUTING: pd.DataFrame | None = None


def load_excel_data(path=RAW_DATA_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read both relevant sheets once; subsequent calls hit the cache."""
    global _MONITORING, _SCOUTING
    if _MONITORING is None or _SCOUTING is None:
        _MONITORING = pd.read_excel(path, sheet_name="Monitoring_Data")
        _SCOUTING = pd.read_excel(path, sheet_name="Scouting_Data")
    return _MONITORING.copy(), _SCOUTING.copy()


def get_monitoring() -> pd.DataFrame:
    df, _ = load_excel_data()
    return df


def get_scouting() -> pd.DataFrame:
    _, df = load_excel_data()
    return df


def clean_monitoring_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Lightweight cleaning — defensive coercions only. The dataset is
    already well-formed but we guard against future edits.
    """
    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date", "Player"])

    numeric_cols = [
        "Total_Distance", "HSR", "Sprint_Distance", "Accelerations", "Decelerations",
        "RPE", "Session_Load", "Acute_Load", "Chronic_Load", "ACWR",
        "HRV_RMSSD", "Resting_HR", "Fatigue_Score", "Soreness_Score",
        "Sleep_Quality", "CMJ_Height",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Injury_Label" in df.columns:
        df["Injury_Label"] = df["Injury_Label"].fillna(0).astype(int)

    df = df.sort_values(["Player", "Date"]).reset_index(drop=True)
    return df
