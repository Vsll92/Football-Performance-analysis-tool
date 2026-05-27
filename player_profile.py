"""
7) Player Profile page.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table

from src.config import COLORS, POSITION_COLORS, READINESS_COLORS, VARIABLE_LABELS
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    apply_filters, date_range_picker,
    filter_field, empty_state, traffic_badge,
)
from src.visuals import (
    apply_layout, empty_fig, acwr_zoned_line, TABLE_STYLE,
)
from src.insights import generate_player_insight
from src.readiness import explain_readiness


DATA: pd.DataFrame = None


def _filters():
    players = sorted(DATA["Player"].unique(),
                       key=lambda x: int(x.split("_")[-1]))
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-3", children=[
            filter_field("Player",
                dcc.Dropdown(
                    id="pp-player",
                    options=[{"label": p, "value": p} for p in players],
                    value=players[0], clearable=False,
                    className="dash-dropdown")),
            filter_field("Date range", date_range_picker(DATA, "pp-dates")),
            filter_field("Recent table/recommendation window",
                dcc.Dropdown(
                    id="pp-window",
                    options=[{"label": f"{n} days", "value": n}
                              for n in [7, 14, 21, 28]],
                    value=14, clearable=False,
                    className="dash-dropdown")),
        ]),
    ])


def layout():
    return html.Div([
        page_header("Player Profile",
                      ("Per-player monitoring report: current status, "
                        "load and recovery trends, baseline comparisons, "
                        "and an automated recommendation.")),
        _filters(),
        html.Div(id="pp-status-card"),
        html.Div(id="pp-kpis"),

        section_bar("Trends"),
        html.Div(className="grid-2", children=[
            html.Div(id="pp-load-card"),
            html.Div(id="pp-acwr-card"),
        ]),
        html.Div(className="grid-2", children=[
            html.Div(id="pp-wellness-card"),
            html.Div(id="pp-neuro-card"),
        ]),

        section_bar("Recent log table"),
        html.Div(id="pp-table-card"),

        html.Div(id="pp-recommendation-card"),
    ])


def register_callbacks(app):

    @app.callback(
        Output("pp-status-card", "children"),
        Output("pp-kpis", "children"),
        Output("pp-load-card", "children"),
        Output("pp-acwr-card", "children"),
        Output("pp-wellness-card", "children"),
        Output("pp-neuro-card", "children"),
        Output("pp-table-card", "children"),
        Output("pp-recommendation-card", "children"),
        Input("pp-player", "value"),
        Input("pp-dates", "start_date"),
        Input("pp-dates", "end_date"),
        Input("pp-window", "value"),
    )
    def _update(player, start_date, end_date, window):
        window = int(window or 14)
        df = apply_filters(DATA, players=[player],
                            start_date=start_date, end_date=end_date)

        if df.empty:
            return (empty_state(f"No data for {player}"),
                    empty_state(), empty_state(), empty_state(),
                    empty_state(), empty_state(), empty_state(), empty_state())

        df = df.sort_values("Date")
        last = df.iloc[-1]
        reasons = explain_readiness(last)

        # Status card
        status_card = html.Div(className="status-card", children=[
            html.Div(className="status-row", children=[
                html.Div([
                    html.H3(player, className="status-player"),
                    html.Div(f"{last['Position']} · {last['Date'].strftime('%a %b %d, %Y')}",
                              className="muted",
                              style={"marginTop": "2px"}),
                ]),
                html.Div(className="status-meta", children=[
                    html.Span(f"Score {last['Readiness_Score']}",
                                className="status-score-pill"),
                    traffic_badge(last["Readiness_Status"]),
                ]),
            ]),
            html.Div(className="status-reasons", children=[
                html.Div("Reasons triggering the current status",
                          className="muted",
                          style={"fontSize": "11px", "textTransform": "uppercase",
                                  "letterSpacing": "1px", "fontWeight": 700}),
                html.Ul([html.Li(r) for r in reasons]),
            ]),
        ])

        # KPIs (latest values)
        kpis = kpi_strip([
            kpi("Latest Load", f"{last['Session_Load']:.0f} AU"),
            kpi("Latest ACWR", f"{last['ACWR']:.2f}",
                 tone="bad" if last["ACWR"] > 1.5 else
                       "warn" if last["ACWR"] > 1.3 else "ok"),
            kpi("Latest Fatigue", f"{last['Fatigue_Score']:.1f}/5",
                 tone="warn" if last["Fatigue_Score"] >= 4 else "info"),
            kpi("Latest Sleep", f"{last['Sleep_Quality']:.1f}/5",
                 tone="warn" if last["Sleep_Quality"] <= 2.5 else "info"),
            kpi("Latest CMJ", f"{last['CMJ_Height']:.1f} cm",
                 sub=f"{last.get('CMJ_Height_PctChange', 0):+.1f}% vs baseline"),
            kpi("Latest HRV", f"{last['HRV_RMSSD']:.1f} ms",
                 sub=f"{last.get('HRV_RMSSD_PctChange', 0):+.1f}% vs baseline"),
            kpi("Latest RHR", f"{last['Resting_HR']:.1f} bpm",
                 sub=f"{last.get('Resting_HR_PctChange', 0):+.1f}% vs baseline"),
        ])

        # Workload card
        f_load = go.Figure()
        f_load.add_trace(go.Scatter(x=df["Date"], y=df["Session_Load"],
                                       mode="lines+markers",
                                       line=dict(color=COLORS["accent"], width=2),
                                       marker=dict(size=5),
                                       name="Session Load"))
        if (df["Injury_Label"] == 1).any():
            inj_dates = df[df["Injury_Label"] == 1]
            f_load.add_trace(go.Scatter(
                x=inj_dates["Date"], y=inj_dates["Session_Load"],
                mode="markers",
                marker=dict(symbol="x", size=14, color=COLORS["danger"],
                              line=dict(width=1, color="#fff")),
                name="Injury day",
            ))
        f_load.update_xaxes(title=""); f_load.update_yaxes(title="Session Load (AU)")
        f_load = apply_layout(f_load, height=300)
        load_card = chart_card("Training load",
                                  f"All sessions for {player} in the window.",
                                  dcc.Graph(figure=f_load, config={"displaylogo": False}))

        # ACWR card
        acwr_card = chart_card(
            "ACWR with zones",
            "Player-specific ACWR overlaid on the monitoring zones.",
            dcc.Graph(figure=acwr_zoned_line(df, height=300),
                        config={"displaylogo": False}),
        )

        # Wellness card
        f_w = go.Figure()
        f_w.add_trace(go.Scatter(x=df["Date"], y=df["Fatigue_Score"],
                                    mode="lines", name="Fatigue",
                                    line=dict(color=COLORS["warning"], width=2)))
        f_w.add_trace(go.Scatter(x=df["Date"], y=df["Soreness_Score"],
                                    mode="lines", name="Soreness",
                                    line=dict(color=COLORS["danger"], width=2,
                                                dash="dot")))
        f_w.add_trace(go.Scatter(x=df["Date"], y=df["Sleep_Quality"],
                                    mode="lines", name="Sleep",
                                    line=dict(color=COLORS["success"], width=2)))
        f_w.update_xaxes(title=""); f_w.update_yaxes(title="Score (1–5)")
        f_w = apply_layout(f_w, height=300)
        wellness_card = chart_card("Wellness markers",
                                      "Fatigue, soreness, and sleep on the same axis.",
                                      dcc.Graph(figure=f_w,
                                                  config={"displaylogo": False}))

        # Neuro card (CMJ + HRV + RHR with baselines)
        cmj_base = df["CMJ_Height_Baseline"].iloc[0]
        hrv_base = df["HRV_RMSSD_Baseline"].iloc[0]
        rhr_base = df["Resting_HR_Baseline"].iloc[0]
        f_n = go.Figure()
        f_n.add_trace(go.Scatter(x=df["Date"], y=df["CMJ_Height"],
                                    mode="lines", name="CMJ (cm)",
                                    line=dict(color=COLORS["accent"], width=2)))
        f_n.add_hline(y=cmj_base, line_dash="dot",
                        line_color=COLORS["accent"], opacity=0.5,
                        annotation_text=f"CMJ base {cmj_base:.1f}",
                        annotation_position="left")
        f_n.add_trace(go.Scatter(x=df["Date"], y=df["HRV_RMSSD"],
                                    mode="lines", name="HRV (ms)",
                                    line=dict(color=COLORS["purple"], width=2),
                                    yaxis="y2"))
        f_n.add_trace(go.Scatter(x=df["Date"], y=df["Resting_HR"],
                                    mode="lines", name="RHR (bpm)",
                                    line=dict(color=COLORS["warning"], width=2,
                                                dash="dot"),
                                    yaxis="y2"))
        f_n.update_layout(yaxis=dict(title="CMJ (cm)"),
                            yaxis2=dict(title="HRV / RHR",
                                          overlaying="y", side="right",
                                          showgrid=False))
        f_n.update_xaxes(title="")
        f_n = apply_layout(f_n, height=300)
        neuro_card = chart_card(
            "Neuromuscular & autonomic markers",
            f"CMJ on left axis (baseline {cmj_base:.1f} cm). HRV / RHR on right axis.",
            dcc.Graph(figure=f_n, config={"displaylogo": False}),
        )

        # Recent log table
        recent = df.tail(window).copy().sort_values("Date", ascending=False)
        recent["Date"] = recent["Date"].dt.strftime("%Y-%m-%d")
        cols_to_show = ["Date", "Session_Load", "ACWR", "Fatigue_Score",
                          "Soreness_Score", "Sleep_Quality", "HRV_RMSSD",
                          "CMJ_Height", "Readiness_Score", "Readiness_Status"]
        recent = recent[[c for c in cols_to_show if c in recent.columns]].round(2)
        cols = [{"name": c.replace("_", " "), "id": c} for c in recent.columns]
        table_card = chart_card(
            f"Last {window} sessions",
            "Most recent player log with status colouring.",
            dash_table.DataTable(
                data=recent.to_dict("records"), columns=cols,
                sort_action="native",
                style_data_conditional=[
                    {"if": {"filter_query": '{Readiness_Status} = "Red"'},
                      "backgroundColor": "rgba(248,113,113,0.12)"},
                    {"if": {"filter_query": '{Readiness_Status} = "Yellow"'},
                      "backgroundColor": "rgba(245,158,11,0.10)"},
                ],
                page_size=window,
                **TABLE_STYLE,
            ),
        )

        # Recommendation
        rec = generate_player_insight(df, player, window=min(window, 7))
        recommendation = html.Div(className="card-pf", children=[
            html.Div(className="card-head", children=[
                html.H4("Recommendation", className="card-title"),
                html.Span("Auto-generated", className="card-tag"),
            ]),
            html.Div(className=f"insight-box {rec['level']}", children=[
                html.Div(className="insight-headline", children=[
                    html.Span("Player-level insight", className="ins-tag"),
                    html.Span(rec["headline"]),
                ]),
                html.Div(rec["detail"], className="insight-detail"),
                html.Div(rec["coaching"], className="insight-coaching"),
                html.Div(rec["caution"], className="insight-caution"),
            ]),
        ])

        return (status_card, kpis, load_card, acwr_card,
                wellness_card, neuro_card, table_card, recommendation)
