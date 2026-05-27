"""
9) Comparison Lab — robust interactive version.

All filters are Inputs and update automatically. The Generate button remains as a
manual refresh affordance, but it is no longer required for filters to apply.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table

from src.config import (
    COLORS, POSITION_COLORS, VARIABLE_LABELS, EXTERNAL_LOAD_VARS,
    INTERNAL_LOAD_VARS, WELLNESS_VARS, NEURO_VARS, ALL_METRICS,
)
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card, apply_filters,
    date_range_picker, filter_field, empty_state, status_filter,
    injury_filter_options, safe_list, safe_metric, safe_metrics_list,
)
from src.visuals import apply_layout, empty_fig, radar_compare, heatmap_correlation, box_by_group, TABLE_STYLE
from src.insights import generate_combined_readiness_insight

DATA: pd.DataFrame = None

BASE_METRICS = list(dict.fromkeys(ALL_METRICS + [
    "ACWR_Calc", "Readiness_Score", "High_Intensity_Exposure",
    "Mechanical_Load_Proxy", "Wellness_Stress_Proxy", "Recovery_Risk_Composite",
]))
DEFAULT_COMPARISON_METRICS = ["Session_Load", "ACWR", "Fatigue_Score", "Soreness_Score", "Sleep_Quality", "HRV_RMSSD", "CMJ_Height", "Readiness_Score"]
GOOD_METRICS = {"Sleep_Quality", "HRV_RMSSD", "CMJ_Height"}

COMPARISON_MODES = [
    {"label": "👥 Player vs Player", "value": "player"},
    {"label": "🧭 Position vs Position", "value": "position"},
    {"label": "⚖️ Workload vs Wellness", "value": "workload_wellness"},
    {"label": "💓 CMJ vs HRV", "value": "cmj_hrv"},
    {"label": "🌐 Combined Readiness", "value": "combined"},
    {"label": "🚑 Injured vs Non-injured", "value": "injury_split"},
    {"label": "🛠️ Custom", "value": "custom"},
]
CHART_TYPES = [
    {"label": "Line", "value": "line"},
    {"label": "Bar", "value": "bar"},
    {"label": "Box", "value": "box"},
    {"label": "Scatter", "value": "scatter"},
    {"label": "Risk radar", "value": "radar"},
    {"label": "Heatmap", "value": "heatmap"},
]
AGG_OPTS = [
    {"label": "Daily", "value": "daily"},
    {"label": "Weekly", "value": "weekly"},
    {"label": "Mean window", "value": "mean"},
    {"label": "Latest value", "value": "latest"},
]

MODE_HINTS = {
    "player": "Compare selected players. Player, position, readiness, injury and date filters are applied together first.",
    "position": "Compare positional groups. If no position is selected, all positions in the current filtered data are used.",
    "workload_wellness": "Use Metric A as workload (e.g. Session_Load/HSR) and Metric B as wellness/recovery (e.g. Fatigue/HRV).",
    "cmj_hrv": "Focused CMJ-HRV readiness comparison. It still respects all selected filters.",
    "combined": "Multi-metric readiness/risk comparison across selected players or positions.",
    "injury_split": "Compare injury-labelled and non-injury sessions. With very few injuries, treat this as descriptive only.",
    "custom": "Free comparison mode using any selected metric and chart type.",
}


def _player_sort(players):
    return sorted(players, key=lambda x: int(str(x).split("_")[-1]))


def _metric_options():
    return [{"label": VARIABLE_LABELS.get(m, m), "value": m} for m in BASE_METRICS]


def layout():
    players = _player_sort(DATA["Player"].unique().tolist())
    positions = sorted(DATA["Position"].unique().tolist())
    return html.Div([
        page_header(
            "Comparison Lab",
            "Interactive comparison workspace. Change filters and the page updates automatically; the refresh button is optional.",
        ),
        html.Div(className="filters-bar", children=[
            html.Div(className="note-banner", children=[
                html.Strong("Filter note: "),
                "all filters are applied together. If a player does not belong to a selected position, the result will correctly show no data."
            ]),
            html.Div(className="grid-3", children=[
                filter_field("Comparison mode", dcc.Dropdown(id="cmp-mode", options=COMPARISON_MODES, value="player", clearable=False, className="dash-dropdown")),
                filter_field("Aggregation", dcc.Dropdown(id="cmp-agg", options=AGG_OPTS, value="mean", clearable=False, className="dash-dropdown")),
                filter_field("Chart type", dcc.Dropdown(id="cmp-chart", options=CHART_TYPES, value="bar", clearable=False, className="dash-dropdown")),
            ]),
            html.Div(style={"height": "10px"}),
            html.Div(className="grid-3", children=[
                filter_field("Players", dcc.Dropdown(id="cmp-players", options=[{"label": p, "value": p} for p in players], value=players[:2], multi=True, className="dash-dropdown")),
                filter_field("Positions", dcc.Dropdown(id="cmp-positions", options=[{"label": p, "value": p} for p in positions], value=[], multi=True, className="dash-dropdown", placeholder="All positions")),
                filter_field("Date range", date_range_picker(DATA, "cmp-dates")),
            ]),
            html.Div(style={"height": "10px"}),
            html.Div(className="grid-4", children=[
                filter_field("Readiness status", status_filter("cmp-readiness-status")),
                filter_field("Injury filter", injury_filter_options("cmp-injury-label")),
                filter_field("Metric A", dcc.Dropdown(id="cmp-metric-a", options=_metric_options(), value="Session_Load", clearable=False, className="dash-dropdown")),
                filter_field("Metric B", dcc.Dropdown(id="cmp-metric-b", options=_metric_options(), value="Fatigue_Score", clearable=False, className="dash-dropdown")),
            ]),
            html.Div(style={"height": "10px"}),
            html.Div(className="grid-2", children=[
                filter_field("Multi-metrics", dcc.Dropdown(id="cmp-metrics", options=_metric_options(), value=DEFAULT_COMPARISON_METRICS, multi=True, className="dash-dropdown")),
                filter_field("", html.Button("⚡ Refresh comparison", id="cmp-go", className="btn-primary", n_clicks=0, style={"marginTop": "20px"})),
            ]),
        ]),
        html.Div(id="cmp-mode-hint", className="note-banner", style={"marginTop": "8px"}),
        html.Div(id="cmp-kpis"),
        html.Div(id="cmp-primary-chart"),
        html.Div(className="grid-2", children=[html.Div(id="cmp-secondary-chart-1"), html.Div(id="cmp-secondary-chart-2")]),
        section_bar("Combined readiness comparison"),
        html.Div(id="cmp-combined-block"),
    ])


def register_callbacks(app):
    @app.callback(Output("cmp-mode-hint", "children"), Input("cmp-mode", "value"))
    def _mode_hint(mode):
        return MODE_HINTS.get(mode, "")

    @app.callback(
        Output("cmp-kpis", "children"),
        Output("cmp-primary-chart", "children"),
        Output("cmp-secondary-chart-1", "children"),
        Output("cmp-secondary-chart-2", "children"),
        Output("cmp-combined-block", "children"),
        Input("cmp-mode", "value"),
        Input("cmp-agg", "value"),
        Input("cmp-players", "value"),
        Input("cmp-positions", "value"),
        Input("cmp-dates", "start_date"),
        Input("cmp-dates", "end_date"),
        Input("cmp-metric-a", "value"),
        Input("cmp-metric-b", "value"),
        Input("cmp-metrics", "value"),
        Input("cmp-chart", "value"),
        Input("cmp-readiness-status", "value"),
        Input("cmp-injury-label", "value"),
        Input("cmp-go", "n_clicks"),
    )
    def _update(mode, agg, players, positions, start, end, metric_a, metric_b, metrics, chart, statuses, injury_filter, _n):
        allowed_metrics = [m for m in BASE_METRICS if m in DATA.columns]
        metric_a = safe_metric(metric_a, "Session_Load", allowed_metrics)
        metric_b = safe_metric(metric_b, "Fatigue_Score", allowed_metrics)
        metrics = safe_metrics_list(metrics, DEFAULT_COMPARISON_METRICS, allowed_metrics)
        mode = mode or "player"
        agg = agg or "mean"
        chart = chart or "bar"

        # Always apply global filters first.
        df = apply_filters(DATA, players=players, positions=positions, start_date=start, end_date=end,
                           statuses=statuses, injury_filter=injury_filter)
        if df.empty:
            empty = empty_state("No data for the selected filter combination. Please adjust players, positions, dates, readiness or injury filter.")
            return empty, empty, empty, empty, empty

        df, groupby, selected = _resolve_group(df, mode)
        if df.empty or not groupby or not selected:
            empty = empty_state("No valid comparison group remains after filters.")
            return empty, empty, empty, empty, empty

        # KPIs
        kpis = _kpi_strip(df, groupby, metric_a, metric_b)
        primary = _primary_chart(df, mode, agg, chart, groupby, metric_a, metric_b, metrics)
        table = _summary_table(df, groupby, metric_a, metric_b, metrics, agg)
        heatmap = _correlation_card(df, metrics)
        combined = _combined_readiness_block(df, groupby, selected)
        return kpis, primary, table, heatmap, combined


def _resolve_group(df: pd.DataFrame, mode: str):
    df = df.copy()
    if mode == "injury_split":
        df["Injured"] = df["Injury_Label"].map({1: "Injured", 0: "Non-injured"})
        return df, "Injured", [x for x in ["Injured", "Non-injured"] if x in df["Injured"].unique()]
    if mode == "position":
        return df, "Position", sorted(df["Position"].dropna().unique().tolist())
    # player-based default for player/combined/custom/cmj_hrv/workload_wellness
    return df, "Player", _player_sort(df["Player"].dropna().unique().tolist())


def _kpi_strip(df, groupby, metric_a, metric_b):
    inj = int(df["Injury_Label"].sum()) if "Injury_Label" in df.columns else 0
    red = int((df["Readiness_Status"] == "Red").sum()) if "Readiness_Status" in df.columns else 0
    cards = [
        kpi("Groups", df[groupby].nunique(), tone="info"),
        kpi("Rows", f"{len(df):,}", tone="info"),
        kpi("Injuries", inj, tone="bad" if inj else "ok"),
        kpi("Red sessions", red, tone="bad" if red else "ok"),
        kpi(f"Mean {VARIABLE_LABELS.get(metric_a, metric_a)}", f"{df[metric_a].mean():.2f}"),
        kpi(f"Mean {VARIABLE_LABELS.get(metric_b, metric_b)}", f"{df[metric_b].mean():.2f}"),
    ]
    return kpi_strip(cards)


def _time_aggregate(df, groupby, metric, agg):
    d = df.copy()
    if agg == "weekly":
        d["Period"] = d["Date"].dt.to_period("W").apply(lambda r: r.start_time)
        return d.groupby(["Period", groupby])[metric].mean().reset_index(), "Period"
    if agg == "daily":
        d["Period"] = d["Date"]
        return d.groupby(["Period", groupby])[metric].mean().reset_index(), "Period"
    if agg == "latest":
        idx = d.sort_values("Date").groupby(groupby)["Date"].idxmax()
        return d.loc[idx, [groupby, metric, "Date"]].rename(columns={"Date": "Period"}), "Period"
    # mean
    return d.groupby(groupby)[metric].mean().reset_index(), groupby


def _primary_chart(df, mode, agg, chart_type, groupby, metric_a, metric_b, metrics):
    title_metric = VARIABLE_LABELS.get(metric_a, metric_a)
    if chart_type == "line" and agg in {"mean", "latest"}:
        return chart_card("Line chart unavailable for this aggregation", "Line charts need Daily or Weekly aggregation. Switch chart type to Bar or aggregation to Daily/Weekly.", empty_fig("Choose Daily/Weekly for a trend."))
    if chart_type == "line":
        trend, period = _time_aggregate(df, groupby, metric_a, agg)
        fig = px.line(trend, x=period, y=metric_a, color=groupby, markers=True,
                      color_discrete_map=POSITION_COLORS if groupby == "Position" else {})
        fig.update_traces(line=dict(width=2), marker=dict(size=5))
        fig.update_xaxes(title=""); fig.update_yaxes(title=title_metric)
        fig = apply_layout(fig, height=400)
        return chart_card("Trend comparison", f"{title_metric} by {groupby.lower()} ({agg}).", dcc.Graph(figure=fig, config={"displaylogo": False}))
    if chart_type == "bar":
        data, _ = _time_aggregate(df, groupby, metric_a, agg)
        if agg in {"daily", "weekly"}:
            data = data.groupby(groupby)[metric_a].mean().reset_index()
        data = data.sort_values(metric_a, ascending=True)
        fig = px.bar(data, x=metric_a, y=groupby, orientation="h", color=groupby,
                     color_discrete_map=POSITION_COLORS if groupby == "Position" else {})
        fig.update_traces(marker_line_width=0); fig.update_xaxes(title=title_metric); fig.update_yaxes(title="")
        fig = apply_layout(fig, height=max(340, 28 * len(data)), showlegend=False)
        return chart_card("Bar comparison", f"{agg.title()} {title_metric} by {groupby.lower()}.", dcc.Graph(figure=fig, config={"displaylogo": False}))
    if chart_type == "box":
        fig = box_by_group(df, metric_a, groupby, color_map=POSITION_COLORS if groupby == "Position" else None, height=400)
        return chart_card("Distribution comparison", f"Spread of {title_metric} by {groupby.lower()}.", dcc.Graph(figure=fig, config={"displaylogo": False}))
    if chart_type == "scatter":
        fig = px.scatter(df, x=metric_a, y=metric_b, color=groupby, hover_data=["Player", "Position", "Date"],
                         color_discrete_map=POSITION_COLORS if groupby == "Position" else {})
        fig.update_traces(marker=dict(size=7, line=dict(width=0), opacity=0.72))
        fig.update_xaxes(title=title_metric); fig.update_yaxes(title=VARIABLE_LABELS.get(metric_b, metric_b))
        fig = apply_layout(fig, height=420)
        return chart_card("Metric relationship", f"{VARIABLE_LABELS.get(metric_a, metric_a)} vs {VARIABLE_LABELS.get(metric_b, metric_b)}.", dcc.Graph(figure=fig, config={"displaylogo": False}))
    if chart_type == "radar":
        return _risk_radar_card(df, groupby, metrics)
    if chart_type == "heatmap":
        return _risk_heatmap_card(df, groupby, metrics)
    return chart_card("Chart", "No compatible chart type selected.", empty_fig())


def _summary_table(df, groupby, metric_a, metric_b, metrics, agg):
    agg_dict = {"Rows": ("Date", "count"), "Injuries": ("Injury_Label", "sum"),
                "Red_Sessions": ("Readiness_Status", lambda s: int((s == "Red").sum())),
                f"Mean_{metric_a}": (metric_a, "mean"), f"Mean_{metric_b}": (metric_b, "mean"),
                "Latest_Date": ("Date", "max")}
    for m in metrics:
        if m in df.columns and m not in {metric_a, metric_b}:
            agg_dict[f"Mean_{m}"] = (m, "mean")
    tbl = df.groupby(groupby).agg(**agg_dict).reset_index().round(2)
    tbl["Latest_Date"] = pd.to_datetime(tbl["Latest_Date"]).dt.strftime("%Y-%m-%d")
    cols = [{"name": c.replace("_", " "), "id": c} for c in tbl.columns]
    return chart_card("Sortable comparison table", "Filtered group summary. Sort columns to identify the highest-risk or highest-load groups.",
                      dash_table.DataTable(data=tbl.to_dict("records"), columns=cols, sort_action="native", filter_action="native", page_size=12, **TABLE_STYLE))


def _correlation_card(df, metrics):
    valid = [m for m in metrics if m in df.columns]
    if len(valid) < 3:
        return chart_card("Correlation heatmap", "Select at least 3 valid multi-metrics.", empty_fig("Need 3+ metrics."))
    sub = df.dropna(subset=valid)
    if sub.empty:
        return chart_card("Correlation heatmap", "No complete rows for the selected metrics.", empty_fig("No complete rows."))
    fig = heatmap_correlation(sub, valid, height=420)
    return chart_card("Correlation heatmap", "Pearson correlation for selected metrics in the current filtered data.", dcc.Graph(figure=fig, config={"displaylogo": False}))


def _risk_values(df, groupby, metrics):
    means = df.groupby(groupby)[metrics].mean()
    values_by_group = {}
    for entity in means.index:
        vals = []
        for m in metrics:
            ref = df[m].dropna()
            if ref.empty or ref.max() == ref.min():
                vals.append(0.5); continue
            v = means.loc[entity, m]
            norm = (v - ref.min()) / (ref.max() - ref.min())
            norm = float(max(0, min(1, norm)))
            if m in GOOD_METRICS:
                norm = 1 - norm
            vals.append(norm)
        values_by_group[str(entity)] = vals
    return values_by_group, means


def _risk_radar_card(df, groupby, metrics):
    metrics = [m for m in metrics if m in df.columns]
    if not metrics:
        return chart_card("Combined Risk Radar", "No valid metrics selected.", empty_fig())
    values, _ = _risk_values(df, groupby, metrics)
    fig = radar_compare(values, metrics, height=440)
    return chart_card("Combined Risk Radar", "Further from the centre = higher monitoring concern, not better performance. Sleep, HRV and CMJ are inverted.", dcc.Graph(figure=fig, config={"displaylogo": False}))


def _risk_heatmap_card(df, groupby, metrics):
    metrics = [m for m in metrics if m in df.columns]
    if not metrics:
        return chart_card("Risk heatmap", "No valid metrics selected.", empty_fig())
    values, means = _risk_values(df, groupby, metrics)
    heat = pd.DataFrame(values, index=metrics).T
    fig = go.Figure(data=go.Heatmap(z=heat.values, x=[VARIABLE_LABELS.get(m, m) for m in metrics], y=heat.index,
                                    colorscale="RdYlGn_r", zmin=0, zmax=1,
                                    text=means.round(2).values, texttemplate="%{text}", textfont=dict(size=10),
                                    colorbar=dict(thickness=10, title="Risk")))
    fig.update_xaxes(tickangle=-30)
    fig = apply_layout(fig, height=420, showlegend=False)
    return chart_card("Risk heatmap", "Red = higher relative monitoring concern within the selected data.", dcc.Graph(figure=fig, config={"displaylogo": False}))


def _combined_readiness_block(df, groupby, selected):
    metrics = [m for m in DEFAULT_COMPARISON_METRICS if m in df.columns]
    if df.empty or not selected:
        return empty_state("No selection — choose players/positions above.")
    radar = _risk_radar_card(df, groupby, metrics)
    heat = _risk_heatmap_card(df, groupby, metrics)
    means = df.groupby(groupby)[metrics].mean().round(2).reset_index()
    tbl = chart_card("Combined-readiness summary table", "Group means for the core monitoring markers.",
                     dash_table.DataTable(data=means.to_dict("records"), columns=[{"name": c.replace("_", " "), "id": c} for c in means.columns], sort_action="native", **TABLE_STYLE))
    ins = generate_combined_readiness_insight(df, groupby, list(means[groupby].astype(str)))
    insight = html.Div(className=f"insight-box {ins.get('level','info')}", style={"marginTop": "16px"}, children=[
        html.Div(className="insight-headline", children=[html.Span("Combined-readiness insight", className="ins-tag"), html.Span(ins.get("headline", ""))]),
        html.Div(ins.get("detail", ""), className="insight-detail"),
        html.Div(ins.get("coaching", ""), className="insight-coaching"),
        html.Div(ins.get("caution", ""), className="insight-caution"),
    ])
    return html.Div([html.Div(className="grid-2", children=[radar, heat]), tbl, insight])
