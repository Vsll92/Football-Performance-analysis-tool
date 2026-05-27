"""
10) Machine Learning page — exploratory injury classifier.
"""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import dcc, html, Input, Output, State, dash_table

from src.config import COLORS, VARIABLE_LABELS
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
    filter_field, empty_state, apply_filters, position_dropdown, status_filter, date_range_picker,
)
from src.visuals import apply_layout, empty_fig, TABLE_STYLE
from src.ml_model import train_injury_model


DATA: pd.DataFrame = None


FEATURE_OPTIONS = [
    "Total_Distance", "HSR", "Sprint_Distance",
    "Accelerations", "Decelerations", "RPE",
    "Session_Load", "Acute_Load", "Chronic_Load", "ACWR",
    "Fatigue_Score", "Soreness_Score", "Sleep_Quality",
    "HRV_RMSSD", "Resting_HR", "CMJ_Height",
    "CMJ_Height_PctChange", "HRV_RMSSD_PctChange",
]


def _controls():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-3", children=[
            filter_field("Model",
                dcc.Dropdown(id="ml-model",
                    options=[{"label": "Logistic Regression", "value": "Logistic Regression"},
                              {"label": "Decision Tree",       "value": "Decision Tree"},
                              {"label": "Random Forest",       "value": "Random Forest"}],
                    value="Logistic Regression", clearable=False,
                    className="dash-dropdown")),
            filter_field("Oversample minority class",
                dcc.RadioItems(id="ml-os",
                    options=[{"label": "Yes (SMOTE-like)", "value": "yes"},
                              {"label": "No",                "value": "no"}],
                    value="no", className="radio-row")),
            filter_field("Random seed",
                dcc.Dropdown(id="ml-seed",
                    options=[{"label": str(s), "value": s}
                              for s in [0, 7, 17, 42, 100]],
                    value=42, clearable=False, className="dash-dropdown")),
        ]),
        html.Div(style={"height": "10px"}),
        html.Div(className="grid-3", children=[
            filter_field("Date range", date_range_picker(DATA, "ml-dates")),
            filter_field("Positions", position_dropdown(DATA, "ml-positions")),
            filter_field("Readiness", status_filter("ml-status")),
        ]),
        html.Div(style={"height": "10px"}),
        html.Div(className="grid-2", children=[
            filter_field("Features",
                dcc.Dropdown(id="ml-features",
                    options=[{"label": VARIABLE_LABELS.get(f, f), "value": f}
                              for f in FEATURE_OPTIONS],
                    value=["Session_Load", "ACWR", "Fatigue_Score",
                            "HRV_RMSSD", "CMJ_Height_PctChange",
                            "Sleep_Quality", "Soreness_Score"],
                    multi=True, className="dash-dropdown")),
            filter_field("",
                html.Button("🚀  Train model", id="ml-go", n_clicks=0,
                              className="btn-primary",
                              style={"marginTop": "20px"})),
        ]),
    ])


def layout():
    return html.Div([
        page_header("Machine Learning — Exploratory",
                      ("Train a simple classifier on monitoring variables "
                        "to identify which features track with injury label. "
                        "Treat this as exploratory only.")),
        html.Div(className="danger-banner", children=[
            html.Strong("Exploratory only. "),
            "Injury cases are extremely rare in this dataset (≈0.1% of "
            "sessions). Any model trained here cannot predict injuries "
            "reliably — it is useful only for understanding which monitoring "
            "variables co-vary with injury days. Do not use these outputs as "
            "diagnostic or selection criteria. Do not overclaim what the "
            "ROC-AUC means with this class balance.",
        ]),
        _controls(),
        html.Div(id="ml-kpis"),
        html.Div(id="ml-interpretation"),

        section_bar("Confusion matrix & ROC"),
        html.Div(className="grid-2", children=[
            html.Div(id="ml-cm-card"),
            html.Div(id="ml-roc-card"),
        ]),

        section_bar("Classification report"),
        html.Div(id="ml-report-card"),

        section_bar("Feature importance"),
        html.Div(id="ml-feat-card"),
    ])


def register_callbacks(app):

    @app.callback(
        Output("ml-kpis", "children"),
        Output("ml-interpretation", "children"),
        Output("ml-cm-card", "children"),
        Output("ml-roc-card", "children"),
        Output("ml-report-card", "children"),
        Output("ml-feat-card", "children"),
        Input("ml-go", "n_clicks"),
        State("ml-model", "value"),
        State("ml-os", "value"),
        State("ml-seed", "value"),
        State("ml-features", "value"),
        State("ml-dates", "start_date"),
        State("ml-dates", "end_date"),
        State("ml-positions", "value"),
        State("ml-status", "value"),
    )
    def _go(n, model_name, oversample, seed, features, start_date, end_date, positions, statuses):
        if n == 0:
            hint = html.Div("Choose your features and click Train model above.",
                              className="muted",
                              style={"padding": "20px", "textAlign": "center"})
            return hint, None, hint, hint, hint, hint

        features = [f for f in (features or []) if f in DATA.columns]
        if not features:
            err = html.Div("Select at least one valid feature to train on.",
                            className="muted",
                            style={"padding": "20px", "textAlign": "center"})
            return err, None, err, err, err, err

        df_model = apply_filters(DATA, positions=positions, statuses=statuses, start_date=start_date, end_date=end_date)
        result = train_injury_model(
            df_model, features=features, model_name=model_name,
            oversample=(oversample == "yes"), random_state=seed,
        )

        if result.get("status") != "ok":
            err = html.Div(
                f"Could not train model: {result.get('message', 'unknown error')}",
                className="muted",
                style={"padding": "20px", "textAlign": "center"})
            return err, None, err, err, err, err

        # Compute macro F1 / recall from sklearn-style report dict
        rep = result["report"]
        macro_f1 = rep.get("macro avg", {}).get("f1-score", 0.0)
        macro_recall = rep.get("macro avg", {}).get("recall", 0.0)
        roc_auc = result.get("roc_auc")

        # KPIs
        kpis = kpi_strip([
            kpi("Model",         model_name, tone="info"),
            kpi("Filtered rows", result.get("n_rows", 0)),
            kpi("Injury cases",  result.get("n_injuries", 0), tone="bad" if result.get("n_injuries", 0) else "ok"),
            kpi("Prevalence",    f"{result.get('injury_prevalence', 0):.2f}%"),
            kpi("Train rows",    result["n_train"]),
            kpi("Test positives", result.get("n_pos_test", 0), tone="bad" if result.get("n_pos_test", 0) < 5 else "info"),
            kpi("Macro F1",      f"{macro_f1:.3f}",  tone="info"),
            kpi("Macro Recall",  f"{macro_recall:.3f}", tone="info"),
            kpi("ROC AUC",       f"{roc_auc:.3f}" if roc_auc is not None else "—",
                 tone="info",
                 sub="Inflated by class imbalance"),
        ])

        # Interpretation
        feat_imp_series = result.get("feature_importance")
        top3 = list(feat_imp_series.head(3).index) if feat_imp_series is not None else []
        top_str = ", ".join(top3) if top3 else "—"
        interpretation = html.Div(className="insight-box warning",
                                    style={"marginBottom": "16px"}, children=[
            html.Div(className="insight-headline", children=[
                html.Span("How to read this", className="ins-tag"),
                html.Span(
                    f"The model picked up signal from: {top_str}."),
            ]),
            html.Div(("These are the features the algorithm leaned on most. "
                        "Monitor these daily on the dashboard, even outside the "
                        "model context."),
                       className="insight-detail"),
            html.Div(("Use the model to confirm the variables already in your "
                        "monitoring routine, not to predict who will get "
                        "injured. With <0.2% positive class, predictions are "
                        "not actionable — the per-class recall for the "
                        "minority class is what to scrutinise, not overall "
                        "accuracy or ROC."),
                       className="insight-coaching"),
            html.Div(("Class imbalance inflates every standard metric. "
                        "Treat any ROC-AUC reading as descriptive — the model "
                        "may be picking up label-correlated noise that won't "
                        "transfer to next season."),
                       className="insight-caution"),
        ])

        # Confusion matrix
        cm = result["confusion_matrix"]  # numpy 2x2
        f_cm = go.Figure(data=go.Heatmap(
            z=cm,
            x=["Pred: Non-injured", "Pred: Injured"],
            y=["Actual: Non-injured", "Actual: Injured"],
            colorscale="Blues",
            text=cm, texttemplate="%{text}",
            textfont=dict(size=18, color="white"),
            colorbar=dict(thickness=10),
        ))
        f_cm = apply_layout(f_cm, height=360, showlegend=False)
        cm_card = chart_card("Confusion matrix",
                                "Rows = actual, columns = predicted.",
                                dcc.Graph(figure=f_cm,
                                            config={"displaylogo": False}))

        # ROC
        fpr = result.get("fpr")
        tpr = result.get("tpr")
        if fpr is not None and tpr is not None:
            f_roc = go.Figure()
            f_roc.add_trace(go.Scatter(x=fpr, y=tpr,
                                          mode="lines",
                                          line=dict(color=COLORS["accent"], width=2.5),
                                          name="ROC"))
            f_roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1],
                                          mode="lines",
                                          line=dict(color=COLORS["text_muted"],
                                                      width=1, dash="dash"),
                                          name="Chance"))
            f_roc.update_xaxes(title="False Positive Rate", range=[0, 1])
            f_roc.update_yaxes(title="True Positive Rate", range=[0, 1])
            f_roc = apply_layout(f_roc, height=360)
            roc_card = chart_card(
                f"ROC curve (AUC = {roc_auc:.3f})" if roc_auc is not None else "ROC curve",
                "Interpret with extreme caution given the class imbalance.",
                dcc.Graph(figure=f_roc, config={"displaylogo": False}),
            )
        else:
            roc_card = chart_card("ROC curve",
                                    "Could not compute — see notes above.",
                                    empty_fig())

        # Classification report
        report = pd.DataFrame(result["report"]).T.round(3)
        report = report.reset_index().rename(columns={"index": "Class"})
        report_card = chart_card(
            "Per-class precision / recall / F1",
            "Focus on the 'Injured' row — the minority class — when "
            "interpreting performance.",
            dash_table.DataTable(
                data=report.to_dict("records"),
                columns=[{"name": c, "id": c} for c in report.columns],
                **TABLE_STYLE,
            ),
        )

        # Feature importance
        if feat_imp_series is not None and not feat_imp_series.empty:
            fi_df = (feat_imp_series.reset_index()
                      .rename(columns={"index": "Feature", 0: "Importance"}))
            fi_df.columns = ["Feature", "Importance"]
            fi_df = fi_df.sort_values("Importance")
            f_fi = px.bar(fi_df, x="Importance", y="Feature", orientation="h",
                            color="Importance", color_continuous_scale="Blues")
            f_fi.update_traces(marker_line_width=0)
            f_fi.update_xaxes(title="Relative importance")
            f_fi.update_yaxes(title="")
            f_fi = apply_layout(f_fi, height=max(360, 28 * len(fi_df)),
                                  showlegend=False)
            f_fi.update_coloraxes(showscale=False)
            feat_card = chart_card(
                "Feature importance",
                "Higher = the model used this variable more heavily.",
                dcc.Graph(figure=f_fi, config={"displaylogo": False}),
            )
        else:
            feat_card = chart_card("Feature importance",
                                      "Not available for the chosen model.",
                                      empty_fig())

        return (kpis, interpretation, cm_card, roc_card, report_card, feat_card)
