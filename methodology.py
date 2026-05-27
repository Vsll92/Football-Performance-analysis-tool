"""
11) Methodology & Data Quality page.
"""
from __future__ import annotations

import pandas as pd
from dash import dcc, html, dash_table

from src.config import (
    COLORS, READINESS_RULES, READINESS_STATUS_THRESHOLDS, ACWR_ZONES,
)
from src.layout import (
    page_header, section_bar, kpi, kpi_strip, chart_card,
)
from src.visuals import TABLE_STYLE
from src.preprocessing import data_quality_report


DATA: pd.DataFrame = None


def _column_note(col: str) -> str:
    notes = {
        "Date": "Daily session date",
        "Player": "Anonymised player ID (Player_01 .. Player_30)",
        "Position": "Tactical role (Winger / CB / FB / AM / CM / DM)",
        "Total_Distance": "Total distance covered (m), GPS-derived",
        "HSR": "High-speed running (m), GPS-derived (typ. > 19.8 km/h)",
        "Sprint_Distance": "Sprint distance (m), GPS-derived (typ. > 25.2 km/h)",
        "Accelerations": "Accelerations count above intensity threshold",
        "Decelerations": "Decelerations count above intensity threshold",
        "RPE": "Self-reported Rating of Perceived Exertion (0–10)",
        "Session_Load": "sRPE = RPE × duration (AU)",
        "Acute_Load": "7-day rolling sum of Session_Load",
        "Chronic_Load": "28-day rolling sum of Session_Load",
        "ACWR": "Acute / Chronic workload ratio (provided)",
        "Acute_Load_Calc": "Recomputed 7-day rolling sum (derived)",
        "Chronic_Load_Calc": "Recomputed 28-day rolling sum (derived)",
        "ACWR_Calc": "Recomputed ACWR (derived)",
        "HRV_RMSSD": "Heart-rate variability (ms), morning measurement",
        "Resting_HR": "Resting heart rate (bpm), morning measurement",
        "CMJ_Height": "Countermovement jump height (cm)",
        "Fatigue_Score": "Self-reported fatigue (1–5; high = worse)",
        "Soreness_Score": "Self-reported soreness (1–5; high = worse)",
        "Sleep_Quality": "Self-reported sleep quality (1–5; high = better)",
        "Injury_Label": "Binary: 1 = injury day, 0 = otherwise (provided)",
        "Readiness_Score": "Sum of triggered readiness flags (derived)",
        "Readiness_Status": "Green / Yellow / Red bucket (derived)",
    }
    return notes.get(col, "—")


def layout():
    dq = data_quality_report(DATA)

    # --- KPI strip ---
    kpi_block = kpi_strip([
        kpi("Players",   dq["n_players"]),
        kpi("Positions", dq["n_positions"]),
        kpi("Sessions",  f"{dq['n_rows']:,}"),
        kpi("Window",    f"{dq['date_start']} → {dq['date_end']}"),
        kpi("Injuries",  dq["n_injuries"],
             sub=f"{dq['injury_rate']:.2f}% of sessions",
             tone="bad" if dq["n_injuries"] > 0 else "ok"),
        kpi("Missing values", f"{dq['missing_total']:,}", tone="info"),
        kpi("Derived columns", dq["n_derived"], tone="info"),
    ])

    # --- Class imbalance callout ---
    imbalance_callout = html.Div(className="danger-banner", children=[
        html.Strong("⚠ Severe class imbalance. "),
        f"Only {dq['n_injuries']} session(s) are labelled as injuries "
        f"out of {dq['n_rows']:,} ({dq['injury_rate']:.2f}%). This makes "
        "any predictive modelling unreliable. The dashboard treats injury "
        "modelling as exploratory only — it surfaces variables that co-vary "
        "with injury days but does not predict who will be injured.",
    ])

    # --- Variable inventory ---
    inventory_rows = []
    for col in DATA.columns:
        inventory_rows.append({
            "Column":   col,
            "Type":     str(DATA[col].dtype),
            "Missing":  int(DATA[col].isna().sum()),
            "Min":      f"{DATA[col].min():.2f}" if pd.api.types.is_numeric_dtype(DATA[col]) else "—",
            "Mean":     f"{DATA[col].mean():.2f}" if pd.api.types.is_numeric_dtype(DATA[col]) else "—",
            "Max":      f"{DATA[col].max():.2f}" if pd.api.types.is_numeric_dtype(DATA[col]) else "—",
            "Notes":    _column_note(col),
        })
    inventory_card = chart_card(
        "Variable inventory",
        "Every column in the master dataframe — raw and derived.",
        dash_table.DataTable(
            data=inventory_rows,
            columns=[{"name": c, "id": c} for c in
                       ["Column", "Type", "Missing", "Min", "Mean", "Max", "Notes"]],
            page_size=15,
            filter_action="native",
            sort_action="native",
            **TABLE_STYLE,
        ),
    )

    # --- Injury distribution ---
    inj_by_player = DATA[DATA["Injury_Label"] == 1].groupby("Player").size()
    inj_by_pos    = DATA[DATA["Injury_Label"] == 1].groupby("Position").size()
    if inj_by_player.empty:
        inj_dist_card = chart_card("Injury distribution",
                                      "No injuries in this dataset.",
                                      html.Div("—"))
    else:
        rows = []
        for player, n in inj_by_player.items():
            rows.append({
                "Player": player,
                "Position": DATA[DATA["Player"] == player]["Position"].iloc[0],
                "Injuries": int(n),
                "Date(s)": ", ".join(
                    DATA[(DATA["Player"] == player) &
                          (DATA["Injury_Label"] == 1)]["Date"].dt
                          .strftime("%b %d").tolist()),
            })
        inj_dist_card = chart_card(
            "Injury distribution",
            "Each labelled injury session with player and date.",
            dash_table.DataTable(
                data=rows,
                columns=[{"name": c, "id": c} for c in
                          ["Player", "Position", "Injuries", "Date(s)"]],
                **TABLE_STYLE,
            ),
        )

    # --- Variables-by-family card ---
    families = {
        "External load":    "Total_Distance, HSR, Sprint_Distance, Accelerations, Decelerations",
        "Internal load":    "RPE, Session_Load, Acute_Load, Chronic_Load, ACWR",
        "Wellness":         "Fatigue_Score, Soreness_Score, Sleep_Quality",
        "Neuromuscular":    "CMJ_Height (and CMJ_Height_Baseline / _PctChange)",
        "Autonomic":        "HRV_RMSSD, Resting_HR (and *_Baseline / _PctChange)",
        "Label":            "Injury_Label (0 / 1)",
        "Derived (readiness)": "Readiness_Score, Readiness_Status, Flag_* booleans",
        "Derived (time)":   "Week, Week_Start, DayOfWeek, Month",
    }
    fam_rows = [{"Family": k, "Variables": v} for k, v in families.items()]
    family_card = chart_card(
        "Variables grouped by family",
        "How the dashboard organises its 30+ columns.",
        dash_table.DataTable(
            data=fam_rows,
            columns=[{"name": "Family", "id": "Family"},
                       {"name": "Variables", "id": "Variables"}],
            **TABLE_STYLE,
        ),
    )

    # --- Derived variables list ---
    derived_rows = [
        {"Variable": "Acute_Load_Calc",       "Definition": "7-day rolling SUM of Session_Load per player"},
        {"Variable": "Chronic_Load_Calc",     "Definition": "28-day rolling SUM of Session_Load per player"},
        {"Variable": "ACWR_Calc",             "Definition": "Acute_Load_Calc / Chronic_Load_Calc"},
        {"Variable": "CMJ_Height_Baseline",   "Definition": "Mean CMJ over first 14 sessions per player"},
        {"Variable": "HRV_RMSSD_Baseline",    "Definition": "Mean HRV over first 14 sessions per player"},
        {"Variable": "Resting_HR_Baseline",   "Definition": "Mean RHR over first 14 sessions per player"},
        {"Variable": "*_PctChange",           "Definition": "(value − baseline) / baseline × 100, signed"},
        {"Variable": "Fatigue_Score_RollMean7", "Definition": "7-day rolling MEAN of Fatigue_Score"},
        {"Variable": "Sleep_Quality_RollMean7", "Definition": "7-day rolling MEAN of Sleep_Quality"},
        {"Variable": "Soreness_Score_RollMean7", "Definition": "7-day rolling MEAN of Soreness_Score"},
        {"Variable": "ACWR_Zone",             "Definition": "Underload < 0.8 ≤ Optimal < 1.3 ≤ Caution < 1.5 ≤ High Spike"},
        {"Variable": "Flag_* (booleans)",     "Definition": "One per readiness rule (see Readiness scoring table)"},
        {"Variable": "Readiness_Score",       "Definition": "Sum of triggered Flag_* points (0–9)"},
        {"Variable": "Readiness_Status",      "Definition": "Green 0–1 / Yellow 2–3 / Red 4+"},
    ]
    derived_card = chart_card(
        "Derived variables",
        "Everything computed inside `src/metrics.py` and `src/readiness.py`.",
        dash_table.DataTable(
            data=derived_rows,
            columns=[{"name": "Variable", "id": "Variable"},
                       {"name": "Definition", "id": "Definition"}],
            **TABLE_STYLE,
        ),
    )

    # --- ACWR zones table ---
    acwr_rows = [
        {"Zone": "Underload",   "Range": "< 0.80",       "Interpretation": "Possible undertraining; monitor next session."},
        {"Zone": "Optimal",     "Range": "0.80 – 1.30",  "Interpretation": "Well-managed acute load."},
        {"Zone": "Caution",     "Range": "1.30 – 1.50",  "Interpretation": "Elevated acute load — monitor closely."},
        {"Zone": "High Spike",  "Range": "> 1.50",       "Interpretation": "Consider modifying training; recheck recovery."},
    ]
    acwr_card = chart_card(
        "ACWR monitoring zones",
        "Practical thresholds used across the dashboard — not universal medical rules.",
        dash_table.DataTable(
            data=acwr_rows,
            columns=[{"name": c, "id": c} for c in ["Zone", "Range", "Interpretation"]],
            **TABLE_STYLE,
        ),
    )

    # --- Readiness scoring table ---
    rules_rows = []
    for key, rule in READINESS_RULES.items():
        rules_rows.append({"Rule": key, "Threshold": rule.get("desc", ""),
                              "Points": rule["points"]})
    rules_card = chart_card(
        "Readiness scoring rules",
        "Each rule adds points if triggered. ACWR > 1.5 adds an EXTRA +1 on "
        "top of the > 1.3 rule, so a session above 1.5 contributes +2 in total.",
        dash_table.DataTable(
            data=rules_rows,
            columns=[{"name": c, "id": c} for c in ["Rule", "Threshold", "Points"]],
            **TABLE_STYLE,
        ),
    )

    # --- Status threshold ---
    status_rows = []
    for status, (lo, hi) in READINESS_STATUS_THRESHOLDS.items():
        status_rows.append({"Status": status,
                              "Score range": f"{lo} – {hi if hi < 99 else '∞'}",
                              "Coaching": {
                                  "Green":  "Cleared for normal training",
                                  "Yellow": "Modify intensity / monitor",
                                  "Red":    "Recovery-focused day; reduce HSR 24–48h",
                              }[status]})
    status_card = chart_card(
        "Status thresholds",
        "Mapping from readiness score to traffic-light status.",
        dash_table.DataTable(
            data=status_rows,
            columns=[{"name": c, "id": c} for c in ["Status", "Score range", "Coaching"]],
            **TABLE_STYLE,
        ),
    )

    # --- Known limitations ---
    limitations = html.Div(className="card-pf", children=[
        html.Div(className="card-head", children=[
            html.H4("Known limitations", className="card-title"),
        ]),
        html.Ul([
            html.Li("Very few injury cases (<0.2%) — predictive modelling is not reliable."),
            html.Li("Baselines are computed from the first 14 days per player; "
                    "any player who was already fatigued in that window has a biased baseline."),
            html.Li("ACWR thresholds (1.3, 1.5) are practical monitoring guides taken from applied sport science literature; "
                    "they are not universal medical rules and differ between studies."),
            html.Li("Subjective wellness (fatigue, soreness, sleep) varies by individual reporting style — "
                    "compare each player against their own history rather than absolute values."),
            html.Li("All GPS-derived metrics inherit the limitations of GPS measurement in stadiums and indoor pitches."),
            html.Li("This dashboard is a monitoring SUPPORT tool — it does not diagnose, predict, or "
                    "replace the medical and coaching teams' judgement."),
        ], className="dim", style={"fontSize": "13px", "lineHeight": "1.7"}),
    ])

    # --- What this can / cannot do ---
    can_cannot = html.Div(className="grid-2", children=[
        html.Div(className="card-pf", children=[
            html.H4("What this dashboard CAN do", className="card-title",
                      style={"color": COLORS["success"]}),
            html.Ul([
                html.Li("Surface which players are accumulating load."),
                html.Li("Flag readiness drops vs each player's own baseline."),
                html.Li("Combine workload, wellness, and neuro/autonomic markers in one view."),
                html.Li("Provide a structured coach briefing automatically."),
                html.Li("Provide retrospective case review of injury events."),
            ], className="dim", style={"fontSize": "13px"}),
        ]),
        html.Div(className="card-pf", children=[
            html.H4("What this dashboard CANNOT do", className="card-title",
                      style={"color": COLORS["danger"]}),
            html.Ul([
                html.Li("Predict injuries reliably (class imbalance is too severe)."),
                html.Li("Diagnose any medical condition."),
                html.Li("Replace clinical judgement on return-to-play."),
                html.Li("Prove causality between any monitoring variable and outcome."),
                html.Li("Account for game-day load, travel fatigue, or context not in the dataset."),
            ], className="dim", style={"fontSize": "13px"}),
        ]),
    ])

    return html.Div([
        page_header("Methodology & Data Quality",
                      ("The academic backbone behind the dashboard: dataset "
                        "structure, derived variables, scoring logic, and the "
                        "boundaries of what we can and cannot conclude.")),
        kpi_block,
        imbalance_callout,

        section_bar("Dataset"),
        inventory_card,
        html.Div(className="grid-2", children=[inj_dist_card, family_card]),

        section_bar("Derived variables & scoring"),
        derived_card,
        html.Div(className="grid-2", children=[acwr_card, rules_card]),
        status_card,

        section_bar("Boundaries of the analysis"),
        can_cannot,
        limitations,

        html.Div(className="note-banner",
                  style={"marginTop": "16px"}, children=[
            html.Strong("Communicating these outputs — "),
            "When presenting findings to coaches, lead with what the data "
            "shows ('X has elevated ACWR for three consecutive days'), "
            "then translate to action ('recommend recovery-focused session'), "
            "and finally add the caveat ('this is a monitoring flag, not a "
            "medical diagnosis'). That sequence builds trust without "
            "overclaiming.",
        ]),
    ])


def register_callbacks(app):
    pass
