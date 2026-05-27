"""
preprocessing.py — single entry point that returns the fully-engineered DataFrame.

Combines:
- raw Excel load (data_loader)
- cleaning
- feature engineering (metrics.build_features)
- readiness scoring (readiness.attach_readiness)

This is what `app.py` calls at boot.
"""
from __future__ import annotations

import pandas as pd

from .data_loader import get_monitoring, clean_monitoring_data
from .metrics import build_features
from .readiness import attach_readiness


def build_master_dataframe() -> pd.DataFrame:
    raw = get_monitoring()
    clean = clean_monitoring_data(raw)
    engineered = build_features(clean)
    return attach_readiness(engineered)


def data_quality_report(df: pd.DataFrame) -> dict:
    """Return a small dict the methodology page renders."""
    return {
        "n_rows":      len(df),
        "n_players":   df["Player"].nunique(),
        "n_positions": df["Position"].nunique(),
        "date_start":  df["Date"].min().date().isoformat(),
        "date_end":    df["Date"].max().date().isoformat(),
        "n_injuries":  int(df["Injury_Label"].sum()),
        "injury_rate": float(df["Injury_Label"].mean()) * 100,
        "missing_total": int(df.isna().sum().sum()),
        "n_derived":   sum(1 for c in df.columns if c.endswith(("_Calc",
                                                                  "_Baseline",
                                                                  "_PctChange",
                                                                  "_RollMean7"))
                            or c.startswith("Flag_")
                            or c in {"Readiness_Score", "Readiness_Status",
                                      "ACWR_Zone", "Week", "Week_Start"}),
    }
