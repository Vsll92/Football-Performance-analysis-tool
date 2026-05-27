"""Dash-independent safe filter helpers used by QA scripts and mirrored in layout.py."""
from __future__ import annotations
import pandas as pd


def safe_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v not in (None, "")]
    if value == "":
        return []
    return [value]


def safe_metric(metric, default: str, allowed_metrics):
    allowed = list(allowed_metrics)
    if metric in allowed:
        return metric
    return default if default in allowed else (allowed[0] if allowed else default)


def safe_metrics_list(metrics, default_metrics, allowed_metrics):
    allowed = set(allowed_metrics)
    vals = [m for m in safe_list(metrics) if m in allowed]
    if vals:
        return vals
    return [m for m in default_metrics if m in allowed] or list(allowed)[:1]


def safe_focus_player(filtered_df: pd.DataFrame, current_player=None):
    if filtered_df is None or filtered_df.empty or "Player" not in filtered_df.columns:
        return current_player
    players = sorted(filtered_df["Player"].dropna().unique().tolist(), key=lambda x: int(str(x).split("_")[-1]))
    if current_player in players:
        return current_player
    return players[0] if players else current_player


def apply_filters(df: pd.DataFrame, players=None, positions=None, start_date=None, end_date=None, statuses=None, injury_filter=None):
    out = df.copy()
    players = safe_list(players)
    positions = safe_list(positions)
    statuses = safe_list(statuses)
    if players and "Player" in out.columns:
        out = out[out["Player"].isin(players)]
    if positions and "Position" in out.columns:
        out = out[out["Position"].isin(positions)]
    if start_date and "Date" in out.columns:
        out = out[out["Date"] >= pd.to_datetime(start_date)]
    if end_date and "Date" in out.columns:
        out = out[out["Date"] <= pd.to_datetime(end_date)]
    if statuses and "Readiness_Status" in out.columns:
        out = out[out["Readiness_Status"].isin(statuses)]
    if injury_filter and injury_filter != "all" and "Injury_Label" in out.columns:
        if injury_filter == "injured":
            out = out[out["Injury_Label"] == 1]
        elif injury_filter == "non_injured":
            out = out[out["Injury_Label"] == 0]
    return out
