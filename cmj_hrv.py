"""
5) CMJ & HRV Readiness page.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table

from src.config import (
    COLORS, POSITION_COLORS, READINESS_COLORS, VARIABLE_LABELS,
)
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    apply_filters, player_dropdown, position_dropdown, date_range_picker,
    filter_field, empty_state, safe_focus_player,
)
from src.visuals import (
    apply_layout, empty_fig, scatter_relationship, TABLE_STYLE,
)
from src.insights import generate_cmj_hrv_insight


DATA: pd.DataFrame = None


def _filters():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-4", children=[
            filter_field("Players",   player_dropdown(DATA, "ch-players")),
            filter_field("Positions", position_dropdown(DATA, "ch-positions")),
            filter_field("Date range", date_range_picker(DATA, "ch-dates")),
            filter_field("Focus player (trends)",
                dcc.Dropdown(
                    id="ch-focus",
                    options=[{"label": p, "value": p}
                              for p in sorted(DATA["Player"].unique(),
                                              key=lambda x: int(x.split("_")[-1]))],
                    value=sorted(DATA["Player"].unique(),
                                  key=lambda x: int(x.split("_")[-1]))[0],
                    clearable=False, className="dash-dropdown")),
        ]),
    ])


def layout():
    return html.Div([
        page_header(
            "CMJ & HRV Readiness",
            ("Neuromuscular (countermovement jump) and autonomic (heart-rate "
              "variability) markers compared to each player's own baseline. "
              "Read them together with fatigue and load — never on their own."),
        ),
        _explainer_card(),
        _filters(),
        html.Div(id="ch-kpis"),
        html.Div(id="ch-insight"),

        section_bar("Per-player trends vs baseline"),
        html.Div(className="grid-2", children=[
            html.Div(id="ch-cmj-trend-card"),
            html.Div(id="ch-hrv-trend-card"),
        ]),

        section_bar("Relationships between markers"),
        html.Div(className="grid-3", children=[
            html.Div(id="ch-cmj-fat-card"),
            html.Div(id="ch-hrv-fat-card"),
            html.Div(id="ch-cmj-hrv-card"),
        ]),

        section_bar("Drop tables"),
        html.Div(className="grid-2", children=[
            html.Div(id="ch-cmj-table-card"),
            html.Div(id="ch-hrv-table-card"),
        ]),

        html.Div(id="ch-combined-card"),
    ])


def _explainer_card():
    return html.Div(className="card-pf", children=[
        html.Div(className="card-head", children=[
            html.H4("How to read these markers", className="card-title"),
        ]),
        html.Div(className="grid-3", children=[
            html.Div([
                html.H5("CMJ Height", style={"margin": "0 0 6px",
                                                "color": COLORS["accent"]}),
                html.P("How fresh and powerful the legs look. "
                        "Drops vs the player's own baseline can mean "
                        "neuromuscular fatigue accumulating.",
                        className="dim",
                        style={"fontSize": "13px", "margin": 0}),
            ]),
            html.Div([
                html.H5("HRV (RMSSD)", style={"margin": "0 0 6px",
                                                "color": COLORS["purple"]}),
                html.P("How well the body is recovering between sessions. "
                        "Lower values vs baseline suggest reduced autonomic "
                        "readiness.",
                        className="dim",
                        style={"fontSize": "13px", "margin": 0}),
            ]),
            html.Div([
                html.H5("Resting HR", style={"margin": "0 0 6px",
                                                "color": COLORS["warning"]}),
                html.P("How hard the body is working at rest. Elevated "
                        "values vs baseline can mean fatigue or illness "
                        "onset.",
                        className="dim",
                        style={"fontSize": "13px", "margin": 0}),
            ]),
        ]),
        html.Div("Interpret all three together — a single dropped marker is "
                  "noise; two or three converging signals deserve action.",
                  className="insight-caution",
                  style={"marginTop": "12px"}),
    ])


def register_callbacks(app):

    @app.callback(
        Output("ch-kpis", "children"),
        Output("ch-insight", "children"),
        Output("ch-cmj-trend-card", "children"),
        Output("ch-hrv-trend-card", "children"),
        Output("ch-cmj-fat-card", "children"),
        Output("ch-hrv-fat-card", "children"),
        Output("ch-cmj-hrv-card", "children"),
        Output("ch-cmj-table-card", "children"),
        Output("ch-hrv-table-card", "children"),
        Output("ch-combined-card", "children"),
        Input("ch-players", "value"),
        Input("ch-positions", "value"),
        Input("ch-dates", "start_date"),
        Input("ch-dates", "end_date"),
        Input("ch-focus", "value"),
    )
    def _update(players, positions, start_date, end_date, focus_player):
        df = apply_filters(DATA, players, positions, start_date, end_date)
        focus_player = safe_focus_player(df, focus_player)

        if df.empty:
            return (empty_state(), None, empty_state(), empty_state(),
                    empty_state(), empty_state(), empty_state(),
                    empty_state(), empty_state(), empty_state())

        # KPIs
        cmj_drops = (df["CMJ_Height_PctChange"] <= -5).sum()
        hrv_drops = (df["HRV_RMSSD_PctChange"] <= -10).sum()
        both = ((df["CMJ_Height_PctChange"] <= -5) &
                  (df["HRV_RMSSD_PctChange"] <= -10)).sum()
        kpis = kpi_strip([
            kpi("Mean CMJ",    f"{df['CMJ_Height'].mean():.1f} cm"),
            kpi("Mean HRV",    f"{df['HRV_RMSSD'].mean():.1f} ms"),
            kpi("Mean RHR",    f"{df['Resting_HR'].mean():.1f} bpm"),
            kpi("CMJ drops",   int(cmj_drops),
                 sub="sessions ≥ 5% below baseline",
                 tone="warn" if cmj_drops > 5 else "info"),
            kpi("HRV drops",   int(hrv_drops),
                 sub="sessions ≥ 10% below baseline",
                 tone="warn" if hrv_drops > 5 else "info"),
            kpi("Combined drops", int(both),
                 sub="same day, both signals",
                 tone="bad" if both > 0 else "ok"),
        ])

        ins = generate_cmj_hrv_insight(df)
        insight = html.Div(className=f"insight-box {ins['level']}",
                            style={"marginBottom": "16px"}, children=[
            html.Div(className="insight-headline", children=[
                html.Span("Neuro & HRV insight", className="ins-tag"),
                html.Span(ins["headline"]),
            ]),
            html.Div(ins["detail"], className="insight-detail"),
            html.Div(ins["coaching"], className="insight-coaching"),
            html.Div(ins["caution"], className="insight-caution"),
        ])

        # Trends — focus player vs own baseline
        p_data = df[df["Player"] == focus_player].sort_values("Date")
        if p_data.empty:
            cmj_trend = hrv_trend = empty_state(f"No data for {focus_player}")
        else:
            cmj_base = p_data["CMJ_Height_Baseline"].iloc[0]
            hrv_base = p_data["HRV_RMSSD_Baseline"].iloc[0]

            f_cmj = go.Figure()
            f_cmj.add_trace(go.Scatter(x=p_data["Date"], y=p_data["CMJ_Height"],
                                          mode="lines+markers",
                                          line=dict(color=COLORS["accent"], width=2),
                                          marker=dict(size=5), name="CMJ Height"))
            f_cmj.add_hline(y=cmj_base, line_dash="dash",
                              line_color=COLORS["text_muted"],
                              annotation_text=f"Baseline {cmj_base:.1f} cm",
                              annotation_position="right")
            f_cmj.add_hline(y=cmj_base * 0.95, line_dash="dot",
                              line_color=COLORS["danger"], opacity=0.55,
                              annotation_text="-5% threshold",
                              annotation_position="right")
            f_cmj.update_yaxes(title="CMJ Height (cm)")
            f_cmj.update_xaxes(title="")
            f_cmj = apply_layout(f_cmj, height=320, showlegend=False)
            cmj_trend = chart_card(
                f"CMJ trend — {focus_player}",
                "Dashed line = player's 14-day baseline. Dotted line = -5% threshold.",
                dcc.Graph(figure=f_cmj, config={"displaylogo": False}),
            )

            f_hrv = go.Figure()
            f_hrv.add_trace(go.Scatter(x=p_data["Date"], y=p_data["HRV_RMSSD"],
                                          mode="lines+markers",
                                          line=dict(color=COLORS["purple"], width=2),
                                          marker=dict(size=5), name="HRV RMSSD"))
            f_hrv.add_hline(y=hrv_base, line_dash="dash",
                              line_color=COLORS["text_muted"],
                              annotation_text=f"Baseline {hrv_base:.1f} ms",
                              annotation_position="right")
            f_hrv.add_hline(y=hrv_base * 0.90, line_dash="dot",
                              line_color=COLORS["danger"], opacity=0.55,
                              annotation_text="-10% threshold",
                              annotation_position="right")
            f_hrv.update_yaxes(title="HRV RMSSD (ms)")
            f_hrv.update_xaxes(title="")
            f_hrv = apply_layout(f_hrv, height=320, showlegend=False)
            hrv_trend = chart_card(
                f"HRV trend — {focus_player}",
                "Dashed line = player's 14-day baseline. Dotted line = -10% threshold.",
                dcc.Graph(figure=f_hrv, config={"displaylogo": False}),
            )

        # Relationship scatters
        f_cf = scatter_relationship(df, "Fatigue_Score", "CMJ_Height",
                                       color="Position",
                                       color_map=POSITION_COLORS,
                                       height=320)
        cmj_fat_card = chart_card("CMJ vs Fatigue",
                                    "Does subjective fatigue track CMJ output?",
                                    dcc.Graph(figure=f_cf,
                                                config={"displaylogo": False}))

        f_hf = scatter_relationship(df, "Fatigue_Score", "HRV_RMSSD",
                                       color="Position",
                                       color_map=POSITION_COLORS,
                                       height=320)
        hrv_fat_card = chart_card("HRV vs Fatigue",
                                    "Does subjective fatigue track autonomic recovery?",
                                    dcc.Graph(figure=f_hf,
                                                config={"displaylogo": False}))

        f_ch = scatter_relationship(df, "CMJ_Height", "HRV_RMSSD",
                                       color="Position",
                                       color_map=POSITION_COLORS,
                                       height=320)
        cmj_hrv_card = chart_card("CMJ vs HRV",
                                    "Are the two readiness signals aligned today?",
                                    dcc.Graph(figure=f_ch,
                                                config={"displaylogo": False}))

        # Drop tables
        cmj_tbl = (df[df["CMJ_Height_PctChange"] <= -5]
                      .groupby("Player")
                      .agg(Position=("Position", "first"),
                            Drops=("CMJ_Height_PctChange", "count"),
                            Mean_PctChange=("CMJ_Height_PctChange", "mean"),
                            Min_PctChange=("CMJ_Height_PctChange", "min"))
                      .reset_index().round(2)
                      .sort_values("Drops", ascending=False).head(10))
        cmj_cols = [
            {"name": "Player",    "id": "Player"},
            {"name": "Pos",       "id": "Position"},
            {"name": "Drop days", "id": "Drops"},
            {"name": "Mean %Δ",   "id": "Mean_PctChange"},
            {"name": "Worst %Δ",  "id": "Min_PctChange"},
        ]
        cmj_table_card = chart_card(
            "CMJ drop table",
            "Players with sessions ≥ 5% below their CMJ baseline.",
            (dash_table.DataTable(
                data=cmj_tbl.to_dict("records"), columns=cmj_cols,
                sort_action="native", **TABLE_STYLE,
            ) if not cmj_tbl.empty else
              html.Div("No CMJ drops in this window.", className="muted",
                       style={"padding": "20px", "textAlign": "center"})),
        )

        hrv_tbl = (df[df["HRV_RMSSD_PctChange"] <= -10]
                      .groupby("Player")
                      .agg(Position=("Position", "first"),
                            Drops=("HRV_RMSSD_PctChange", "count"),
                            Mean_PctChange=("HRV_RMSSD_PctChange", "mean"),
                            Min_PctChange=("HRV_RMSSD_PctChange", "min"))
                      .reset_index().round(2)
                      .sort_values("Drops", ascending=False).head(10))
        hrv_cols = [
            {"name": "Player",    "id": "Player"},
            {"name": "Pos",       "id": "Position"},
            {"name": "Drop days", "id": "Drops"},
            {"name": "Mean %Δ",   "id": "Mean_PctChange"},
            {"name": "Worst %Δ",  "id": "Min_PctChange"},
        ]
        hrv_table_card = chart_card(
            "HRV drop table",
            "Players with sessions ≥ 10% below their HRV baseline.",
            (dash_table.DataTable(
                data=hrv_tbl.to_dict("records"), columns=hrv_cols,
                sort_action="native", **TABLE_STYLE,
            ) if not hrv_tbl.empty else
              html.Div("No HRV drops in this window.", className="muted",
                       style={"padding": "20px", "textAlign": "center"})),
        )

        # Combined readiness drop table
        combined_mask = ((df["CMJ_Height_PctChange"] <= -5) &
                         (df["HRV_RMSSD_PctChange"] <= -10))
        comb = df[combined_mask].copy()
        if comb.empty:
            combined_card = chart_card(
                "Combined readiness drops (CMJ ≥ 5% and HRV ≥ 10% below baseline, same day)",
                "Sessions where both neuromuscular and autonomic signals dropped.",
                html.Div("No combined drops in this window — single-signal "
                          "events are below the priority threshold.",
                          className="muted",
                          style={"padding": "20px", "textAlign": "center"}),
            )
        else:
            comb_tbl = (comb.groupby("Player")
                          .agg(Position=("Position", "first"),
                                Days=("Date", "count"),
                                Mean_CMJ_PctChange=("CMJ_Height_PctChange", "mean"),
                                Mean_HRV_PctChange=("HRV_RMSSD_PctChange", "mean"),
                                Mean_Fatigue=("Fatigue_Score", "mean"),
                                Last_Status=("Readiness_Status", "last"))
                          .reset_index().round(2)
                          .sort_values("Days", ascending=False))
            cols = [
                {"name": "Player",   "id": "Player"},
                {"name": "Pos",      "id": "Position"},
                {"name": "Days",     "id": "Days"},
                {"name": "CMJ %Δ",   "id": "Mean_CMJ_PctChange"},
                {"name": "HRV %Δ",   "id": "Mean_HRV_PctChange"},
                {"name": "Fatigue",  "id": "Mean_Fatigue"},
                {"name": "Status",   "id": "Last_Status"},
            ]
            combined_card = chart_card(
                "Combined readiness drops (highest priority)",
                "Players where both CMJ and HRV signals dropped on the same day.",
                dash_table.DataTable(
                    data=comb_tbl.to_dict("records"), columns=cols,
                    sort_action="native",
                    style_data_conditional=[
                        {"if": {"filter_query": '{Last_Status} = "Red"'},
                          "backgroundColor": "rgba(248,113,113,0.15)"},
                    ],
                    **TABLE_STYLE,
                ),
                insight={
                    "headline": (f"{len(comb_tbl)} player(s) showed combined "
                                  "CMJ + HRV drops in this window."),
                    "detail": ("Two converging signals strengthen the case "
                                "for modified training; act with stronger "
                                "confidence than for a single dropped marker."),
                    "coaching": ("Reduce high-speed running exposure for these "
                                  "players for the next 48–72 h and re-check "
                                  "before the next intense block."),
                    "caution": "Baseline biases (player tired during baseline window) can affect this table.",
                    "level": "warning",
                },
            )

        return (kpis, insight, cmj_trend, hrv_trend,
                cmj_fat_card, hrv_fat_card, cmj_hrv_card,
                cmj_table_card, hrv_table_card, combined_card)
