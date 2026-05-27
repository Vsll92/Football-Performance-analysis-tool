"""
2) Workload Monitoring.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table

from src.config import (
    COLORS, POSITION_COLORS, VARIABLE_LABELS,
    EXTERNAL_LOAD_VARS, INTERNAL_LOAD_VARS,
)
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    apply_filters, player_dropdown, position_dropdown, date_range_picker,
    filter_field, empty_state, safe_metric,
)
from src.visuals import (
    apply_layout, empty_fig, bar_ranking, box_by_group, TABLE_STYLE,
)
from src.insights import generate_workload_insight


DATA: pd.DataFrame = None

LOAD_METRICS = EXTERNAL_LOAD_VARS + ["RPE", "Session_Load"]


def _filters():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-4", children=[
            filter_field("Players",   player_dropdown(DATA, "wl-players")),
            filter_field("Positions", position_dropdown(DATA, "wl-positions")),
            filter_field("Date range", date_range_picker(DATA, "wl-dates")),
            filter_field("Primary metric",
                dcc.Dropdown(id="wl-metric",
                    options=[{"label": VARIABLE_LABELS.get(m, m), "value": m}
                              for m in LOAD_METRICS],
                    value="Session_Load", clearable=False,
                    className="dash-dropdown")),
        ]),
        html.Div(style={"height": "10px"}),
        html.Div(className="grid-2", children=[
            filter_field("Aggregation",
                dcc.RadioItems(id="wl-agg",
                    options=[{"label": "Daily",  "value": "D"},
                              {"label": "Weekly", "value": "W"}],
                    value="D", className="radio-row",
                    inputStyle={"marginRight": "5px"})),
            filter_field("View",
                dcc.RadioItems(id="wl-view",
                    options=[{"label": "Squad mean", "value": "team"},
                              {"label": "Per player", "value": "player"}],
                    value="team", className="radio-row",
                    inputStyle={"marginRight": "5px"})),
        ]),
    ])


def layout():
    return html.Div([
        page_header(
            "Workload Monitoring",
            ("External and internal training load. Identify who is loading "
              "hardest, who is spiking, and where high-speed exposure "
              "concentrates."),
        ),
        _filters(),
        html.Div(id="wl-kpis"),
        html.Div(id="wl-insight"),

        section_bar("Trend & ranking"),
        html.Div(className="grid-2", children=[
            html.Div(id="wl-trend-card"),
            html.Div(id="wl-rank-card"),
        ]),

        section_bar("By position & exposure mix"),
        html.Div(className="grid-2", children=[
            html.Div(id="wl-position-card"),
            html.Div(id="wl-exposure-card"),
        ]),

        section_bar("Workload concerns"),
        html.Div(id="wl-concern-card"),
    ])


def register_callbacks(app):

    @app.callback(
        Output("wl-kpis", "children"),
        Output("wl-insight", "children"),
        Output("wl-trend-card", "children"),
        Output("wl-rank-card", "children"),
        Output("wl-position-card", "children"),
        Output("wl-exposure-card", "children"),
        Output("wl-concern-card", "children"),
        Input("wl-players", "value"),
        Input("wl-positions", "value"),
        Input("wl-dates", "start_date"),
        Input("wl-dates", "end_date"),
        Input("wl-metric", "value"),
        Input("wl-agg", "value"),
        Input("wl-view", "value"),
    )
    def _update(players, positions, start_date, end_date, metric, agg, view):
        metric = safe_metric(metric, "Session_Load", LOAD_METRICS)
        agg = agg or "D"
        view = view or "team"
        df = apply_filters(DATA, players, positions, start_date, end_date)

        # KPIs
        if df.empty:
            kpis = empty_state()
        else:
            spikes = int(df["Flag_ACWR_Spike"].sum())
            kpis = kpi_strip([
                kpi("Total dist",   f"{df['Total_Distance'].sum() / 1000:.1f} km"),
                kpi("Mean HSR",     f"{df['HSR'].mean():.0f} m", tone="info"),
                kpi("Mean Sprint",  f"{df['Sprint_Distance'].mean():.0f} m"),
                kpi("Mean Acc.",    f"{df['Accelerations'].mean():.1f}"),
                kpi("Mean Dec.",    f"{df['Decelerations'].mean():.1f}"),
                kpi("Mean RPE",     f"{df['RPE'].mean():.1f}/10"),
                kpi("Mean Load",    f"{df['Session_Load'].mean():.0f} AU"),
                kpi("ACWR spikes",  spikes,
                     tone="bad" if spikes > 5 else "warn" if spikes > 0 else "ok"),
            ])

        # Insight
        if df.empty:
            insight = None
        else:
            ins = generate_workload_insight(df)
            insight = html.Div(className=f"insight-box {ins['level']}",
                                style={"marginBottom": "16px"}, children=[
                html.Div(className="insight-headline", children=[
                    html.Span("Workload insight", className="ins-tag"),
                    html.Span(ins["headline"]),
                ]),
                html.Div(ins["detail"], className="insight-detail"),
                html.Div(ins["coaching"], className="insight-coaching"),
                html.Div(ins["caution"], className="insight-caution"),
            ])

        # Trend chart
        if df.empty:
            trend_card = empty_state()
        else:
            df2 = df.copy()
            if agg == "W":
                df2["Period"] = df2["Date"].dt.to_period("W").apply(lambda r: r.start_time)
            else:
                df2["Period"] = df2["Date"]

            if view == "team":
                trend = df2.groupby("Period")[metric].mean().reset_index()
                f = go.Figure()
                f.add_trace(go.Scatter(x=trend["Period"], y=trend[metric],
                                          mode="lines", fill="tozeroy",
                                          line=dict(color=COLORS["accent"], width=2),
                                          fillcolor="rgba(79,140,255,0.18)"))
                f.update_xaxes(title=""); f.update_yaxes(title=VARIABLE_LABELS.get(metric, metric))
                f = apply_layout(f, height=320, showlegend=False)
                t_title = f"Squad {VARIABLE_LABELS.get(metric, metric)}"
                t_sub = f"{'Weekly' if agg == 'W' else 'Daily'} squad mean."
            else:
                trend = df2.groupby(["Period", "Player"])[metric].mean().reset_index()
                f = px.line(trend, x="Period", y=metric, color="Player")
                f.update_xaxes(title=""); f.update_yaxes(title=VARIABLE_LABELS.get(metric, metric))
                f.update_traces(line=dict(width=1.5))
                f = apply_layout(f, height=320)
                t_title = f"Per-player {VARIABLE_LABELS.get(metric, metric)}"
                t_sub = f"{'Weekly' if agg == 'W' else 'Daily'} value by player."
            trend_card = chart_card(t_title, t_sub,
                                      dcc.Graph(figure=f, config={"displaylogo": False}),
                                      tag=f"{'Weekly' if agg == 'W' else 'Daily'}")

        # Ranking
        if df.empty:
            rank_card = empty_state()
        else:
            r = (df.groupby(["Player", "Position"])[metric].mean()
                    .reset_index()
                    .sort_values(metric, ascending=True))
            f = px.bar(r.tail(15), x=metric, y="Player",
                        orientation="h", color="Position",
                        color_discrete_map=POSITION_COLORS)
            f.update_traces(marker_line_width=0)
            f.update_xaxes(title=VARIABLE_LABELS.get(metric, metric))
            f.update_yaxes(title="")
            f = apply_layout(f, height=max(380, 24 * 15))
            rank_card = chart_card(
                f"Top 15 — mean {VARIABLE_LABELS.get(metric, metric)}",
                "Per-player ranking, coloured by position.",
                dcc.Graph(figure=f, config={"displaylogo": False}),
            )

        # By position
        if df.empty:
            pos_card = empty_state()
        else:
            f = box_by_group(df, metric, "Position",
                              color_map=POSITION_COLORS, height=360)
            pos_card = chart_card(
                "Distribution by position",
                "Spread, median, and outliers per positional group.",
                dcc.Graph(figure=f, config={"displaylogo": False}),
            )

        # Exposure (HSR vs Sprint, Acc vs Dec)
        if df.empty:
            exp_card = empty_state()
        else:
            f = make_exposure_fig(df)
            exp_card = chart_card(
                "High-intensity exposure mix",
                "Mean HSR vs Sprint distance and accelerations vs decelerations per player.",
                dcc.Graph(figure=f, config={"displaylogo": False}),
            )

        # Concerns table
        if df.empty:
            concern_card = empty_state()
        else:
            recent = df[df["Date"] >= df["Date"].max() - pd.Timedelta(days=7)]
            tbl = (recent.groupby("Player")
                    .agg(Position=("Position", "first"),
                          Session_Load=("Session_Load", "mean"),
                          ACWR=("ACWR", "mean"),
                          Spike_Days=("Flag_ACWR_Spike", "sum"),
                          Fatigue=("Fatigue_Score", "mean"),
                          Status=("Readiness_Status", "last"))
                    .reset_index()
                    .round(2))
            tbl["Spike_Days"] = tbl["Spike_Days"].astype(int)
            tbl["Action"] = tbl.apply(_recommended_action, axis=1)
            tbl = tbl.sort_values(["Spike_Days", "ACWR"],
                                    ascending=[False, False]).head(12)

            cols = [
                {"name": "Player",       "id": "Player"},
                {"name": "Pos",          "id": "Position"},
                {"name": "Mean Load",    "id": "Session_Load"},
                {"name": "Mean ACWR",    "id": "ACWR"},
                {"name": "Spike days",   "id": "Spike_Days"},
                {"name": "Mean Fat.",    "id": "Fatigue"},
                {"name": "Status",       "id": "Status"},
                {"name": "Suggested action", "id": "Action"},
            ]
            concern_card = chart_card(
                "Workload concern table (last 7 days of selection)",
                "Per-player snapshot with a suggested coaching action.",
                dash_table.DataTable(
                    data=tbl.to_dict("records"), columns=cols,
                    sort_action="native", filter_action="native",
                    style_data_conditional=[
                        {"if": {"filter_query": '{Status} = "Red"'},
                          "backgroundColor": "rgba(248,113,113,0.10)"},
                        {"if": {"filter_query": '{Status} = "Yellow"'},
                          "backgroundColor": "rgba(245,158,11,0.08)"},
                    ],
                    **TABLE_STYLE,
                ),
            )

        return (kpis, insight, trend_card, rank_card, pos_card, exp_card, concern_card)


def _recommended_action(row):
    if row["Status"] == "Red":
        return "Recovery-focused session; reduce HSR 24–48h"
    if row["Spike_Days"] > 0 and row["ACWR"] > 1.4:
        return "Cap high-speed work; monitor next session"
    if row["Fatigue"] >= 4:
        return "Modify intensity; recheck wellness"
    if row["Status"] == "Yellow":
        return "Manage intensity; full volume OK"
    return "Cleared for normal training"


def make_exposure_fig(df: pd.DataFrame):
    from plotly.subplots import make_subplots
    means = (df.groupby(["Player", "Position"])
                .agg(HSR=("HSR", "mean"),
                      Sprint=("Sprint_Distance", "mean"),
                      Acc=("Accelerations", "mean"),
                      Dec=("Decelerations", "mean"))
                .reset_index())
    fig = make_subplots(rows=1, cols=2, subplot_titles=(
        "HSR vs Sprint Distance (mean)",
        "Accelerations vs Decelerations (mean)"))
    for pos in means["Position"].unique():
        sub = means[means["Position"] == pos]
        fig.add_trace(go.Scatter(
            x=sub["HSR"], y=sub["Sprint"], mode="markers",
            name=pos, legendgroup=pos,
            marker=dict(size=10, color=POSITION_COLORS.get(pos, COLORS["accent"]),
                          line=dict(width=0)),
            text=sub["Player"], hovertemplate="%{text}<br>HSR %{x:.0f}<br>Sprint %{y:.0f}<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=sub["Acc"], y=sub["Dec"], mode="markers",
            name=pos, legendgroup=pos, showlegend=False,
            marker=dict(size=10, color=POSITION_COLORS.get(pos, COLORS["accent"]),
                          line=dict(width=0)),
            text=sub["Player"], hovertemplate="%{text}<br>Acc %{x:.1f}<br>Dec %{y:.1f}<extra></extra>",
        ), row=1, col=2)
    fig.update_xaxes(title_text="HSR (m)", row=1, col=1)
    fig.update_yaxes(title_text="Sprint Distance (m)", row=1, col=1)
    fig.update_xaxes(title_text="Accelerations", row=1, col=2)
    fig.update_yaxes(title_text="Decelerations", row=1, col=2)
    return apply_layout(fig, height=360)
