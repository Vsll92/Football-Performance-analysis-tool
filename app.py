"""
Football Performance & Injury-Risk Dashboard — v2 (Professional)
=================================================================

Entry point: `python app.py`  → http://127.0.0.1:8050

Architecture
------------
- src/data_loader.py     read Excel
- src/metrics.py         derive ACWR, baselines, % change, flags
- src/readiness.py       readiness score + traffic-light status
- src/preprocessing.py   end-to-end pipeline (`build_master_dataframe`)
- src/visuals.py         Plotly chart factories
- src/insights.py        data-driven insight generators
- src/layout.py          shared Dash components (header, kpi, chart_card)
- src/ml_model.py        exploratory injury-risk classifier
- src/report.py          markdown coach report

- pages/                 one module per page (layout + register_callbacks)
- assets/style.css       theme (Performance Lab dark)
"""
from __future__ import annotations

from datetime import date as date_cls

import dash
from dash import Dash, dcc, html, Input, Output, ALL
import dash_bootstrap_components as dbc

from src.preprocessing import build_master_dataframe

from pages import (
    overview, workload, acwr_page, fatigue, cmj_hrv,
    injury, player_profile, position_page, comparison,
    ml_page, coach_report, methodology,
)


# =============================================================================
# 1. Master DataFrame
# =============================================================================
DATA = build_master_dataframe()

# Inject DATA into every page module
for module in (overview, workload, acwr_page, fatigue, cmj_hrv,
                injury, player_profile, position_page, comparison,
                ml_page, coach_report, methodology):
    module.DATA = DATA


# =============================================================================
# 2. Dash init
# =============================================================================
app = Dash(
    __name__,
    external_stylesheets=[
        "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap",
        dbc.themes.BOOTSTRAP,
    ],
    suppress_callback_exceptions=True,
    title="Football Performance Lab",
    update_title=None,
)
server = app.server


# =============================================================================
# 3. Routing config
# =============================================================================
NAV_ITEMS = [
    ("Monitoring", [
        ("/",                  "📊", "Executive Overview"),
        ("/workload",          "🏃", "Workload Monitoring"),
        ("/acwr",              "⚖️", "ACWR & Spikes"),
        ("/fatigue",           "😴", "Fatigue & Wellness"),
        ("/cmj-hrv",           "💓", "CMJ & HRV"),
    ]),
    ("Risk & Analysis", [
        ("/injury",            "🚑", "Injury Patterns"),
        ("/ml",                "🤖", "Machine Learning"),
    ]),
    ("Drill-down", [
        ("/player",            "👤", "Player Profile"),
        ("/position",          "🧭", "Position Comparison"),
        ("/comparison",        "🔀", "Comparison Lab"),
    ]),
    ("Communication", [
        ("/coach-report",      "📝", "Coach Report"),
        ("/methodology",       "📚", "Methodology"),
    ]),
]

PATH_LABEL = {p: lbl for _, items in NAV_ITEMS for p, _, lbl in items}

PAGES = {
    "/":              overview,
    "/workload":      workload,
    "/acwr":          acwr_page,
    "/fatigue":       fatigue,
    "/cmj-hrv":       cmj_hrv,
    "/injury":        injury,
    "/player":        player_profile,
    "/position":      position_page,
    "/comparison":    comparison,
    "/ml":            ml_page,
    "/coach-report":  coach_report,
    "/methodology":   methodology,
}


# =============================================================================
# 4. Sidebar
# =============================================================================
def sidebar():
    sections = []
    for title, links in NAV_ITEMS:
        sections.append(html.Div(title, className="nav-section-title"))
        for href, icon, label in links:
            sections.append(dcc.Link(
                children=[html.Span(icon, className="nav-icon"),
                            html.Span(label)],
                href=href,
                className="nav-link",
                id={"type": "nav-link", "href": href},
            ))
    return html.Div(className="sidebar", children=[
        html.Div(className="brand", children=[
            html.Div("⚽", className="brand-mark"),
            html.Div([
                html.Div("Performance Lab", className="brand-title"),
                html.Div("Football Analytics", className="brand-sub"),
            ]),
        ]),
        *sections,
        html.Div(style={"height": "20px"}),
        html.Div("v2 · Master in Sports Analytics", className="muted",
                  style={"padding": "8px 12px", "fontSize": "10px"}),
    ])


# =============================================================================
# 5. Topbar
# =============================================================================
def topbar():
    dr = f"{DATA['Date'].min().strftime('%b %d')} – {DATA['Date'].max().strftime('%b %d, %Y')}"
    return html.Div(className="topbar", children=[
        html.Div(className="crumb", children=[
            html.Span("Performance Lab"),
            html.Span("›", className="crumb-sep"),
            html.Span(id="crumb-current", className="crumb-current"),
        ]),
        html.Div(className="topbar-meta", children=[
            html.Span(f"📅 {dr}", className="pill"),
            html.Span(f"👥 {DATA['Player'].nunique()} players", className="pill"),
            html.Span(f"📈 {len(DATA):,} sessions", className="pill"),
        ]),
    ])


# =============================================================================
# 6. App layout
# =============================================================================
app.layout = html.Div(className="app-shell", children=[
    dcc.Location(id="url", refresh=False),
    sidebar(),
    html.Div(className="main", children=[
        topbar(),
        html.Div(className="content", id="page-content"),
    ]),
])


# =============================================================================
# 7. Router
# =============================================================================
@app.callback(
    Output("page-content", "children"),
    Output("crumb-current", "children"),
    Input("url", "pathname"),
)
def render_page(pathname):
    pathname = pathname or "/"
    module = PAGES.get(pathname, overview)
    try:
        layout = module.layout()
    except Exception as exc:  # never let a page crash the shell
        layout = html.Div(className="card-pf", children=[
            html.H3("Page failed to render", style={"color": "#F87171"}),
            html.Pre(str(exc), style={"whiteSpace": "pre-wrap",
                                        "color": "#B8C2D2"}),
        ])
    return layout, PATH_LABEL.get(pathname, "Overview")


@app.callback(
    Output({"type": "nav-link", "href": ALL}, "className"),
    Input("url", "pathname"),
    Input({"type": "nav-link", "href": ALL}, "id"),
)
def highlight_active_link(pathname, ids):
    pathname = pathname or "/"
    out = []
    for id_obj in ids:
        active = (id_obj["href"] == pathname)
        out.append("nav-link active" if active else "nav-link")
    return out


# =============================================================================
# 8. Register page callbacks
# =============================================================================
for module in PAGES.values():
    if hasattr(module, "register_callbacks"):
        module.register_callbacks(app)


# =============================================================================
# 9. Run
# =============================================================================
if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8050)
