"""
3) ACWR & Workload Spike page.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table

from src.config import (
    COLORS, POSITION_COLORS, ACWR_ZONE_COLORS, VARIABLE_LABELS,
)
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    apply_filters, player_dropdown, position_dropdown, date_range_picker,
    filter_field, empty_state, safe_metric,
)
from src.visuals import (
    apply_layout, empty_fig, acwr_zoned_line, TABLE_STYLE,
)
from src.insights import generate_acwr_insight


DATA: pd.DataFrame = None


def _filters():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-4", children=[
            filter_field("Players",   player_dropdown(DATA, "ac-players")),
            filter_field("Positions", position_dropdown(DATA, "ac-positions")),
            filter_field("Date range", date_range_picker(DATA, "ac-dates")),
            filter_field("ACWR source",
                dcc.Dropdown(id="ac-source",
                    options=[{"label": "Dataset ACWR", "value": "ACWR"},
                             {"label": "Calculated ACWR (7d avg / 28d avg)", "value": "ACWR_Calc"}],
                    value="ACWR", clearable=False, className="dash-dropdown")),
        ]),
    ])


def layout():
    return html.Div([
        page_header(
            "ACWR & Workload Spikes",
            ("Acute-to-Chronic Workload Ratio (7 / 28-day rolling Session "
              "Load) with practical monitoring zones. ACWR is a workload "
              "tool, not a medical rule."),
        ),
        _filters(),
        html.Div(id="ac-kpis"),
        html.Div(id="ac-insight"),

        section_bar("Squad ACWR trend & zones"),
        html.Div(className="grid-2", children=[
            html.Div(id="ac-trend-card"),
            html.Div(id="ac-dist-card"),
        ]),

        section_bar("Acute vs chronic, spike ranking"),
        html.Div(className="grid-2", children=[
            html.Div(id="ac-scatter-card"),
            html.Div(id="ac-rank-card"),
        ]),

        section_bar("Pre-injury ACWR window"),
        html.Div(id="ac-preinjury-card"),

        html.Div(className="note-banner", children=[
            html.Strong("How to read ACWR zones — "),
            "Underload (<0.8): possible undertraining. Optimal (0.8–1.3): "
            "well-managed. Caution (1.3–1.5): elevated acute load — monitor "
            "the next session. High Spike (>1.5): consider modifying training "
            "and recheck recovery markers. These thresholds are practical "
            "monitoring guides, not universal medical rules.",
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("ac-kpis", "children"),
        Output("ac-insight", "children"),
        Output("ac-trend-card", "children"),
        Output("ac-dist-card", "children"),
        Output("ac-scatter-card", "children"),
        Output("ac-rank-card", "children"),
        Output("ac-preinjury-card", "children"),
        Input("ac-players", "value"),
        Input("ac-positions", "value"),
        Input("ac-dates", "start_date"),
        Input("ac-dates", "end_date"),
        Input("ac-source", "value"),
    )
    def _update(players, positions, start_date, end_date, acwr_source):
        acwr_col = safe_metric(acwr_source, "ACWR", ["ACWR", "ACWR_Calc"])
        df = apply_filters(DATA, players, positions, start_date, end_date)
        if acwr_col != "ACWR":
            df = df.copy()
            df["ACWR_Display"] = df[acwr_col]
            df["ACWR_Zone_Display"] = df["ACWR_Calc_Zone"]
        else:
            df = df.copy()
            df["ACWR_Display"] = df["ACWR"]
            df["ACWR_Zone_Display"] = df["ACWR_Zone"]

        if df.empty:
            return (empty_state(), None, empty_state(), empty_state(),
                    empty_state(), empty_state(), empty_state())
        df["Flag_ACWR_High_Display"] = df["ACWR_Display"] > 1.3
        df["Flag_ACWR_Spike_Display"] = df["ACWR_Display"] > 1.5

        # KPIs
        underload = (df["ACWR_Zone_Display"] == "Underload").sum()
        optimal   = (df["ACWR_Zone_Display"] == "Optimal").sum()
        caution   = (df["ACWR_Zone_Display"] == "Caution").sum()
        spike     = (df["ACWR_Zone_Display"] == "High Spike").sum()
        mean_acwr = df["ACWR_Display"].mean()

        kpis = kpi_strip([
            kpi("Sessions",   f"{len(df):,}"),
            kpi("Mean ACWR",  f"{mean_acwr:.2f}",
                 tone="bad" if mean_acwr > 1.3 else "info"),
            kpi("Max ACWR",   f"{df['ACWR_Display'].max():.2f}", tone="warn"),
            kpi("Underload",  int(underload), tone="info"),
            kpi("Optimal",    int(optimal),   tone="ok"),
            kpi("Caution",    int(caution),   tone="warn"),
            kpi("High Spike", int(spike),
                 tone="bad" if spike > 0 else "info"),
        ])

        # Insight
        ins_df = df.copy()
        ins_df["ACWR"] = ins_df["ACWR_Display"]
        ins_df["Flag_ACWR_High"] = ins_df["Flag_ACWR_High_Display"]
        ins_df["Flag_ACWR_Spike"] = ins_df["Flag_ACWR_Spike_Display"]
        ins = generate_acwr_insight(ins_df)
        insight = html.Div(className=f"insight-box {ins['level']}",
                            style={"marginBottom": "16px"}, children=[
            html.Div(className="insight-headline", children=[
                html.Span("ACWR insight", className="ins-tag"),
                html.Span(ins["headline"]),
            ]),
            html.Div(ins["detail"], className="insight-detail"),
            html.Div(ins["coaching"], className="insight-coaching"),
            html.Div(ins["caution"], className="insight-caution"),
        ])

        # Trend
        f_trend = acwr_zoned_line(df, height=320, metric="ACWR_Display")
        trend_card = chart_card(
            "Squad ACWR over time",
            "Daily mean selected ACWR source with the four monitoring zones shaded behind.",
            dcc.Graph(figure=f_trend, config={"displaylogo": False}),
        )

        # Distribution
        zone_counts = (df["ACWR_Zone_Display"].value_counts()
                          .reindex(["Underload", "Optimal", "Caution", "High Spike"])
                          .fillna(0))
        f_dist = go.Figure(data=go.Bar(
            x=zone_counts.index, y=zone_counts.values,
            marker_color=[ACWR_ZONE_COLORS[z] for z in zone_counts.index],
            marker_line_width=0,
        ))
        f_dist.update_yaxes(title="Sessions")
        f_dist.update_xaxes(title="")
        f_dist = apply_layout(f_dist, height=320, showlegend=False)
        dist_card = chart_card(
            "Zone distribution",
            "How many sessions fell in each ACWR band.",
            dcc.Graph(figure=f_dist, config={"displaylogo": False}),
        )

        # Acute vs chronic scatter
        f_scat = px.scatter(df, x="Chronic_Load_Avg_28", y="Acute_Load_Avg_7",
                              color="ACWR_Zone_Display",
                              color_discrete_map=ACWR_ZONE_COLORS,
                              hover_data=["Player", "Date", "ACWR", "ACWR_Calc"])
        f_scat.update_traces(marker=dict(size=6, line=dict(width=0), opacity=0.65))
        # ACWR=1 reference line
        if df["Chronic_Load_Avg_28"].max() > 0:
            xs = [0, df["Chronic_Load_Avg_28"].max()]
            f_scat.add_trace(go.Scatter(x=xs, y=xs, mode="lines",
                                          line=dict(color=COLORS["text_muted"],
                                                      width=1, dash="dash"),
                                          name="ACWR = 1", showlegend=False))
        f_scat.update_xaxes(title="Chronic Load Avg (28-d)")
        f_scat.update_yaxes(title="Acute Load Avg (7-d)")
        f_scat = apply_layout(f_scat, height=380)
        scatter_card = chart_card(
            "Acute vs chronic load",
            "Each dot is one player-day. Distance from the dashed ACWR=1 line "
            "shows how far a session sits from the optimal band.",
            dcc.Graph(figure=f_scat, config={"displaylogo": False}),
        )

        # Spike ranking
        spike_table = (df.groupby(["Player", "Position"])
                          .agg(Spike_Days=("Flag_ACWR_Spike_Display", "sum"),
                                Caution_Days=("Flag_ACWR_High_Display", "sum"),
                                Mean_ACWR=("ACWR_Display", "mean"),
                                Max_ACWR=("ACWR_Display", "max"))
                          .reset_index()
                          .round(2))
        spike_table["Spike_Days"] = spike_table["Spike_Days"].astype(int)
        spike_table["Caution_Days"] = (spike_table["Caution_Days"].astype(int)
                                          - spike_table["Spike_Days"])
        spike_table = spike_table.sort_values(["Spike_Days", "Max_ACWR"],
                                                ascending=[False, False]).head(12)

        cols = [
            {"name": "Player",       "id": "Player"},
            {"name": "Pos",          "id": "Position"},
            {"name": "Spike days",   "id": "Spike_Days"},
            {"name": "Caution days", "id": "Caution_Days"},
            {"name": "Mean ACWR",    "id": "Mean_ACWR"},
            {"name": "Max ACWR",     "id": "Max_ACWR"},
        ]
        rank_card = chart_card(
            "Repeated-spike players",
            "Top 12 by count of ACWR > 1.5 sessions in the window.",
            dash_table.DataTable(
                data=spike_table.to_dict("records"), columns=cols,
                sort_action="native",
                style_data_conditional=[
                    {"if": {"filter_query": "{Spike_Days} >= 2"},
                      "backgroundColor": "rgba(248,113,113,0.10)"},
                ],
                **TABLE_STYLE,
            ),
        )

        # Pre-injury ACWR
        preinj_card = _preinjury_card(df)
        return (kpis, insight, trend_card, dist_card,
                scatter_card, rank_card, preinj_card)


def _preinjury_card(df: pd.DataFrame):
    inj_rows = df[df["Injury_Label"] == 1]
    if inj_rows.empty:
        return chart_card(
            "Pre-injury ACWR window",
            "No injuries in the current window.",
            html.Div("Nothing to plot — adjust filters to include an injury date.",
                      className="muted", style={"padding": "20px",
                                                 "textAlign": "center"}),
        )
    rows = []
    for _, r in inj_rows.iterrows():
        player = r["Player"]
        injury_date = r["Date"]
        pre = DATA[(DATA["Player"] == player) &
                    (DATA["Date"] >= injury_date - pd.Timedelta(days=14)) &
                    (DATA["Date"] <= injury_date)].copy()
        pre["Days_From_Injury"] = (pre["Date"] - injury_date).dt.days
        pre["Case"] = f"{player} @ {injury_date.strftime('%b %d')}"
        rows.append(pre)
    pre_all = pd.concat(rows)
    if pre_all.empty:
        return chart_card("Pre-injury ACWR window",
                          "No pre-injury data available.",
                          empty_fig())
    fig = px.line(pre_all, x="Days_From_Injury", y="ACWR", color="Case", markers=True)
    fig.add_vline(x=0, line_dash="dash", line_color=COLORS["danger"],
                   annotation_text="Injury day",
                   annotation_position="top right")
    fig.add_hline(y=1.5, line_dash="dot", line_color=COLORS["danger"], opacity=0.4)
    fig.add_hline(y=1.3, line_dash="dot", line_color=COLORS["warning"], opacity=0.4)
    fig.update_xaxes(title="Days from injury (negative = before)")
    fig.update_yaxes(title="ACWR")
    fig = apply_layout(fig, height=380)
    return chart_card(
        "ACWR in the 14 days before each injury",
        "Each line is one case. The vertical dashed line is the injury day.",
        dcc.Graph(figure=fig, config={"displaylogo": False}),
        insight={
            "headline": ("With only a handful of injury cases, any pre-injury "
                          "pattern here is descriptive, not predictive."),
            "detail": ("Look for whether ACWR crossed the 1.3 caution line in "
                        "the days immediately before the injury day."),
            "coaching": ("Use this view in retrospective case review with the "
                          "medical team. Do not generalise from these specific "
                          "lines to new players."),
            "caution": "Very small n — no statistical claim can be made.",
            "level": "warning",
        },
    )
