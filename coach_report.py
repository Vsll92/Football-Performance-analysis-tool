"""
10) Coach Report page — auto-generated briefing + download.
"""
from __future__ import annotations

import io
import re
from datetime import datetime
import pandas as pd
from dash import dcc, html, Input, Output, State

from src.config import COLORS
from src.layout import (
    page_header, section_bar, chart_card, filter_field,
    date_range_picker, apply_filters,
)
from src.report import generate_coach_report


DATA: pd.DataFrame = None


def _controls():
    return html.Div(className="filters-bar", children=[
        html.Div(className="grid-3", children=[
            filter_field("Date range", date_range_picker(DATA, "cr-dates")),
            filter_field("Export format",
                dcc.Dropdown(id="cr-format",
                    options=[{"label": "Markdown (.md)", "value": "md"},
                              {"label": "HTML (.html)",   "value": "html"},
                              {"label": "Plain text (.txt)", "value": "txt"}],
                    value="md", clearable=False, className="dash-dropdown")),
            filter_field("",
                html.Div([
                    html.Button("🔄 Regenerate", id="cr-go",
                                  className="btn-secondary",
                                  n_clicks=0,
                                  style={"marginRight": "10px",
                                          "marginTop": "20px"}),
                    html.Button("⬇ Download report", id="cr-download-btn",
                                  className="btn-primary",
                                  n_clicks=0, style={"marginTop": "20px"}),
                ])),
        ]),
    ])


def layout():
    return html.Div([
        page_header(
            "Coach Report",
            ("Auto-generated written briefing built from the same data that "
              "drives the other pages. Useful as a 15–20 minute coach "
              "presentation script."),
        ),
        _controls(),
        dcc.Download(id="cr-download"),

        section_bar("Briefing"),
        html.Div(className="card-pf", children=[
            html.Div(className="card-head", children=[
                html.Div([
                    html.H4("Performance & readiness briefing",
                              className="card-title"),
                    html.Div(id="cr-meta", className="card-subtitle"),
                ]),
                html.Span("Auto-generated", className="card-tag"),
            ]),
            html.Div(id="cr-body", className="markdown-body"),
        ]),

        section_bar("How to use this report"),
        html.Div(className="card-pf", children=[
            html.P(
                "This report combines: today's readiness counts, top players "
                "to watch, workload concerns, fatigue / recovery findings, "
                "CMJ / HRV readiness signals, and any injury observations. "
                "It is intentionally short — meant to support a daily or "
                "weekly briefing, not replace per-player conversations.",
                className="dim",
                style={"fontSize": "13px", "margin": 0}),
            html.P(
                "Export to Markdown for sharing in a chat / wiki, HTML for "
                "an emailable version, or TXT for environments without "
                "Markdown rendering.",
                className="dim",
                style={"fontSize": "13px", "marginTop": "10px"}),
        ]),
    ])


def register_callbacks(app):

    @app.callback(
        Output("cr-body", "children"),
        Output("cr-meta", "children"),
        Input("cr-go", "n_clicks"),
        Input("cr-dates", "start_date"),
        Input("cr-dates", "end_date"),
    )
    def _regen(n, start, end):
        df = apply_filters(DATA, start_date=start, end_date=end)
        if df.empty:
            return html.Div("No data in current window.",
                              className="muted"), ""
        md_text = generate_coach_report(df)
        meta = (f"Generated {datetime.now().strftime('%b %d, %Y %H:%M')} · "
                  f"Window {df['Date'].min().strftime('%b %d')} – "
                  f"{df['Date'].max().strftime('%b %d')} · "
                  f"{df['Player'].nunique()} players, {len(df):,} sessions")
        return dcc.Markdown(md_text, className="markdown-body"), meta

    @app.callback(
        Output("cr-download", "data"),
        Input("cr-download-btn", "n_clicks"),
        State("cr-dates", "start_date"),
        State("cr-dates", "end_date"),
        State("cr-format", "value"),
        prevent_initial_call=True,
    )
    def _download(n, start, end, fmt):
        df = apply_filters(DATA, start_date=start, end_date=end)
        if df.empty:
            return None
        md_text = generate_coach_report(df)
        stamp = datetime.now().strftime("%Y%m%d_%H%M")

        if fmt == "html":
            html_body = _md_to_html(md_text)
            return dict(content=html_body, filename=f"coach_report_{stamp}.html")
        if fmt == "txt":
            txt = re.sub(r"[#*`>|_]", "", md_text)
            return dict(content=txt, filename=f"coach_report_{stamp}.txt")
        return dict(content=md_text, filename=f"coach_report_{stamp}.md")


# -----------------------------------------------------------------------------
# Minimal Markdown → HTML (good enough for an email-friendly export)
# -----------------------------------------------------------------------------
def _md_to_html(md: str) -> str:
    lines = md.split("\n")
    out = []
    in_table = False
    in_list = False
    for line in lines:
        # Headings
        if line.startswith("# "):
            out.append(f"<h1>{line[2:].strip()}</h1>")
            continue
        if line.startswith("## "):
            out.append(f"<h2>{line[3:].strip()}</h2>")
            continue
        if line.startswith("### "):
            out.append(f"<h3>{line[4:].strip()}</h3>")
            continue
        # Tables (simple Markdown)
        if "|" in line and line.strip().startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                continue  # separator row
            if not in_table:
                out.append("<table>")
                in_table = True
                tag = "th"
            else:
                tag = "td"
            out.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            continue
        else:
            if in_table:
                out.append("</table>")
                in_table = False
        # Lists
        if line.lstrip().startswith(("- ", "* ")):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{line.lstrip()[2:]}</li>")
            continue
        else:
            if in_list:
                out.append("</ul>")
                in_list = False
        # Blockquote
        if line.startswith("> "):
            out.append(f"<blockquote>{line[2:]}</blockquote>")
            continue
        # Horizontal rule
        if line.strip() in {"---", "***"}:
            out.append("<hr>")
            continue
        # Bold/italic minimal
        line_p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        line_p = re.sub(r"\*(.+?)\*", r"<em>\1</em>", line_p)
        line_p = re.sub(r"`(.+?)`", r"<code>\1</code>", line_p)
        if line_p.strip():
            out.append(f"<p>{line_p}</p>")
        else:
            out.append("")
    if in_table:
        out.append("</table>")
    if in_list:
        out.append("</ul>")
    body = "\n".join(out)
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Coach Report</title>
<style>
body {{ font-family: Inter, sans-serif; max-width: 820px; margin: 30px auto;
         padding: 0 20px; background: #fafafa; color: #1a1a1a;
         line-height: 1.55; }}
h1 {{ border-bottom: 3px solid #4F8CFF; padding-bottom: 6px; }}
h2 {{ color: #333; margin-top: 26px; }}
table {{ border-collapse: collapse; margin: 12px 0; }}
th, td {{ border: 1px solid #ccc; padding: 7px 12px; text-align: left; }}
th {{ background: #f0f4ff; }}
blockquote {{ border-left: 3px solid #F59E0B; padding: 8px 14px;
              margin: 12px 0; color: #555; background: #fffbeb; }}
code {{ background: #eee; padding: 2px 5px; border-radius: 3px; font-size: 13px; }}
</style></head>
<body>{body}</body></html>"""
