"""
visuals.py — Plotly chart factories with a uniform, clean style.

Every chart in the dashboard goes through `apply_layout()` so colours,
fonts, margins, and grids are consistent.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .config import (
    COLORS, PLOTLY_LAYOUT, POSITION_COLORS, READINESS_COLORS,
    ACWR_ZONE_COLORS, VARIABLE_LABELS,
)


# -----------------------------------------------------------------------------
# Core layout
# -----------------------------------------------------------------------------
def apply_layout(fig: go.Figure, height: int = 360,
                  showlegend: bool = True) -> go.Figure:
    fig.update_layout(**PLOTLY_LAYOUT)
    fig.update_layout(height=height, showlegend=showlegend)
    fig.update_xaxes(showline=False)
    fig.update_yaxes(showline=False)
    return fig


def empty_fig(message: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, showarrow=False,
                       font=dict(size=14, color=COLORS["text_muted"]),
                       xref="paper", yref="paper", x=0.5, y=0.5)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return apply_layout(fig, height=320, showlegend=False)


# -----------------------------------------------------------------------------
# Trend (line)
# -----------------------------------------------------------------------------
def line_trend(df: pd.DataFrame, x: str, y: str,
                color: str | None = None,
                title: str | None = None,
                color_map: dict | None = None,
                height: int = 320) -> go.Figure:
    if df.empty:
        return empty_fig()
    fig = px.line(df, x=x, y=y, color=color, markers=False,
                  color_discrete_map=color_map or {})
    fig.update_traces(line=dict(width=2))
    fig.update_xaxes(title="")
    fig.update_yaxes(title=VARIABLE_LABELS.get(y, y))
    return apply_layout(fig, height=height)


# -----------------------------------------------------------------------------
# Ranking (horizontal bar)
# -----------------------------------------------------------------------------
def bar_ranking(df: pd.DataFrame, value: str, label: str,
                  color: str | None = None,
                  n: int = 12, color_map: dict | None = None,
                  height: int = 380) -> go.Figure:
    if df.empty:
        return empty_fig()
    sub = df.sort_values(value, ascending=True).tail(n)
    fig = px.bar(sub, x=value, y=label, orientation="h",
                  color=color, color_discrete_map=color_map or {})
    if color is None:
        fig.update_traces(marker_color=COLORS["accent"])
    fig.update_traces(marker_line_width=0)
    fig.update_xaxes(title=VARIABLE_LABELS.get(value, value))
    fig.update_yaxes(title="")
    return apply_layout(fig, height=max(height, 24 * len(sub)))


# -----------------------------------------------------------------------------
# Distribution / box
# -----------------------------------------------------------------------------
def box_by_group(df: pd.DataFrame, value: str, group: str,
                   color_map: dict | None = None,
                   height: int = 360) -> go.Figure:
    if df.empty:
        return empty_fig()
    fig = px.box(df, x=group, y=value, color=group,
                   color_discrete_map=color_map or {},
                   points="outliers")
    fig.update_xaxes(title="")
    fig.update_yaxes(title=VARIABLE_LABELS.get(value, value))
    fig.update_traces(marker=dict(size=4),
                       line=dict(width=1.5))
    return apply_layout(fig, height=height, showlegend=False)


# -----------------------------------------------------------------------------
# Scatter
# -----------------------------------------------------------------------------
def scatter_relationship(df: pd.DataFrame, x: str, y: str,
                            color: str | None = None,
                            size: str | None = None,
                            color_map: dict | None = None,
                            trendline: bool = False,
                            height: int = 380) -> go.Figure:
    if df.empty:
        return empty_fig()
    kw = dict(color=color, size=size, color_discrete_map=color_map or {},
                hover_data=["Player", "Date"] if "Player" in df.columns else None)
    if trendline:
        try:
            fig = px.scatter(df, x=x, y=y, trendline="ols", **kw)
        except Exception:
            fig = px.scatter(df, x=x, y=y, **kw)
    else:
        fig = px.scatter(df, x=x, y=y, **kw)
    fig.update_traces(marker=dict(line=dict(width=0), opacity=0.75))
    fig.update_xaxes(title=VARIABLE_LABELS.get(x, x))
    fig.update_yaxes(title=VARIABLE_LABELS.get(y, y))
    return apply_layout(fig, height=height)


# -----------------------------------------------------------------------------
# Correlation heatmap
# -----------------------------------------------------------------------------
def heatmap_correlation(df: pd.DataFrame, cols: list[str],
                         height: int = 460) -> go.Figure:
    if df.empty or not cols:
        return empty_fig()
    cm = df[cols].corr()
    labels = [VARIABLE_LABELS.get(c, c) for c in cols]
    fig = go.Figure(data=go.Heatmap(
        z=cm.values, x=labels, y=labels,
        colorscale="RdBu_r", zmid=0, zmin=-1, zmax=1,
        text=cm.round(2).values, texttemplate="%{text}",
        textfont=dict(size=10),
        colorbar=dict(thickness=10),
    ))
    fig.update_xaxes(tickangle=-30)
    return apply_layout(fig, height=height, showlegend=False)


# -----------------------------------------------------------------------------
# ACWR zoned line
# -----------------------------------------------------------------------------
def acwr_zoned_line(df: pd.DataFrame, height: int = 340, metric: str = "ACWR") -> go.Figure:
    if df.empty or metric not in df.columns:
        return empty_fig()
    daily = df.groupby("Date")[metric].mean().reset_index()
    fig = go.Figure()
    x0, x1 = daily["Date"].min(), daily["Date"].max()
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=0,    y1=0.8,
                   fillcolor=ACWR_ZONE_COLORS["Underload"], opacity=0.10,
                   line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=0.8,  y1=1.3,
                   fillcolor=ACWR_ZONE_COLORS["Optimal"], opacity=0.10,
                   line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=1.3,  y1=1.5,
                   fillcolor=ACWR_ZONE_COLORS["Caution"], opacity=0.12,
                   line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=x0, x1=x1, y0=1.5,  y1=3.0,
                   fillcolor=ACWR_ZONE_COLORS["High Spike"], opacity=0.12,
                   line=dict(width=0), layer="below")
    fig.add_trace(go.Scatter(
        x=daily["Date"], y=daily[metric], mode="lines+markers",
        line=dict(color=COLORS["text"], width=2.2),
        marker=dict(size=5, color=COLORS["accent"]),
        name="Squad mean ACWR",
    ))
    fig.add_hline(y=1.0, line_dash="dash",
                   line_color=COLORS["text_muted"], opacity=0.55)
    fig.update_yaxes(title=VARIABLE_LABELS.get(metric, metric), range=[0, max(2.0, daily[metric].max() * 1.05)])
    fig.update_xaxes(title="")
    return apply_layout(fig, height=height)


# -----------------------------------------------------------------------------
# Readiness donut
# -----------------------------------------------------------------------------
def readiness_donut(df: pd.DataFrame, height: int = 320) -> go.Figure:
    if df.empty:
        return empty_fig()
    counts = df["Readiness_Status"].value_counts().reindex(
        ["Green", "Yellow", "Red"]).fillna(0)
    fig = go.Figure(data=go.Pie(
        labels=counts.index, values=counts.values, hole=0.62,
        marker=dict(colors=[READINESS_COLORS[c] for c in counts.index],
                     line=dict(color=COLORS["panel"], width=2)),
        textinfo="label+percent", textfont=dict(size=12),
    ))
    fig.update_layout(annotations=[dict(
        text=f"<b>{int(counts.sum())}</b><br><span style='font-size:10px;color:#8B949E'>sessions</span>",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color=COLORS["text"]),
    )])
    return apply_layout(fig, height=height, showlegend=False)


# -----------------------------------------------------------------------------
# Player wellness heatmap (player × date for one metric)
# -----------------------------------------------------------------------------
def player_wellness_heatmap(df: pd.DataFrame, metric: str = "Fatigue_Score",
                                height: int = 460) -> go.Figure:
    if df.empty:
        return empty_fig()
    pivot = (df.pivot_table(index="Player", columns="Date",
                             values=metric, aggfunc="mean")
                .sort_index(key=lambda idx: [int(p.split("_")[-1]) for p in idx]))
    if pivot.empty:
        return empty_fig()

    # Reverse-scale wellness where "high = good" so red always means worse
    higher_is_worse = {"Fatigue_Score": True, "Soreness_Score": True,
                        "RPE": True, "Resting_HR": True}
    scale = "RdYlGn_r" if higher_is_worse.get(metric, False) else "RdYlGn"
    if metric in {"HRV_RMSSD", "CMJ_Height", "Sleep_Quality"}:
        scale = "RdYlGn"

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values, x=pivot.columns, y=pivot.index,
        colorscale=scale,
        colorbar=dict(thickness=10, title=VARIABLE_LABELS.get(metric, metric)),
        hovertemplate="%{y} · %{x|%b %d}<br>" + metric + ": %{z:.2f}<extra></extra>",
    ))
    fig.update_xaxes(title="")
    fig.update_yaxes(title="")
    return apply_layout(fig, height=height, showlegend=False)


# -----------------------------------------------------------------------------
# Radar — player or group(s) vs squad (multi-metric on 0-1 normalised scale)
# -----------------------------------------------------------------------------
def radar_compare(values_by_group: dict[str, list[float]],
                    metrics: list[str], height: int = 420,
                    title: str | None = None) -> go.Figure:
    """`values_by_group` is {label: [v1, v2, ...]} aligned with `metrics`."""
    if not values_by_group or not metrics:
        return empty_fig()

    labels = [VARIABLE_LABELS.get(m, m) for m in metrics]
    palette = [COLORS["accent"], COLORS["warning"], COLORS["success"],
                COLORS["pink"], COLORS["purple"], COLORS["accent_2"],
                COLORS["danger"]]

    fig = go.Figure()
    for i, (name, vals) in enumerate(values_by_group.items()):
        col = palette[i % len(palette)]
        fig.add_trace(go.Scatterpolar(
            r=list(vals) + [vals[0]],
            theta=labels + [labels[0]],
            fill="toself", name=name,
            line=dict(color=col, width=2),
            opacity=0.55,
        ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 1], showticklabels=True,
                              gridcolor=COLORS["border"],
                              tickfont=dict(size=9, color=COLORS["text_muted"])),
            angularaxis=dict(gridcolor=COLORS["border"],
                                tickfont=dict(size=10, color=COLORS["text"])),
            bgcolor=COLORS["panel"],
        ),
    )
    if title:
        fig.update_layout(title=dict(text=title, x=0.01, font=dict(size=14)))
    return apply_layout(fig, height=height)


def normalize_metric(series: pd.Series,
                       ref: pd.Series | None = None,
                       reverse: bool = False) -> float:
    """Min-max normalise `series.mean()` against `ref` (or itself), 0..1."""
    base = ref if ref is not None else series
    if base.empty or base.max() == base.min():
        return 0.5
    val = series.mean()
    norm = (val - base.min()) / (base.max() - base.min())
    norm = float(min(1.0, max(0.0, norm)))
    return 1.0 - norm if reverse else norm


# -----------------------------------------------------------------------------
# Multi-line trend with optional dual y-axis
# -----------------------------------------------------------------------------
def dual_axis_trend(df: pd.DataFrame, x: str,
                     y1: list[str], y2: list[str],
                     y1_title: str = "", y2_title: str = "",
                     color_map: dict | None = None,
                     height: int = 340) -> go.Figure:
    if df.empty:
        return empty_fig()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    palette = color_map or {}
    p_iter = iter([COLORS["accent"], COLORS["warning"], COLORS["success"],
                    COLORS["pink"], COLORS["purple"], COLORS["accent_2"]])
    for c in y1:
        if c not in df.columns:
            continue
        fig.add_trace(go.Scatter(x=df[x], y=df[c], mode="lines",
                                  name=VARIABLE_LABELS.get(c, c),
                                  line=dict(color=palette.get(c, next(p_iter)), width=2)),
                       secondary_y=False)
    for c in y2:
        if c not in df.columns:
            continue
        fig.add_trace(go.Scatter(x=df[x], y=df[c], mode="lines",
                                  name=VARIABLE_LABELS.get(c, c),
                                  line=dict(color=palette.get(c, next(p_iter)), width=2,
                                              dash="dot")),
                       secondary_y=True)
    fig.update_yaxes(title_text=y1_title, secondary_y=False)
    fig.update_yaxes(title_text=y2_title, secondary_y=True, showgrid=False)
    fig.update_xaxes(title="")
    return apply_layout(fig, height=height)


# -----------------------------------------------------------------------------
# DataTable styling preset
# -----------------------------------------------------------------------------
TABLE_STYLE = {
    "style_table": {"overflowX": "auto"},
    "style_cell":  {"backgroundColor": COLORS["panel"], "color": COLORS["text"],
                     "border": f"1px solid {COLORS['border']}",
                     "fontFamily": "Inter, sans-serif", "fontSize": "12px",
                     "padding": "8px 10px", "textAlign": "left"},
    "style_header": {"backgroundColor": COLORS["panel_light"],
                      "color": COLORS["text"], "fontWeight": "700",
                      "border": f"1px solid {COLORS['border']}",
                      "textTransform": "uppercase",
                      "fontSize": "11px", "letterSpacing": "1px"},
}

READINESS_TABLE_STYLE_CONDITIONAL = [
    {"if": {"filter_query": '{Readiness_Status} = "Red"'},
     "backgroundColor": "rgba(248, 113, 113, 0.15)"},
    {"if": {"filter_query": '{Readiness_Status} = "Yellow"'},
     "backgroundColor": "rgba(245, 158, 11, 0.10)"},
    {"if": {"filter_query": '{Readiness_Status} = "Green"'},
     "backgroundColor": "rgba(52, 211, 153, 0.10)"},
]
