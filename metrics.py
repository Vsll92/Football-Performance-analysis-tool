"""
Metrics — all derived-variable calculations.

Every derived column is computed here and labelled explicitly so the
methodology page and processed-data exports are transparent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ACWR_ZONES


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["Week"] = df["Date"].dt.to_period("W").astype(str)
    df["Week_Start"] = df["Date"].dt.to_period("W").apply(lambda r: r.start_time)
    df["DayOfWeek"] = df["Date"].dt.day_name()
    df["Month"] = df["Date"].dt.month_name()
    return df


def calculate_rolling_sum(df: pd.DataFrame, col: str = "Session_Load", window: int = 7,
                          name: str | None = None) -> pd.DataFrame:
    """Rolling SUM per player. Kept for transparency/exports."""
    name = name or f"{col}_RollSum{window}"
    df = df.copy().sort_values(["Player", "Date"])
    df[name] = df.groupby("Player")[col].transform(
        lambda s: s.rolling(window=window, min_periods=1).sum()
    )
    return df


def calculate_rolling_mean(df: pd.DataFrame, col: str, window: int = 7,
                           name: str | None = None) -> pd.DataFrame:
    """Rolling MEAN per player. Used for ACWR_Calc and readiness context."""
    name = name or f"{col}_RollMean{window}"
    df = df.copy().sort_values(["Player", "Date"])
    df[name] = df.groupby("Player")[col].transform(
        lambda s: s.rolling(window=window, min_periods=1).mean()
    )
    return df

# Backward-compatible alias used by older page code.
def calculate_rolling_load(df: pd.DataFrame, col: str = "Session_Load", window: int = 7,
                           name: str | None = None) -> pd.DataFrame:
    return calculate_rolling_sum(df, col=col, window=window, name=name)


def calculate_acwr(df: pd.DataFrame, acute_col: str = "Acute_Load_Avg_7",
                   chronic_col: str = "Chronic_Load_Avg_28", name: str = "ACWR_Calc") -> pd.DataFrame:
    """
    Calculated ACWR = 7-day rolling average Session_Load / 28-day rolling average Session_Load.

    This fixes the common error of dividing 7-day SUM by 28-day SUM, which produces
    artificially low values around 0.25–0.45 and is not comparable to standard ACWR.
    """
    df = df.copy()
    df[name] = np.where(df[chronic_col] > 0, df[acute_col] / df[chronic_col], np.nan)
    return df


def classify_acwr_zone(acwr: float) -> str:
    if pd.isna(acwr):
        return "Unknown"
    if acwr < ACWR_ZONES["underload"][1]:
        return "Underload"
    if acwr < ACWR_ZONES["optimal"][1]:
        return "Optimal"
    if acwr < ACWR_ZONES["caution"][1]:
        return "Caution"
    return "High Spike"


def calculate_player_baselines(df: pd.DataFrame,
                               variables=("CMJ_Height", "HRV_RMSSD", "Resting_HR")) -> pd.DataFrame:
    """Per-player baseline = mean of first 14 available sessions."""
    baselines = []
    for player, g in df.sort_values("Date").groupby("Player"):
        head = g.head(14)
        row = {"Player": player}
        for var in variables:
            if var in head.columns:
                row[f"{var}_Baseline"] = head[var].mean()
        baselines.append(row)
    return pd.DataFrame(baselines)


def attach_baselines(df: pd.DataFrame, baselines: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(baselines, on="Player", how="left")
    for var in ("CMJ_Height", "HRV_RMSSD", "Resting_HR"):
        b = f"{var}_Baseline"
        if var in df.columns and b in df.columns:
            df[f"{var}_PctChange"] = np.where(df[b] != 0, (df[var] - df[b]) / df[b] * 100.0, np.nan)
    return df


def add_proxy_variables(df: pd.DataFrame) -> pd.DataFrame:
    """Clearly labelled derived proxies; none are claimed as directly measured."""
    df = df.copy()
    # Simple scaled proxies for page/report context; defensively handle zero variance.
    def z(col):
        if col not in df.columns or df[col].std(ddof=0) == 0:
            return pd.Series(0, index=df.index)
        return (df[col] - df[col].mean()) / df[col].std(ddof=0)
    df["High_Intensity_Exposure"] = df.get("HSR", 0) + df.get("Sprint_Distance", 0)
    df["Mechanical_Load_Proxy"] = (z("Total_Distance") + z("HSR") + z("Sprint_Distance") +
                                    z("Accelerations") + z("Decelerations"))
    df["Wellness_Stress_Proxy"] = (z("Fatigue_Score") + z("Soreness_Score") - z("Sleep_Quality") -
                                    z("HRV_RMSSD") + z("Resting_HR"))
    df["Recovery_Risk_Composite"] = (df.get("Fatigue_Score", 0) + df.get("Soreness_Score", 0) +
                                      (6 - df.get("Sleep_Quality", 3)) +
                                      (df.get("HRV_RMSSD_PctChange", 0) <= -10).astype(int) +
                                      (df.get("CMJ_Height_PctChange", 0) <= -5).astype(int))
    return df


def add_monitoring_flags(df: pd.DataFrame, acwr_col: str = "ACWR") -> pd.DataFrame:
    """Boolean flags consumed by the readiness scorer and coach report."""
    df = df.copy()
    if acwr_col not in df.columns:
        acwr_col = "ACWR"
    df["Flag_ACWR_High"] = df[acwr_col] > 1.3
    df["Flag_ACWR_Spike"] = df[acwr_col] > 1.5
    df["Flag_Fatigue_High"] = df["Fatigue_Score"] >= 4.0
    df["Flag_Soreness_High"] = df["Soreness_Score"] >= 4.0
    df["Flag_Sleep_Poor"] = df["Sleep_Quality"] <= 2.5
    df["Flag_HRV_Drop"] = df.get("HRV_RMSSD_PctChange", 0) <= -10.0
    df["Flag_CMJ_Drop"] = df.get("CMJ_Height_PctChange", 0) <= -5.0
    df["Flag_RHR_Up"] = df.get("Resting_HR_PctChange", 0) >= 5.0
    df["High_Load_Day_Flag"] = df.groupby("Player")["Session_Load"].transform(
        lambda s: s >= s.quantile(0.75)
    )
    return df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """One-shot feature-engineering pipeline used by app boot and exports."""
    df = add_time_features(df)
    # Keep sums for transparency and historical compatibility.
    df = calculate_rolling_sum(df, "Session_Load", 7, "Acute_Load_Calc")
    df = calculate_rolling_sum(df, "Session_Load", 28, "Chronic_Load_Calc")
    # Correct ACWR_Calc uses rolling averages.
    df = calculate_rolling_mean(df, "Session_Load", 7, "Acute_Load_Avg_7")
    df = calculate_rolling_mean(df, "Session_Load", 28, "Chronic_Load_Avg_28")
    df = calculate_acwr(df, "Acute_Load_Avg_7", "Chronic_Load_Avg_28", "ACWR_Calc")
    df = calculate_rolling_mean(df, "Fatigue_Score", 7)
    df = calculate_rolling_mean(df, "Sleep_Quality", 7)
    df = calculate_rolling_mean(df, "Soreness_Score", 7)

    baselines = calculate_player_baselines(df)
    df = attach_baselines(df, baselines)
    df = add_proxy_variables(df)
    df = add_monitoring_flags(df, acwr_col="ACWR")
    df["ACWR_Zone"] = df["ACWR"].apply(classify_acwr_zone)
    df["ACWR_Calc_Zone"] = df["ACWR_Calc"].apply(classify_acwr_zone)
    df["ACWR_Calc_Difference"] = df["ACWR_Calc"] - df["ACWR"]
    return df
