"""
8) Position Comparison page.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output

from src.config import (
    COLORS, POSITION_COLORS, READINESS_COLORS, VARIABLE_LABELS,
    EXTERNAL_LOAD_VARS, INTERNAL_LOAD_VARS, WELLNESS_VARS, NEURO_VARS,
)
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    apply_filters, position_dropdown, date_range_picker,
    filter_field, empty_state, safe_metric,
)
from src.visuals import apply_layout, empty_fig, box_by_group
from src.insights import generate_comparison_insight


DATA: pd.DataFrame = None

POSITION_METRICS = EXTERNAL_LOAD_VARS + INTERNAL_LOAD_VARS + WELLNESS_VARS + NEURO_VARS


def _filters():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-3", children=[
            filter_field("Positions",  position_dropdown(DATA, "ps-positions")),
            filter_field("Date range", date_range_picker(DATA, "ps-dates")),
            filter_field("Primary metric",
                dcc.Dropdown(id="ps-metric",
                    options=([{"label": "── External load", "value": "",
                                "disabled": True}] +
                              [{"label": VARIABLE_LABELS.get(m, m), "value": m}
                                for m in EXTERNAL_LOAD_VARS] +
                              [{"label": "── Internal load", "value": "_",
                                "disabled": True}] +
                              [{"label": VARIABLE_LABELS.get(m, m), "value": m}
                                for m in INTERNAL_LOAD_VARS] +
                              [{"label": "── Wellness", "value": "__",
                                "disabled": True}] +
                              [{"label": VARIABLE_LABELS.get(m, m), "value": m}
                                for m in WELLNESS_VARS] +
                              [{"label": "── Neuro", "value": "___",
                                "disabled": True}] +
                              [{"label": VARIABLE_LABELS.get(m, m), "value": m}
                                for m in NEURO_VARS]),
                    value="Session_Load", clearable=False,
                    className="dash-dropdown")),
        ]),
    ])


def layout():
    return html.Div([
        page_header(
            "Position Comparison",
            ("Compare positional groups across load, wellness, and "
              "recovery markers."),
        ),
        _filters(),
        html.Div(id="ps-kpis"),
        html.Div(id="ps-insight"),

        section_bar("Primary metric"),
        html.Div(id="ps-box-card"),

        section_bar("External load vs fatigue & CMJ"),
        html.Div(className="grid-2", children=[
            html.Div(id="ps-ext-card"),
            html.Div(id="ps-fat-cmj-card"),
        ]),

        section_bar("Readiness mix by position"),
        html.Div(id="ps-mix-card"),

        section_bar("Workload & fatigue rankings within positions"),
        html.Div(className="grid-2", children=[
            html.Div(id="ps-rank-load-card"),
            html.Div(id="ps-rank-fat-card"),
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("ps-kpis", "children"),
        Output("ps-insight", "children"),
        Output("ps-box-card", "children"),
        Output("ps-ext-card", "children"),
        Output("ps-fat-cmj-card", "children"),
        Output("ps-mix-card", "children"),
        Output("ps-rank-load-card", "children"),
        Output("ps-rank-fat-card", "children"),
        Input("ps-positions", "value"),
        Input("ps-dates", "start_date"),
        Input("ps-dates", "end_date"),
        Input("ps-metric", "value"),
    )
    def _update(positions, start_date, end_date, metric):
        metric = safe_metric(metric, "Session_Load", POSITION_METRICS)
        df = apply_filters(DATA, positions=positions,
                            start_date=start_date, end_date=end_date)
        if df.empty:
            return (empty_state(), None, empty_state(), empty_state(),
                    empty_state(), empty_state(), empty_state(), empty_state())

        # KPIs
        load_by_pos = df.groupby("Position")["Session_Load"].mean().sort_values(ascending=False)
        fat_by_pos  = df.groupby("Position")["Fatigue_Score"].mean().sort_values(ascending=False)
        cmj_by_pos  = df.groupby("Position")["CMJ_Height"].mean().sort_values()
        pct_red = (df["Readiness_Status"] == "Red").mean() * 100

        kpis = kpi_strip([
            kpi("Positions in view", df["Position"].nunique(), tone="info"),
            kpi("Sessions",          f"{len(df):,}"),
            kpi("Highest load",
                 f"{load_by_pos.index[0]}",
                 sub=f"{load_by_pos.iloc[0]:.0f} AU"),
            kpi("Highest fatigue",
                 f"{fat_by_pos.index[0]}",
                 sub=f"{fat_by_pos.iloc[0]:.2f}/5",
                 tone="warn"),
            kpi("Lowest CMJ",
                 f"{cmj_by_pos.index[0]}",
                 sub=f"{cmj_by_pos.iloc[0]:.1f} cm",
                 tone="info"),
            kpi("Red sessions",      f"{pct_red:.1f}%",
                 tone="bad" if pct_red > 8 else "warn" if pct_red > 3 else "ok"),
        ])

        # Insight
        ins = generate_comparison_insight(
            df, "Position",
            ["Session_Load", "ACWR", "Fatigue_Score", "HRV_RMSSD", "CMJ_Height"],
        )
        insight = html.Div(className=f"insight-box {ins['level']}",
                            style={"marginBottom": "16px"}, children=[
            html.Div(className="insight-headline", children=[
                html.Span("Positional insight", className="ins-tag"),
                html.Span(ins["headline"]),
            ]),
            html.Div(ins["detail"], className="insight-detail"),
            html.Div(ins["coaching"], className="insight-coaching"),
            html.Div(ins["caution"], className="insight-caution"),
        ])

        # Box plot for chosen metric
        f_box = box_by_group(df, metric, "Position",
                              color_map=POSITION_COLORS, height=380)
        box_card = chart_card(
            f"Distribution: {VARIABLE_LABELS.get(metric, metric)}",
            "Spread by positional group.",
            dcc.Graph(figure=f_box, config={"displaylogo": False}),
        )

        # External load by position (grouped bar)
        ext_summary = (df.groupby("Position")[EXTERNAL_LOAD_VARS]
                            .mean().reset_index().melt(id_vars="Position",
                                                          var_name="Metric",
                                                          value_name="Mean"))
        f_ext = px.bar(ext_summary, x="Metric", y="Mean",
                        color="Position", barmode="group",
                        color_discrete_map=POSITION_COLORS)
        f_ext.update_traces(marker_line_width=0)
        f_ext.update_xaxes(title="")
        f_ext.update_yaxes(title="Mean value")
        f_ext = apply_layout(f_ext, height=360)
        ext_card = chart_card(
            "External load by position",
            "Mean of each external-load metric per positional group.",
            dcc.Graph(figure=f_ext, config={"displaylogo": False}),
        )

        # Fatigue + CMJ combined
        fat_cmj = (df.groupby("Position")
                      .agg(Fatigue=("Fatigue_Score", "mean"),
                            CMJ=("CMJ_Height", "mean"))
                      .reset_index().sort_values("Fatigue"))
        f_fc = go.Figure()
        f_fc.add_trace(go.Bar(x=fat_cmj["Position"], y=fat_cmj["Fatigue"],
                                  name="Fatigue (1–5)",
                                  marker_color=COLORS["warning"],
                                  marker_line_width=0))
        f_fc.add_trace(go.Scatter(x=fat_cmj["Position"], y=fat_cmj["CMJ"],
                                      mode="lines+markers", name="CMJ (cm)",
                                      line=dict(color=COLORS["accent"], width=2),
                                      marker=dict(size=10),
                                      yaxis="y2"))
        f_fc.update_layout(
            yaxis=dict(title="Fatigue (1–5)"),
            yaxis2=dict(title="CMJ (cm)", overlaying="y", side="right",
                          showgrid=False),
        )
        f_fc.update_xaxes(title="")
        f_fc = apply_layout(f_fc, height=360)
        fat_cmj_card = chart_card(
            "Fatigue (bars) vs CMJ (line)",
            "Per-position mean values on a dual axis.",
            dcc.Graph(figure=f_fc, config={"displaylogo": False}),
        )

        # Readiness mix
        mix = (df.groupby(["Position", "Readiness_Status"]).size()
                  .unstack(fill_value=0))
        for col in ["Green", "Yellow", "Red"]:
            if col not in mix.columns:
                mix[col] = 0
        mix_pct = mix[["Green", "Yellow", "Red"]].div(mix.sum(axis=1), axis=0) * 100
        f_mix = go.Figure()
        for status in ["Green", "Yellow", "Red"]:
            f_mix.add_trace(go.Bar(x=mix_pct.index, y=mix_pct[status],
                                      name=status,
                                      marker_color=READINESS_COLORS[status],
                                      marker_line_width=0))
        f_mix.update_layout(barmode="stack")
        f_mix.update_yaxes(title="% of sessions", range=[0, 100])
        f_mix.update_xaxes(title="")
        f_mix = apply_layout(f_mix, height=320)
        mix_card = chart_card(
            "Readiness mix",
            "Each position's share of Green / Yellow / Red sessions.",
            dcc.Graph(figure=f_mix, config={"displaylogo": False}),
        )

        # Rankings within position (top players by load and fatigue)
        load_rank = (df.groupby(["Player", "Position"])["Session_Load"]
                       .mean().reset_index()
                       .sort_values("Session_Load", ascending=False).head(15))
        f_load = px.bar(load_rank.sort_values("Session_Load"),
                         x="Session_Load", y="Player", orientation="h",
                         color="Position", color_discrete_map=POSITION_COLORS)
        f_load.update_traces(marker_line_width=0)
        f_load.update_xaxes(title="Mean Session Load (AU)")
        f_load.update_yaxes(title="")
        f_load = apply_layout(f_load, height=400)
        rank_load_card = chart_card(
            "Top 15 — workload (mean Session Load)",
            "Highest individual workload, coloured by position.",
            dcc.Graph(figure=f_load, config={"displaylogo": False}),
        )

        fat_rank = (df.groupby(["Player", "Position"])["Fatigue_Score"]
                       .mean().reset_index()
                       .sort_values("Fatigue_Score", ascending=False).head(15))
        f_fat = px.bar(fat_rank.sort_values("Fatigue_Score"),
                         x="Fatigue_Score", y="Player", orientation="h",
                         color="Position", color_discrete_map=POSITION_COLORS)
        f_fat.update_traces(marker_line_width=0)
        f_fat.update_xaxes(title="Mean Fatigue (1–5)")
        f_fat.update_yaxes(title="")
        f_fat = apply_layout(f_fat, height=400)
        rank_fat_card = chart_card(
            "Top 15 — fatigue (mean Fatigue Score)",
            "Highest individual subjective fatigue, coloured by position.",
            dcc.Graph(figure=f_fat, config={"displaylogo": False}),
        )

        return (kpis, insight, box_card, ext_card, fat_cmj_card,
                mix_card, rank_load_card, rank_fat_card)
