"""
Configuration module — central place for constants, colours, thresholds.
Edit values here to re-skin or re-tune the whole dashboard.
"""
from pathlib import Path

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw" / "sports_analytics_master_datasets.xlsx"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = ROOT_DIR / "reports"

# -----------------------------------------------------------------------------
# Brand / Theme — modern dark "performance lab" palette (matches style.css)
# -----------------------------------------------------------------------------
COLORS = {
    "bg":            "#0A0E14",
    "bg_2":          "#0F141C",
    "panel":         "#141B26",
    "panel_light":   "#1B2330",
    "panel_3":       "#232C3B",
    "border":        "#2A3548",
    "text":          "#E8EDF5",
    "text_muted":    "#6F7C92",
    "text_soft":     "#B8C2D2",
    "accent":        "#4F8CFF",
    "accent_2":      "#22D3EE",
    "success":       "#34D399",
    "warning":       "#F59E0B",
    "danger":        "#F87171",
    "purple":        "#A78BFA",
    "pink":          "#F472B6",
}

# Traffic-light readiness palette
READINESS_COLORS = {
    "Green":  COLORS["success"],
    "Yellow": COLORS["warning"],
    "Red":    COLORS["danger"],
}

# Position colours (consistent across pages)
POSITION_COLORS = {
    "Winger": "#4F8CFF",
    "CB":     "#22D3EE",
    "FB":     "#A78BFA",
    "AM":     "#F59E0B",
    "CM":     "#34D399",
    "DM":     "#F472B6",
}

# -----------------------------------------------------------------------------
# Monitoring thresholds  (practical guides, NOT medical rules)
# -----------------------------------------------------------------------------
ACWR_ZONES = {
    "underload":      (0.0, 0.8),
    "optimal":        (0.8, 1.3),
    "caution":        (1.3, 1.5),
    "high_spike":     (1.5, 99.0),
}

ACWR_ZONE_COLORS = {
    "Underload":  COLORS["accent_2"],
    "Optimal":    COLORS["success"],
    "Caution":    COLORS["warning"],
    "High Spike": COLORS["danger"],
}

# -----------------------------------------------------------------------------
# Readiness scoring rules  (interpretation: an `acwr_very_high` ROW *replaces*
# `acwr_high` by adding an EXTRA +1, so net total is +2 for ACWR > 1.5.
# This matches the spec: "ACWR > 1.3 → +1, ACWR > 1.5 → +2 (total)".)
# -----------------------------------------------------------------------------
READINESS_RULES = {
    "acwr_high":          {"threshold": 1.3, "points": 1,
                            "desc": "ACWR > 1.3 (caution zone)"},
    "acwr_very_high":     {"threshold": 1.5, "points": 1,
                            "desc": "ACWR > 1.5 (extra +1 → net +2 with caution)"},
    "fatigue_high":       {"threshold": 4.0, "points": 1,
                            "desc": "Fatigue ≥ 4 / 5"},
    "soreness_high":      {"threshold": 4.0, "points": 1,
                            "desc": "Soreness ≥ 4 / 5"},
    "sleep_low":          {"threshold": 2.5, "points": 1,
                            "desc": "Sleep ≤ 2.5 / 5"},
    "hrv_drop":           {"threshold": 0.10, "points": 1,
                            "desc": "HRV ≥ 10% below player baseline"},
    "cmj_drop":           {"threshold": 0.05, "points": 1,
                            "desc": "CMJ ≥ 5% below player baseline"},
    "rhr_up":             {"threshold": 0.05, "points": 1,
                            "desc": "Resting HR ≥ 5% above player baseline"},
}

READINESS_STATUS_THRESHOLDS = {
    "Green":  (0, 1),   # 0–1 points
    "Yellow": (2, 3),   # 2–3 points
    "Red":    (4, 99),  # 4+ points
}

# -----------------------------------------------------------------------------
# Plotly default layout
# -----------------------------------------------------------------------------
PLOTLY_LAYOUT = dict(
    paper_bgcolor=COLORS["panel"],
    plot_bgcolor=COLORS["panel"],
    font=dict(family="Inter, system-ui, -apple-system, sans-serif",
              color=COLORS["text"], size=12),
    margin=dict(l=52, r=20, t=30, b=40),
    hoverlabel=dict(bgcolor=COLORS["panel_light"],
                    bordercolor=COLORS["border"],
                    font_color=COLORS["text"]),
    xaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
    yaxis=dict(gridcolor=COLORS["border"], zerolinecolor=COLORS["border"]),
    legend=dict(bgcolor="rgba(0,0,0,0)", bordercolor=COLORS["border"],
                font=dict(size=11)),
)

# -----------------------------------------------------------------------------
# Variable groups
# -----------------------------------------------------------------------------
EXTERNAL_LOAD_VARS = [
    "Total_Distance", "HSR", "Sprint_Distance", "Accelerations", "Decelerations",
]
INTERNAL_LOAD_VARS = [
    "RPE", "Session_Load", "Acute_Load", "Chronic_Load", "ACWR",
    "ACWR_Calc", "Acute_Load_Avg_7", "Chronic_Load_Avg_28",
]
WELLNESS_VARS = [
    "Fatigue_Score", "Soreness_Score", "Sleep_Quality",
]
NEURO_VARS = [
    "CMJ_Height", "HRV_RMSSD", "Resting_HR",
]
ALL_METRICS = EXTERNAL_LOAD_VARS + INTERNAL_LOAD_VARS + WELLNESS_VARS + NEURO_VARS

VARIABLE_LABELS = {
    "Total_Distance":  "Total Distance (m)",
    "HSR":             "High-Speed Running (m)",
    "Sprint_Distance": "Sprint Distance (m)",
    "Accelerations":   "Accelerations (n)",
    "Decelerations":   "Decelerations (n)",
    "RPE":             "RPE (0–10)",
    "Session_Load":    "Session Load (AU)",
    "Acute_Load":      "Acute Load (7-day)",
    "Chronic_Load":    "Chronic Load (28-day)",
    "ACWR":            "Dataset ACWR",
    "ACWR_Calc":       "Calculated ACWR (7d avg / 28d avg)",
    "Acute_Load_Avg_7": "Acute Load Avg (7d)",
    "Chronic_Load_Avg_28": "Chronic Load Avg (28d)",
    "HRV_RMSSD":       "HRV RMSSD (ms)",
    "Resting_HR":      "Resting HR (bpm)",
    "Fatigue_Score":   "Fatigue (1–5)",
    "Soreness_Score":  "Soreness (1–5)",
    "Sleep_Quality":   "Sleep Quality (1–5)",
    "CMJ_Height":      "CMJ Height (cm)",
    "Readiness_Score": "Readiness Score",
    "High_Intensity_Exposure": "High-Intensity Exposure Proxy",
    "Mechanical_Load_Proxy": "Mechanical Load Proxy",
    "Wellness_Stress_Proxy": "Wellness Stress Proxy",
    "Recovery_Risk_Composite": "Recovery Risk Composite",
}

# Whether higher value = "worse"
HIGHER_IS_WORSE = {
    "Fatigue_Score":  True,
    "Soreness_Score": True,
    "RPE":            True,
    "Resting_HR":     True,
    "ACWR":           True,
    "Sleep_Quality":  False,
    "HRV_RMSSD":      False,
    "CMJ_Height":     False,
}
