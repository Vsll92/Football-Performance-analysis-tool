"""
6) Injury-Risk Pattern page.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, dash_table

from src.config import COLORS, POSITION_COLORS, VARIABLE_LABELS
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    apply_filters, player_dropdown, position_dropdown, status_filter, date_range_picker,
    filter_field, empty_state, traffic_badge, injury_filter_options,
)
from src.visuals import (
    apply_layout, empty_fig, box_by_group, heatmap_correlation, TABLE_STYLE,
)
from src.insights import generate_injury_pattern_insight


DATA: pd.DataFrame = None


def _filters():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-5", children=[
            filter_field("Players", player_dropdown(DATA, "in-players")),
            filter_field("Positions", position_dropdown(DATA, "in-positions")),
            filter_field("Readiness", status_filter("in-status")),
            filter_field("Injury filter", injury_filter_options("in-injury-filter")),
            filter_field("Date range", date_range_picker(DATA, "in-dates")),
        ]),
    ])


def layout():
    return html.Div([
        page_header(
            "Injury-Risk Patterns",
            ("Retrospective review of injury-labelled cases and the "
              "monitoring variables in the days before. This is descriptive, "
              "not predictive."),
        ),
        html.Div(className="danger-banner", children=[
            html.Strong("Very few injury cases. "),
            "This page supports case review and pattern exploration, not "
            "reliable injury prediction. Patterns shown here are hypotheses "
            "to test going forward — they do not prove causation and may "
            "not generalise to other players or seasons.",
        ]),
        _filters(),
        html.Div(id="in-kpis"),
        html.Div(id="in-insight"),

        section_bar("Injury timeline"),
        html.Div(id="in-timeline-card"),

        section_bar("Injured vs non-injured distributions"),
        html.Div(className="grid-2", children=[
            html.Div(id="in-box-acwr-card"),
            html.Div(id="in-box-fat-card"),
        ]),
        html.Div(className="grid-2", children=[
            html.Div(id="in-box-load-card"),
            html.Div(id="in-box-hrv-card"),
        ]),

        section_bar("Case-by-case review"),
        html.Div(id="in-case-cards"),

        section_bar("Variable correlations"),
        html.Div(id="in-corr-card"),
    ])


def register_callbacks(app):

    @app.callback(
        Output("in-kpis", "children"),
        Output("in-insight", "children"),
        Output("in-timeline-card", "children"),
        Output("in-box-acwr-card", "children"),
        Output("in-box-fat-card", "children"),
        Output("in-box-load-card", "children"),
        Output("in-box-hrv-card", "children"),
        Output("in-case-cards", "children"),
        Output("in-corr-card", "children"),
        Input("in-players", "value"),
        Input("in-positions", "value"),
        Input("in-status", "value"),
        Input("in-injury-filter", "value"),
        Input("in-dates", "start_date"),
        Input("in-dates", "end_date"),
    )
    def _update(players, positions, statuses, injury_filter, start_date, end_date):
        df = apply_filters(DATA, players=players, positions=positions, statuses=statuses, injury_filter=injury_filter,
                            start_date=start_date, end_date=end_date)

        if df.empty:
            return (empty_state(), None, empty_state(), empty_state(),
                    empty_state(), empty_state(), empty_state(),
                    empty_state(), empty_state())

        n_inj = int(df["Injury_Label"].sum())
        n_total = len(df)
        rate = n_inj / max(n_total, 1) * 100

        kpis = kpi_strip([
            kpi("Sessions",     f"{n_total:,}"),
            kpi("Injuries",     n_inj, sub=f"{rate:.2f}% of sessions",
                 tone="bad" if n_inj > 0 else "ok"),
            kpi("Players hit",  df[df["Injury_Label"] == 1]["Player"].nunique(),
                 tone="warn" if n_inj > 0 else "info"),
            kpi("Positions hit", df[df["Injury_Label"] == 1]["Position"].nunique(),
                 tone="info"),
        ])

        ins = generate_injury_pattern_insight(df)
        insight = html.Div(className=f"insight-box {ins['level']}",
                            style={"marginBottom": "16px"}, children=[
            html.Div(className="insight-headline", children=[
                html.Span("Pattern insight", className="ins-tag"),
                html.Span(ins["headline"]),
            ]),
            html.Div(ins["detail"], className="insight-detail"),
            html.Div(ins["coaching"], className="insight-coaching"),
            html.Div(ins["caution"], className="insight-caution"),
        ])

        # Timeline
        inj_df = df[df["Injury_Label"] == 1]
        if inj_df.empty:
            timeline_card = chart_card("Injury timeline",
                                          "No injury-labelled rows in current selection. This page can still show non-injury monitoring patterns.",
                                          empty_fig("No injury-labelled rows in current selection."))
        else:
            f_tl = go.Figure()
            f_tl.add_trace(go.Scatter(
                x=inj_df["Date"], y=inj_df["Player"],
                mode="markers", marker=dict(symbol="x", size=14,
                                              color=COLORS["danger"],
                                              line=dict(width=1, color="#fff")),
                hovertemplate="%{y} · %{x|%b %d}<extra></extra>",
            ))
            f_tl.update_xaxes(title=""); f_tl.update_yaxes(title="")
            f_tl = apply_layout(f_tl, height=280, showlegend=False)
            timeline_card = chart_card(
                "Injury timeline", f"{n_inj} injury day(s) in window.",
                dcc.Graph(figure=f_tl, config={"displaylogo": False}),
            )

        # Box plots — injured vs non-injured
        df["Injured"] = df["Injury_Label"].map({1: "Injured", 0: "Non-injured"})
        def _box(col, label):
            sub = df.dropna(subset=[col])
            if sub.empty or sub["Injured"].nunique() < 2:
                return chart_card(label, "Not enough data to compare.",
                                    empty_fig("Insufficient cases for comparison."))
            f = px.box(sub, x="Injured", y=col, color="Injured",
                        color_discrete_map={"Injured": COLORS["danger"],
                                              "Non-injured": COLORS["accent"]},
                        points="outliers")
            f.update_traces(marker=dict(size=4), line=dict(width=1.5))
            f.update_xaxes(title="")
            f.update_yaxes(title=VARIABLE_LABELS.get(col, col))
            f = apply_layout(f, height=320, showlegend=False)
            return chart_card(label,
                                f"Distribution of {VARIABLE_LABELS.get(col, col)} "
                                "across injured vs non-injured days.",
                                dcc.Graph(figure=f, config={"displaylogo": False}))
        acwr_box = _box("ACWR", "ACWR")
        fat_box  = _box("Fatigue_Score", "Fatigue")
        load_box = _box("Session_Load", "Session Load")
        hrv_box  = _box("HRV_RMSSD", "HRV RMSSD")

        # Case review cards
        if inj_df.empty:
            case_cards = html.Div("No injury cases in the current window.",
                                    className="muted",
                                    style={"padding": "20px", "textAlign": "center"})
        else:
            cards = []
            for _, r in inj_df.iterrows():
                cards.append(_case_card(r))
            case_cards = html.Div(cards, className="grid-2")

        # Correlation heatmap
        corr_cols = ["Total_Distance", "HSR", "Sprint_Distance",
                       "Session_Load", "ACWR", "Fatigue_Score",
                       "Soreness_Score", "Sleep_Quality",
                       "HRV_RMSSD", "CMJ_Height", "Injury_Label"]
        avail = [c for c in corr_cols if c in df.columns]
        if len(avail) < 4:
            corr_card = empty_state("Not enough variables for correlation matrix.")
        else:
            f_corr = heatmap_correlation(df.dropna(subset=avail), avail, height=460)
            corr_card = chart_card(
                "Correlation matrix",
                "Pearson correlation between monitoring variables and "
                "injury label. With few positive cases, the injury-label row "
                "is unreliable — read it cautiously.",
                dcc.Graph(figure=f_corr, config={"displaylogo": False}),
            )

        return (kpis, insight, timeline_card,
                acwr_box, fat_box, load_box, hrv_box,
                case_cards, corr_card)


def _case_card(r: pd.Series):
    player = r["Player"]
    injury_date = r["Date"]
    pre = DATA[(DATA["Player"] == player) &
                (DATA["Date"] >= injury_date - pd.Timedelta(days=7)) &
                (DATA["Date"] < injury_date)]

    warnings = []
    if not pre.empty:
        if (pre["ACWR"] > 1.5).any():
            warnings.append("ACWR spike (>1.5) in prior week")
        elif (pre["ACWR"] > 1.3).any():
            warnings.append("ACWR caution (>1.3) in prior week")
        if (pre["Fatigue_Score"] >= 4).any():
            warnings.append("High fatigue (≥4/5) in prior week")
        if (pre["Soreness_Score"] >= 4).any():
            warnings.append("High soreness (≥4/5) in prior week")
        if (pre["Sleep_Quality"] <= 2.5).any():
            warnings.append("Poor sleep (≤2.5/5) in prior week")
        if "CMJ_Height_PctChange" in pre.columns and (pre["CMJ_Height_PctChange"] <= -5).any():
            warnings.append("CMJ drop ≥ 5% vs baseline")
        if "HRV_RMSSD_PctChange" in pre.columns and (pre["HRV_RMSSD_PctChange"] <= -10).any():
            warnings.append("HRV drop ≥ 10% vs baseline")
    if not warnings:
        warnings.append("No flags triggered in the prior 7-day window.")

    metrics = [
        ("Position", r.get("Position", "-")),
        ("7-d total load", f"{pre['Session_Load'].sum():.0f} AU" if not pre.empty else "-"),
        ("7-d mean ACWR",  f"{pre['ACWR'].mean():.2f}" if not pre.empty else "-"),
        ("7-d mean fatigue", f"{pre['Fatigue_Score'].mean():.2f}/5" if not pre.empty else "-"),
        ("7-d mean soreness", f"{pre['Soreness_Score'].mean():.2f}/5" if not pre.empty else "-"),
        ("7-d mean sleep", f"{pre['Sleep_Quality'].mean():.2f}/5" if not pre.empty else "-"),
        ("7-d mean HRV", f"{pre['HRV_RMSSD'].mean():.1f} ms" if not pre.empty else "-"),
        ("7-d mean CMJ", f"{pre['CMJ_Height'].mean():.1f} cm" if not pre.empty else "-"),
    ]
    metric_rows = []
    for lbl, val in metrics:
        metric_rows.append(html.Div(style={
            "display": "flex", "justifyContent": "space-between",
            "padding": "5px 0", "borderBottom": "1px dashed " + COLORS["border"],
            "fontSize": "12px",
        }, children=[
            html.Span(lbl, className="dim"),
            html.Strong(val),
        ]))

    return html.Div(className="card-pf", children=[
        html.Div(className="card-head", children=[
            html.Div([
                html.H4(f"{player} — injury on {injury_date.strftime('%b %d, %Y')}",
                          className="card-title"),
                html.Div(f"Last readiness status before injury: {r.get('Readiness_Status', '-')}",
                          className="card-subtitle"),
            ]),
            traffic_badge(r.get("Readiness_Status", "Green")),
        ]),
        html.Div(metric_rows, style={"marginBottom": "12px"}),
        html.Div([
            html.Div("Warning signs in the prior 7 days:",
                      style={"fontSize": "11px",
                              "textTransform": "uppercase",
                              "letterSpacing": "1px",
                              "color": COLORS["text_muted"],
                              "marginBottom": "6px",
                              "fontWeight": "700"}),
            html.Ul([html.Li(w, style={"fontSize": "12px",
                                          "color": COLORS["text_soft"],
                                          "marginBottom": "2px"})
                       for w in warnings],
                     style={"margin": 0, "paddingLeft": "20px"}),
        ]),
        html.Div("Descriptive review only — does not prove causation.",
                  className="insight-caution",
                  style={"marginTop": "10px"}),
    ])
