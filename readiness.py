"""
Readiness scoring — combines flags into a single risk index (0..N points)
and a traffic-light status (Green / Yellow / Red).

This is a MONITORING SUPPORT TOOL, not a medical or diagnostic system.
Thresholds are practical guides documented in `config.READINESS_RULES`.
"""
from __future__ import annotations

import pandas as pd

from .config import READINESS_RULES, READINESS_STATUS_THRESHOLDS


def calculate_readiness_score(row: pd.Series) -> int:
    """Sum risk points for a single row (one player × one date)."""
    pts = 0
    if pd.notna(row.get("ACWR")) and row["ACWR"] > READINESS_RULES["acwr_high"]["threshold"]:
        pts += READINESS_RULES["acwr_high"]["points"]
    if pd.notna(row.get("ACWR")) and row["ACWR"] > READINESS_RULES["acwr_very_high"]["threshold"]:
        pts += READINESS_RULES["acwr_very_high"]["points"]
    if pd.notna(row.get("Fatigue_Score")) and row["Fatigue_Score"] >= READINESS_RULES["fatigue_high"]["threshold"]:
        pts += READINESS_RULES["fatigue_high"]["points"]
    if pd.notna(row.get("Soreness_Score")) and row["Soreness_Score"] >= READINESS_RULES["soreness_high"]["threshold"]:
        pts += READINESS_RULES["soreness_high"]["points"]
    if pd.notna(row.get("Sleep_Quality")) and row["Sleep_Quality"] <= READINESS_RULES["sleep_low"]["threshold"]:
        pts += READINESS_RULES["sleep_low"]["points"]
    if pd.notna(row.get("HRV_RMSSD_PctChange")) and row["HRV_RMSSD_PctChange"] <= -100.0 * READINESS_RULES["hrv_drop"]["threshold"]:
        pts += READINESS_RULES["hrv_drop"]["points"]
    if pd.notna(row.get("CMJ_Height_PctChange")) and row["CMJ_Height_PctChange"] <= -100.0 * READINESS_RULES["cmj_drop"]["threshold"]:
        pts += READINESS_RULES["cmj_drop"]["points"]
    if pd.notna(row.get("Resting_HR_PctChange")) and row["Resting_HR_PctChange"] >= 100.0 * READINESS_RULES["rhr_up"]["threshold"]:
        pts += READINESS_RULES["rhr_up"]["points"]
    return int(pts)


def classify_readiness_status(score: int) -> str:
    for status, (lo, hi) in READINESS_STATUS_THRESHOLDS.items():
        if lo <= score <= hi:
            return status
    return "Green"


def attach_readiness(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Readiness_Score"] = df.apply(calculate_readiness_score, axis=1)
    df["Readiness_Status"] = df["Readiness_Score"].apply(classify_readiness_status)
    return df


def explain_readiness(row: pd.Series) -> list[str]:
    """Human-readable list of triggered reasons — used in player profile."""
    reasons = []
    if pd.notna(row.get("ACWR")) and row["ACWR"] > 1.5:
        reasons.append(f"ACWR spike at {row['ACWR']:.2f} (> 1.5)")
    elif pd.notna(row.get("ACWR")) and row["ACWR"] > 1.3:
        reasons.append(f"ACWR elevated at {row['ACWR']:.2f} (> 1.3)")
    if pd.notna(row.get("Fatigue_Score")) and row["Fatigue_Score"] >= 4:
        reasons.append(f"High self-reported fatigue ({row['Fatigue_Score']:.1f}/5)")
    if pd.notna(row.get("Soreness_Score")) and row["Soreness_Score"] >= 4:
        reasons.append(f"High soreness ({row['Soreness_Score']:.1f}/5)")
    if pd.notna(row.get("Sleep_Quality")) and row["Sleep_Quality"] <= 2.5:
        reasons.append(f"Poor sleep quality ({row['Sleep_Quality']:.1f}/5)")
    if pd.notna(row.get("HRV_RMSSD_PctChange")) and row["HRV_RMSSD_PctChange"] <= -10:
        reasons.append(f"HRV {row['HRV_RMSSD_PctChange']:.1f}% below baseline")
    if pd.notna(row.get("CMJ_Height_PctChange")) and row["CMJ_Height_PctChange"] <= -5:
        reasons.append(f"CMJ {row['CMJ_Height_PctChange']:.1f}% below baseline")
    if pd.notna(row.get("Resting_HR_PctChange")) and row["Resting_HR_PctChange"] >= 5:
        reasons.append(f"Resting HR {row['Resting_HR_PctChange']:.1f}% above baseline")
    if not reasons:
        reasons.append("All monitored indicators within typical ranges.")
    return reasons
