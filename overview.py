"""
1) Executive Overview — head-coach landing page.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table

from src.config import COLORS, READINESS_COLORS, VARIABLE_LABELS
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    apply_filters, position_dropdown, status_filter, date_range_picker,
    filter_field, empty_state, traffic_badge,
)
from src.visuals import (
    apply_layout, empty_fig, readiness_donut,
    TABLE_STYLE,
)
from src.insights import (
    generate_overview_insight, generate_coach_recommendation,
)


DATA: pd.DataFrame = None


def _filters():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-3", children=[
            filter_field("Positions",  position_dropdown(DATA, "ov-positions")),
            filter_field("Readiness",  status_filter("ov-status")),
            filter_field("Date range", date_range_picker(DATA, "ov-dates")),
        ]),
    ])


def layout():
    dr_start = DATA["Date"].min().strftime("%b %d")
    dr_end   = DATA["Date"].max().strftime("%b %d")
    return html.Div([
        page_header(
            "Executive Overview",
            ("A one-screen briefing for the head coach. Squad-level KPIs, "
             "readiness mix, team trends, injury timeline, and the players "
             "you need to manage today."),
            stats=[
                ("Players",  DATA["Player"].nunique()),
                ("Sessions", f"{len(DATA):,}"),
                ("Window",   f"{dr_start} – {dr_end}"),
                ("Injuries", int(DATA["Injury_Label"].sum())),
            ],
        ),
        _filters(),
        html.Div(id="ov-kpis"),
        html.Div(id="ov-coach-summary"),

        section_bar("Squad trends"),
        html.Div(className="grid-2", children=[
            html.Div(id="ov-trend-load-card"),
            html.Div(id="ov-trend-fatigue-card"),
        ]),

        section_bar("Readiness & watchlist"),
        html.Div(className="grid-2", children=[
            html.Div(id="ov-readiness-card"),
            html.Div(id="ov-watchlist-card"),
        ]),

        section_bar("Injury timeline"),
        html.Div(id="ov-injury-card"),
    ])


def register_callbacks(app):

    @app.callback(
        Output("ov-kpis", "children"),
        Output("ov-coach-summary", "children"),
        Output("ov-trend-load-card", "children"),
        Output("ov-trend-fatigue-card", "children"),
        Output("ov-readiness-card", "children"),
        Output("ov-watchlist-card", "children"),
        Output("ov-injury-card", "children"),
        Input("ov-positions", "value"),
        Input("ov-status",    "value"),
        Input("ov-dates",     "start_date"),
        Input("ov-dates",     "end_date"),
    )
    def _update(positions, statuses, start_date, end_date):
        df = apply_filters(DATA, positions=positions, statuses=statuses,
                            start_date=start_date, end_date=end_date)

        # KPIs
        if df.empty:
            kpis = empty_state()
        else:
            n_red    = int((df["Readiness_Status"] == "Red").sum())
            n_yellow = int((df["Readiness_Status"] == "Yellow").sum())
            n_green  = int((df["Readiness_Status"] == "Green").sum())
            spikes   = int(df["Flag_ACWR_Spike"].sum())
            inj      = int(df["Injury_Label"].sum())
            inj_rate = inj / max(len(df), 1) * 100

            kpis = kpi_strip([
                kpi("Players",          df["Player"].nunique(), tone="info"),
                kpi("Sessions",         f"{len(df):,}",         tone="info"),
                kpi("Avg Total Dist.",  f"{df['Total_Distance'].mean():.0f} m"),
                kpi("Avg HSR",          f"{df['HSR'].mean():.0f} m", tone="info"),
                kpi("Avg ACWR",         f"{df['ACWR'].mean():.2f}", tone="info"),
                kpi("Avg Fatigue",      f"{df['Fatigue_Score'].mean():.2f}/5",
                     tone="warn" if df['Fatigue_Score'].mean() > 3.5 else "info"),
                kpi("Avg CMJ",          f"{df['CMJ_Height'].mean():.1f} cm"),
                kpi("Avg HRV",          f"{df['HRV_RMSSD'].mean():.1f} ms"),
                kpi("🟢 Green",         n_green, tone="ok"),
                kpi("🟡 Yellow",        n_yellow, tone="warn"),
                kpi("🔴 Red",           n_red,
                     tone="bad" if n_red > 0 else "info"),
                kpi("ACWR Spikes",      spikes,
                     tone="bad" if spikes > 5 else "warn" if spikes > 0 else "ok"),
                kpi("Injuries",         inj, sub=f"{inj_rate:.2f}% of sessions",
                     tone="bad" if inj > 0 else "ok"),
            ])

        # Coach summary
        if df.empty:
            coach_summary = empty_state()
        else:
            rec = generate_coach_recommendation(df)
            ov  = generate_overview_insight(df)
            coach_summary = html.Div(className="card-pf", children=[
                html.Div(className="card-head", children=[
                    html.Div([
                        html.H4("Today's squad summary", className="card-title"),
                        html.Div(
                            "What the head coach needs to know right now.",
                            className="card-subtitle"),
                    ]),
                    html.Span("Auto-generated", className="card-tag"),
                ]),
                html.Div(className=f"insight-box {rec['level']}", children=[
                    html.Div(className="insight-headline", children=[
                        html.Span("Headline", className="ins-tag"),
                        html.Span(rec["headline"]),
                    ]),
                    html.Div(rec["detail"],   className="insight-detail"),
                    html.Div(rec["coaching"], className="insight-coaching"),
                    html.Div(rec["caution"],  className="insight-caution"),
                ]),
                html.Div(className=f"insight-box {ov['level']}", children=[
                    html.Div(className="insight-headline", children=[
                        html.Span("Period insight", className="ins-tag"),
                        html.Span(ov["headline"]),
                    ]),
                    html.Div(ov["detail"],   className="insight-detail"),
                    html.Div(ov["coaching"], className="insight-coaching"),
                    html.Div(ov["caution"],  className="insight-caution"),
                ]),
            ])

        # Trend cards
        if df.empty:
            trend_load = trend_fatigue = empty_state()
        else:
            daily_load = (df.groupby("Date")["Session_Load"].mean().reset_index())
            f_load = go.Figure()
            f_load.add_trace(go.Scatter(
                x=daily_load["Date"], y=daily_load["Session_Load"],
                fill="tozeroy", mode="lines",
                line=dict(color=COLORS["accent"], width=2),
                fillcolor="rgba(79,140,255,0.18)",
                name="Squad mean Session Load",
            ))
            f_load.update_xaxes(title="")
            f_load.update_yaxes(title="Session Load (AU)")
            f_load = apply_layout(f_load, height=300, showlegend=False)
            trend_load = chart_card(
                "Squad daily training load",
                "Mean Session Load across all players, per training day.",
                dcc.Graph(figure=f_load, config={"displaylogo": False}),
            )

            daily_fat = (df.groupby("Date")
                            .agg(Fatigue=("Fatigue_Score", "mean"),
                                  HRV=("HRV_RMSSD", "mean"))
                            .reset_index())
            hrv_norm = (daily_fat["HRV"] / daily_fat["HRV"].max() * 5
                          if daily_fat["HRV"].max() > 0 else daily_fat["HRV"])
            f_fat = go.Figure()
            f_fat.add_trace(go.Scatter(
                x=daily_fat["Date"], y=daily_fat["Fatigue"],
                mode="lines", name="Fatigue (1–5)",
                line=dict(color=COLORS["warning"], width=2),
            ))
            f_fat.add_trace(go.Scatter(
                x=daily_fat["Date"], y=hrv_norm,
                mode="lines", name="HRV (norm. to fatigue scale)",
                line=dict(color=COLORS["purple"], width=2, dash="dot"),
            ))
            f_fat.update_xaxes(title="")
            f_fat.update_yaxes(title="Fatigue / HRV (norm.)")
            f_fat = apply_layout(f_fat, height=300)
            trend_fatigue = chart_card(
                "Fatigue vs HRV",
                "Squad mean fatigue (1–5) alongside HRV normalised to the same scale.",
                dcc.Graph(figure=f_fat, config={"displaylogo": False}),
            )

        # Readiness donut
        if df.empty:
            readiness_card = empty_state()
        else:
            f_r = readiness_donut(df, height=300)
            readiness_card = chart_card(
                "Readiness mix",
                "Share of sessions classified Green / Yellow / Red.",
                dcc.Graph(figure=f_r, config={"displaylogo": False}),
            )

        # Watchlist
        if df.empty:
            watchlist_card = empty_state()
        else:
            last7 = df[df["Date"] >= df["Date"].max() - pd.Timedelta(days=7)]
            watch = (last7.groupby("Player")
                      .agg(Position=("Position", "first"),
                            Mean_Readiness=("Readiness_Score", "mean"),
                            Max_ACWR=("ACWR", "max"),
                            Mean_Fatigue=("Fatigue_Score", "mean"),
                            Last_Status=("Readiness_Status", "last"))
                      .reset_index()
                      .sort_values("Mean_Readiness", ascending=False)
                      .head(5)
                      .round(2))
            cols = [
                {"name": "Player",          "id": "Player"},
                {"name": "Pos",             "id": "Position"},
                {"name": "Mean Score (7d)", "id": "Mean_Readiness"},
                {"name": "Max ACWR",        "id": "Max_ACWR"},
                {"name": "Mean Fatigue",    "id": "Mean_Fatigue"},
                {"name": "Last Status",     "id": "Last_Status"},
            ]
            watchlist_card = chart_card(
                "Top 5 players to manage",
                "Highest mean Readiness Score over the last 7 days of the selection.",
                dash_table.DataTable(
                    data=watch.to_dict("records"), columns=cols,
                    sort_action="native",
                    style_data_conditional=[
                        {"if": {"filter_query": '{Last_Status} = "Red"',
                                "column_id": "Last_Status"},
                         "color": COLORS["danger"], "fontWeight": "700"},
                        {"if": {"filter_query": '{Last_Status} = "Yellow"',
                                "column_id": "Last_Status"},
                         "color": COLORS["warning"], "fontWeight": "700"},
                        {"if": {"filter_query": '{Last_Status} = "Green"',
                                "column_id": "Last_Status"},
                         "color": COLORS["success"], "fontWeight": "700"},
                    ],
                    **TABLE_STYLE,
                ),
            )

        # Injury timeline
        if df.empty or df["Injury_Label"].sum() == 0:
            f_inj = empty_fig("No injuries recorded in the current window.")
            inj_subtitle = "No injuries recorded in the current window."
        else:
            inj_df = df[df["Injury_Label"] == 1]
            f_inj = go.Figure()
            f_inj.add_trace(go.Scatter(
                x=inj_df["Date"], y=inj_df["Player"],
                mode="markers",
                marker=dict(symbol="x", size=14, color=COLORS["danger"],
                              line=dict(width=1, color="#fff")),
                name="Injury",
                hovertemplate="%{y} · %{x|%b %d}<extra></extra>",
            ))
            f_inj.update_xaxes(title="")
            f_inj.update_yaxes(title="")
            f_inj = apply_layout(f_inj, height=300, showlegend=False)
            inj_subtitle = (f"{len(inj_df)} injury day(s) plotted by player. "
                              "See the Injury Patterns page for case review.")

        injury_card = chart_card(
            "Injury timeline",
            inj_subtitle,
            dcc.Graph(figure=f_inj, config={"displaylogo": False}),
        )

        return (kpis, coach_summary,
                trend_load, trend_fatigue,
                readiness_card, watchlist_card,
                injury_card)
