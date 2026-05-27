"""
layout.py — Shared visual layout primitives used by every page.

Every page is built from these reusable components so the look-and-feel
stays consistent and the codebase stays small.
"""
from __future__ import annotations

import pandas as pd
from dash import dcc, html

from .config import COLORS, READINESS_COLORS


# -----------------------------------------------------------------------------
# Page header (title + subtitle + optional stat-strip)
# -----------------------------------------------------------------------------
def page_header(title: str, subtitle: str = "", stats: list[tuple] | None = None):
    """`stats` is a list of (label, value) tuples shown on the right."""
    stat_blocks = []
    for lbl, val in (stats or []):
        stat_blocks.append(html.Div(className="page-stat", children=[
            html.Span(lbl, className="lbl"),
            html.Strong(str(val)),
        ]))
    return html.Div(className="page-header", children=[
        html.Div(className="page-header-inner", children=[
            html.H1(title, className="page-title"),
            html.P(subtitle, className="page-subtitle") if subtitle else None,
        ]),
        html.Div(stat_blocks, className="page-header-stats") if stat_blocks else None,
    ])


# -----------------------------------------------------------------------------
# Section bar (for splitting long pages into clear blocks)
# -----------------------------------------------------------------------------
def section_bar(label: str):
    return html.Div(className="section-bar", children=[
        html.H2(label),
        html.Div(className="section-line"),
    ])


# -----------------------------------------------------------------------------
# KPI card
# -----------------------------------------------------------------------------
def kpi(label: str, value, sub: str | None = None,
        tone: str = "info", icon: str | None = None):
    """
    tone ∈ {info, ok, warn, bad}.
    """
    cls = f"kpi-card kpi-{tone}"
    children = []
    if icon:
        children.append(html.Div(icon, className="kpi-icon"))
    children += [
        html.Div(label, className="kpi-label"),
        html.Div(str(value), className="kpi-value"),
    ]
    if sub:
        children.append(html.Div(sub, className="kpi-sub"))
    return html.Div(children, className=cls)


def kpi_strip(kpis: list):
    return html.Div(kpis, className="kpi-grid")


# -----------------------------------------------------------------------------
# Chart card — title + subtitle + content + insight
# -----------------------------------------------------------------------------
def chart_card(title: str, subtitle: str = "",
                content=None, insight=None,
                tag: str | None = None):
    head = [
        html.Div([
            html.H4(title, className="card-title"),
            html.Div(subtitle, className="card-subtitle") if subtitle else None,
        ])
    ]
    if tag:
        head.append(html.Span(tag, className="card-tag"))
    return html.Div(className="card-pf", children=[
        html.Div(className="card-head", children=head),
        content,
        render_insight(insight) if insight else None,
    ])


# -----------------------------------------------------------------------------
# Insight renderer
# -----------------------------------------------------------------------------
def render_insight(insight: dict | None):
    if insight is None:
        return None
    if isinstance(insight, str):
        insight = {"headline": insight, "detail": None,
                   "coaching": None, "caution": None, "level": "info"}
    level = insight.get("level", "info")
    children = [
        html.Div(className="insight-headline", children=[
            html.Span("Main insight", className="ins-tag"),
            html.Span(insight.get("headline", "")),
        ]),
    ]
    if insight.get("detail"):
        children.append(html.Div(insight["detail"], className="insight-detail"))
    if insight.get("coaching"):
        children.append(html.Div(insight["coaching"], className="insight-coaching"))
    if insight.get("caution"):
        children.append(html.Div(insight["caution"], className="insight-caution"))
    return html.Div(children, className=f"insight-box {level}")


# -----------------------------------------------------------------------------
# Traffic-light badge
# -----------------------------------------------------------------------------
def traffic_badge(status: str):
    cls = "green" if status == "Green" else "yellow" if status == "Yellow" else "red"
    return html.Span(status, className=f"traffic-badge {cls}")


# -----------------------------------------------------------------------------
# Filters: small wrappers around dcc components
# -----------------------------------------------------------------------------
def filter_field(label: str, control):
    return html.Div([
        html.Div(label, className="filter-label"),
        control,
    ])


def player_dropdown(df: pd.DataFrame, id_: str, multi: bool = True,
                      value=None, placeholder: str = "All players"):
    players = sorted(df["Player"].unique().tolist(),
                      key=lambda x: int(x.split("_")[-1]))
    return dcc.Dropdown(
        id=id_,
        options=[{"label": p, "value": p} for p in players],
        value=value if value is not None else ([] if multi else players[0]),
        multi=multi, placeholder=placeholder, clearable=True,
        className="dash-dropdown",
    )


def position_dropdown(df: pd.DataFrame, id_: str, multi: bool = True,
                        value=None, placeholder: str = "All positions"):
    positions = sorted(df["Position"].unique().tolist())
    return dcc.Dropdown(
        id=id_,
        options=[{"label": p, "value": p} for p in positions],
        value=value if value is not None else ([] if multi else positions[0]),
        multi=multi, placeholder=placeholder, clearable=True,
        className="dash-dropdown",
    )


def date_range_picker(df: pd.DataFrame, id_: str):
    return dcc.DatePickerRange(
        id=id_,
        min_date_allowed=df["Date"].min(),
        max_date_allowed=df["Date"].max(),
        start_date=df["Date"].min(),
        end_date=df["Date"].max(),
        display_format="MMM DD",
    )


def status_filter(id_: str, multi: bool = True):
    return dcc.Dropdown(
        id=id_,
        options=[{"label": s, "value": s} for s in ["Green", "Yellow", "Red"]],
        multi=multi, placeholder="All statuses",
        className="dash-dropdown",
    )


def safe_list(value):
    """Normalize Dash dropdown values: None -> [], scalar -> [scalar], list/tuple -> list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [v for v in value if v not in (None, "")]
    if value == "":
        return []
    return [value]


def safe_metric(metric, default: str, allowed_metrics: list[str] | tuple[str, ...]):
    """Return a valid metric; use default when the dropdown sends None/invalid."""
    allowed = list(allowed_metrics)
    if metric in allowed:
        return metric
    return default if default in allowed else (allowed[0] if allowed else default)


def safe_metrics_list(metrics, default_metrics: list[str], allowed_metrics: list[str] | tuple[str, ...]):
    """Return a non-empty list of valid metrics for multi-select controls."""
    allowed = set(allowed_metrics)
    vals = [m for m in safe_list(metrics) if m in allowed]
    if vals:
        return vals
    return [m for m in default_metrics if m in allowed] or list(allowed)[:1]


def safe_focus_player(filtered_df: pd.DataFrame, current_player=None):
    """Keep focus/radar player consistent with filtered data."""
    if filtered_df is None or filtered_df.empty or "Player" not in filtered_df.columns:
        return current_player
    players = sorted(filtered_df["Player"].dropna().unique().tolist(), key=lambda x: int(str(x).split("_")[-1]))
    if current_player in players:
        return current_player
    return players[0] if players else current_player


def injury_filter_options(id_: str):
    return dcc.Dropdown(
        id=id_,
        options=[
            {"label": "All sessions", "value": "all"},
            {"label": "Injured only", "value": "injured"},
            {"label": "Non-injured only", "value": "non_injured"},
        ],
        value="all", clearable=False, className="dash-dropdown",
    )


def apply_filters(df: pd.DataFrame,
                  players=None, positions=None,
                  start_date=None, end_date=None,
                  statuses=None,
                  injury_filter: str | None = None) -> pd.DataFrame:
    """Shared safe filter function for all pages."""
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


# -----------------------------------------------------------------------------
# Empty-state placeholder
# -----------------------------------------------------------------------------
def empty_state(message: str = "No data in current selection"):
    return html.Div(message, className="muted",
                     style={"textAlign": "center", "padding": "40px"})
