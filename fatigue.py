"""
4) Fatigue & Wellness page.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table

from src.config import (
    COLORS, POSITION_COLORS, READINESS_COLORS, VARIABLE_LABELS,
    HIGHER_IS_WORSE,
)
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    apply_filters, player_dropdown, position_dropdown, date_range_picker,
    filter_field, empty_state, status_filter, safe_metric, safe_focus_player,
)
from src.visuals import (
    apply_layout, empty_fig, player_wellness_heatmap, dual_axis_trend,
    radar_compare, normalize_metric, TABLE_STYLE,
)
from src.insights import generate_fatigue_insight


DATA: pd.DataFrame = None

WELLNESS_METRICS = ["Fatigue_Score", "Soreness_Score", "Sleep_Quality",
                     "RPE", "HRV_RMSSD", "Resting_HR"]


def _filters():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-3", children=[
            filter_field("Players",   player_dropdown(DATA, "ft-players")),
            filter_field("Positions", position_dropdown(DATA, "ft-positions")),
            filter_field("Date range", date_range_picker(DATA, "ft-dates")),
        ]),
        html.Div(style={"height": "10px"}),
        html.Div(className="grid-3", children=[
            filter_field("Heatmap metric",
                dcc.Dropdown(id="ft-heatmap-metric",
                    options=[{"label": VARIABLE_LABELS.get(m, m), "value": m}
                              for m in WELLNESS_METRICS],
                    value="Fatigue_Score", clearable=False,
                    className="dash-dropdown")),
            filter_field("Radar player",
                dcc.Dropdown(id="ft-radar-player",
                    options=[{"label": p, "value": p}
                              for p in sorted(DATA["Player"].unique(),
                                              key=lambda x: int(x.split("_")[-1]))],
                    value=sorted(DATA["Player"].unique(),
                                  key=lambda x: int(x.split("_")[-1]))[0],
                    clearable=False, className="dash-dropdown")),
            filter_field("Readiness status", status_filter("ft-status")),
        ]),
    ])


def layout():
    return html.Div([
        page_header(
            "Fatigue & Wellness",
            ("Subjective wellness (fatigue, soreness, sleep, RPE) and "
              "autonomic markers (HRV, Resting HR). Use it to find who needs "
              "recovery support — but cross-check with objective load before "
              "modifying any plan."),
        ),
        _filters(),
        html.Div(id="ft-kpis"),
        html.Div(id="ft-insight"),

        section_bar("Player × Day wellness heatmap"),
        html.Div(id="ft-heatmap-card"),

        section_bar("Trends"),
        html.Div(className="grid-2", children=[
            html.Div(id="ft-trend-fat-card"),
            html.Div(id="ft-trend-sleep-card"),
        ]),

        section_bar("Player profile vs squad"),
        html.Div(className="grid-2", children=[
            html.Div(id="ft-radar-card"),
            html.Div(id="ft-readiness-mix-card"),
        ]),

        section_bar("Poor recovery table"),
        html.Div(id="ft-poor-recovery-card"),
    ])


def register_callbacks(app):

    @app.callback(
        Output("ft-kpis", "children"),
        Output("ft-insight", "children"),
        Output("ft-heatmap-card", "children"),
        Output("ft-trend-fat-card", "children"),
        Output("ft-trend-sleep-card", "children"),
        Output("ft-radar-card", "children"),
        Output("ft-readiness-mix-card", "children"),
        Output("ft-poor-recovery-card", "children"),
        Input("ft-players", "value"),
        Input("ft-positions", "value"),
        Input("ft-dates", "start_date"),
        Input("ft-dates", "end_date"),
        Input("ft-heatmap-metric", "value"),
        Input("ft-radar-player", "value"),
        Input("ft-status", "value"),
    )
    def _update(players, positions, start_date, end_date,
                  heatmap_metric, radar_player, statuses):
        heatmap_metric = safe_metric(heatmap_metric, "Fatigue_Score", WELLNESS_METRICS)
        df = apply_filters(DATA, players, positions, start_date, end_date, statuses)
        radar_player = safe_focus_player(df, radar_player)

        if df.empty:
            return (empty_state(), None, empty_state(), empty_state(),
                    empty_state(), empty_state(), empty_state(), empty_state())

        # KPIs
        pct_red = (df["Readiness_Status"] == "Red").mean() * 100
        kpis = kpi_strip([
            kpi("Mean Fatigue",  f"{df['Fatigue_Score'].mean():.2f}/5",
                 tone="warn" if df['Fatigue_Score'].mean() > 3.5 else "info"),
            kpi("Mean Soreness", f"{df['Soreness_Score'].mean():.2f}/5",
                 tone="warn" if df['Soreness_Score'].mean() > 3.5 else "info"),
            kpi("Mean Sleep",    f"{df['Sleep_Quality'].mean():.2f}/5",
                 tone="warn" if df['Sleep_Quality'].mean() < 3 else "info"),
            kpi("Mean RPE",      f"{df['RPE'].mean():.1f}/10"),
            kpi("Mean HRV",      f"{df['HRV_RMSSD'].mean():.1f} ms"),
            kpi("Mean Resting HR", f"{df['Resting_HR'].mean():.1f} bpm"),
            kpi("Red sessions",  f"{pct_red:.1f}%",
                 tone="bad" if pct_red > 8 else "warn" if pct_red > 3 else "ok"),
        ])

        # Insight
        ins = generate_fatigue_insight(df)
        insight = html.Div(className=f"insight-box {ins['level']}",
                            style={"marginBottom": "16px"}, children=[
            html.Div(className="insight-headline", children=[
                html.Span("Wellness insight", className="ins-tag"),
                html.Span(ins["headline"]),
            ]),
            html.Div(ins["detail"], className="insight-detail"),
            html.Div(ins["coaching"], className="insight-coaching"),
            html.Div(ins["caution"], className="insight-caution"),
        ])

        # Heatmap
        f_hm = player_wellness_heatmap(df, metric=heatmap_metric, height=480)
        scale_note = ("Red = worse" if HIGHER_IS_WORSE.get(heatmap_metric, False)
                        else "Red = lower (worse)" if heatmap_metric in
                        {"Sleep_Quality", "HRV_RMSSD", "CMJ_Height"} else "")
        heatmap_card = chart_card(
            f"{VARIABLE_LABELS.get(heatmap_metric, heatmap_metric)} — player × day",
            f"One row per player, one column per day. {scale_note}.",
            dcc.Graph(figure=f_hm, config={"displaylogo": False}),
            tag=heatmap_metric,
        )

        # Trends
        daily = df.groupby("Date").agg(
            Fatigue=("Fatigue_Score", "mean"),
            Soreness=("Soreness_Score", "mean"),
            Sleep=("Sleep_Quality", "mean"),
            RPE=("RPE", "mean"),
            HRV=("HRV_RMSSD", "mean"),
            RHR=("Resting_HR", "mean"),
        ).reset_index()

        f_fat = go.Figure()
        f_fat.add_trace(go.Scatter(x=daily["Date"], y=daily["Fatigue"],
                                      mode="lines", name="Fatigue (1–5)",
                                      line=dict(color=COLORS["warning"], width=2)))
        f_fat.add_trace(go.Scatter(x=daily["Date"], y=daily["Soreness"],
                                      mode="lines", name="Soreness (1–5)",
                                      line=dict(color=COLORS["danger"], width=2,
                                                  dash="dot")))
        f_fat.update_xaxes(title=""); f_fat.update_yaxes(title="Score (1–5)")
        f_fat = apply_layout(f_fat, height=300)
        trend_fat = chart_card(
            "Squad fatigue vs soreness",
            "Daily squad means.",
            dcc.Graph(figure=f_fat, config={"displaylogo": False}),
        )

        f_sleep = go.Figure()
        f_sleep.add_trace(go.Scatter(x=daily["Date"], y=daily["Sleep"],
                                        mode="lines", name="Sleep (1–5)",
                                        line=dict(color=COLORS["success"], width=2)))
        f_sleep.add_trace(go.Scatter(x=daily["Date"], y=daily["RPE"],
                                        mode="lines", name="RPE (0–10)",
                                        line=dict(color=COLORS["accent"], width=2,
                                                    dash="dot"), yaxis="y2"))
        # Dual-axis layout
        f_sleep.update_layout(yaxis=dict(title="Sleep (1–5)"),
                                yaxis2=dict(title="RPE (0–10)",
                                              overlaying="y", side="right",
                                              showgrid=False))
        f_sleep.update_xaxes(title="")
        f_sleep = apply_layout(f_sleep, height=300)
        trend_sleep = chart_card(
            "Sleep vs perceived effort",
            "Daily squad mean sleep quality (left axis) and RPE (right axis).",
            dcc.Graph(figure=f_sleep, config={"displaylogo": False}),
        )

        # Radar
        radar_card = _radar_card(df, radar_player)

        # Readiness mix by position
        mix = (df.groupby(["Position", "Readiness_Status"]).size()
                  .unstack(fill_value=0))
        for col in ["Green", "Yellow", "Red"]:
            if col not in mix.columns:
                mix[col] = 0
        mix_pct = mix[["Green", "Yellow", "Red"]].div(mix.sum(axis=1), axis=0) * 100
        f_mix = go.Figure()
        for status in ["Green", "Yellow", "Red"]:
            f_mix.add_trace(go.Bar(x=mix_pct.index, y=mix_pct[status],
                                      name=status, marker_color=READINESS_COLORS[status],
                                      marker_line_width=0))
        f_mix.update_layout(barmode="stack")
        f_mix.update_yaxes(title="% of sessions", range=[0, 100])
        f_mix.update_xaxes(title="")
        f_mix = apply_layout(f_mix, height=340)
        mix_card = chart_card(
            "Readiness mix by position",
            "What share of sessions per position fell in each status zone.",
            dcc.Graph(figure=f_mix, config={"displaylogo": False}),
        )

        # Poor-recovery table
        recent = df[df["Date"] >= df["Date"].max() - pd.Timedelta(days=7)]
        tbl = (recent.groupby("Player")
                  .agg(Position=("Position", "first"),
                        Fatigue=("Fatigue_Score", "mean"),
                        Soreness=("Soreness_Score", "mean"),
                        Sleep=("Sleep_Quality", "mean"),
                        HRV=("HRV_RMSSD", "mean"),
                        HRV_Pct=("HRV_RMSSD_PctChange", "mean"),
                        Status=("Readiness_Status", "last"))
                  .reset_index().round(2))
        # Flag rule: any of {high fatigue, high soreness, low sleep, low HRV}
        mask = ((tbl["Fatigue"] >= 3.5) | (tbl["Soreness"] >= 3.5) |
                  (tbl["Sleep"] <= 3) | (tbl["HRV_Pct"] <= -10))
        tbl = tbl[mask].sort_values("Fatigue", ascending=False).head(10)
        cols = [
            {"name": "Player",    "id": "Player"},
            {"name": "Pos",       "id": "Position"},
            {"name": "Fatigue",   "id": "Fatigue"},
            {"name": "Soreness",  "id": "Soreness"},
            {"name": "Sleep",     "id": "Sleep"},
            {"name": "HRV (ms)",  "id": "HRV"},
            {"name": "HRV %Δ",    "id": "HRV_Pct"},
            {"name": "Status",    "id": "Status"},
        ]
        poor_card = chart_card(
            "Players showing poor recovery markers (last 7 days)",
            "Auto-filtered: fatigue ≥ 3.5, soreness ≥ 3.5, sleep ≤ 3, or HRV ≤ -10% baseline.",
            (dash_table.DataTable(
                data=tbl.to_dict("records"), columns=cols,
                sort_action="native",
                style_data_conditional=[
                    {"if": {"filter_query": '{Status} = "Red"'},
                      "backgroundColor": "rgba(248,113,113,0.12)"},
                    {"if": {"filter_query": '{Status} = "Yellow"'},
                      "backgroundColor": "rgba(245,158,11,0.10)"},
                ],
                **TABLE_STYLE,
            ) if not tbl.empty else
              html.Div("No player triggered the recovery filters in this window.",
                       className="muted",
                       style={"padding": "20px", "textAlign": "center"})),
        )

        return (kpis, insight, heatmap_card, trend_fat, trend_sleep,
                radar_card, mix_card, poor_card)


def _radar_card(df: pd.DataFrame, player: str):
    metrics = ["Fatigue_Score", "Soreness_Score", "Sleep_Quality",
                "HRV_RMSSD", "CMJ_Height", "ACWR"]
    p_data = df[df["Player"] == player]
    if p_data.empty:
        return chart_card(
            "Wellness radar — selected player",
            "No data for the chosen player.",
            empty_fig("No data for the selected player."),
        )

    # Normalise relative to whole squad in current filter
    reverse_for = {"Sleep_Quality", "HRV_RMSSD", "CMJ_Height"}  # higher = good
    player_vals = []
    squad_vals  = []
    for m in metrics:
        ref = df[m].dropna()
        if ref.empty:
            player_vals.append(0.5); squad_vals.append(0.5); continue
        player_vals.append(normalize_metric(p_data[m].dropna(), ref=ref,
                                              reverse=m in reverse_for))
        squad_vals.append(normalize_metric(ref, ref=ref,
                                              reverse=m in reverse_for))

    f = radar_compare({player: player_vals, "Squad mean": squad_vals},
                      metrics=metrics, height=420)
    return chart_card(
        f"Wellness radar — {player} vs squad mean",
        ("Values normalised 0–1 vs the current selection. For this risk radar, further-out means more monitoring concern; sleep, HRV and CMJ are inverted."),
        dcc.Graph(figure=f, config={"displaylogo": False}),
    )
