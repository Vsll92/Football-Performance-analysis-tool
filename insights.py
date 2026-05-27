"""
insights.py — Data-driven insight generators.

Every important chart in the dashboard pulls its commentary from a function
defined here. Insights are NEVER generic strings; each one inspects the data
slice it is given, picks out the most salient finding, and returns a
structured `Insight` dict consumed by `visuals.render_insight()`.

Insight schema
--------------
{
    "headline":  "Main finding in one sentence.",
    "detail":    "Optional supporting numbers / context.",
    "coaching":  "What it means for coaching staff.",
    "caution":   "Optional caveat about interpretation.",
    "level":     "info" | "warning" | "danger" | "success",
}

These insights are MONITORING SUPPORT outputs — they never diagnose or
predict; they describe what the data shows and translate to action.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------
EMPTY_INSIGHT = {
    "headline":  "No data in the current selection.",
    "detail":    "Adjust filters above to load this insight.",
    "coaching":  "—",
    "caution":   None,
    "level":     "info",
}


def _top_player(df: pd.DataFrame, col: str, n: int = 1, asc: bool = False):
    if df.empty or col not in df.columns:
        return []
    s = df.groupby("Player")[col].mean().sort_values(ascending=asc)
    return [(p, v) for p, v in s.head(n).items()]


def _count_flag(df: pd.DataFrame, col: str) -> int:
    if df.empty or col not in df.columns:
        return 0
    return int(df[col].sum())


# -----------------------------------------------------------------------------
# Overview-level insight
# -----------------------------------------------------------------------------
def generate_overview_insight(df: pd.DataFrame) -> dict:
    if df.empty:
        return EMPTY_INSIGHT

    pct_red    = (df["Readiness_Status"] == "Red").mean() * 100
    pct_yellow = (df["Readiness_Status"] == "Yellow").mean() * 100
    red_players = (df[df["Readiness_Status"] == "Red"]["Player"]
                     .value_counts().head(3))

    if pct_red > 8:
        level = "danger"
        headline = (f"Squad readiness is under pressure — "
                     f"{pct_red:.1f}% of sessions are Red.")
    elif pct_red + pct_yellow > 30:
        level = "warning"
        headline = (f"Mixed readiness signals — {pct_yellow:.1f}% Yellow and "
                     f"{pct_red:.1f}% Red sessions in the selected window.")
    else:
        level = "success"
        headline = (f"Squad readiness looks healthy — only {pct_red:.1f}% Red "
                     f"and {pct_yellow:.1f}% Yellow sessions.")

    if not red_players.empty:
        names = ", ".join([f"{p} ({c}d)" for p, c in red_players.items()])
        detail = f"Most Red days fall on: {names}."
    else:
        detail = "No player has accumulated multiple Red sessions in this window."

    coaching = ("Open the daily briefing with these traffic-light counts and "
                 "name 3–5 players you want to manage today. The Player "
                 "Profile page gives the per-player reason for each flag.")
    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="Readiness flags are monitoring guides, not medical diagnosis.",
                 level=level)


# -----------------------------------------------------------------------------
# Workload page
# -----------------------------------------------------------------------------
def generate_workload_insight(df: pd.DataFrame) -> dict:
    if df.empty:
        return EMPTY_INSIGHT

    load_means = df.groupby("Player")["Session_Load"].mean().sort_values(ascending=False)
    hsr_means  = df.groupby("Player")["HSR"].mean().sort_values(ascending=False)
    spike_flag = _count_flag(df, "Flag_ACWR_Spike")

    top_load = load_means.head(3)
    top_hsr  = hsr_means.head(3)

    headline = (f"{top_load.index[0]} carries the highest mean Session Load "
                 f"({top_load.iloc[0]:.0f} AU) in the selected window.")
    detail = (f"Top-3 by load: " +
                ", ".join([f"{p} ({v:.0f})" for p, v in top_load.items()]) +
                f". Highest mean HSR: {top_hsr.index[0]} "
                f"({top_hsr.iloc[0]:.0f} m).")

    if spike_flag > 0:
        coaching = (f"{spike_flag} session(s) crossed the ACWR > 1.5 spike "
                     "threshold — those players should not absorb additional "
                     "high-speed running in the next 48 hours.")
        level = "warning"
    else:
        coaching = ("No ACWR spike (>1.5) sessions in this slice. Continue "
                     "the planned periodisation but monitor weekly trend on "
                     "the ACWR page.")
        level = "info"

    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="High load is not inherently harmful — context (match vs training, position role) matters.",
                 level=level)


# -----------------------------------------------------------------------------
# ACWR page
# -----------------------------------------------------------------------------
def generate_acwr_insight(df: pd.DataFrame) -> dict:
    if df.empty:
        return EMPTY_INSIGHT

    spike = _count_flag(df, "Flag_ACWR_Spike")
    caution = _count_flag(df, "Flag_ACWR_High") - spike
    total = len(df)
    spike_players = (df[df["Flag_ACWR_Spike"]]["Player"]
                       .value_counts().head(3))

    if spike == 0 and caution == 0:
        return dict(
            headline="ACWR is well-managed across the squad in this window.",
            detail=(f"No sessions exceeded the 1.3 caution threshold "
                     f"in {total} observations."),
            coaching=("Keep the current ramp-up. Avoid abrupt jumps after "
                       "any low-load week."),
            caution=None, level="success",
        )

    headline = (f"{spike} session(s) crossed the ACWR > 1.5 spike threshold; "
                 f"{caution} more sit in the 1.3–1.5 caution zone.")
    if not spike_players.empty:
        detail = ("Players with most spike sessions: " +
                    ", ".join([f"{p} ({c}d)" for p, c in spike_players.items()]) +
                    ".")
    else:
        detail = "Spike sessions are spread across players — no single hotspot."

    coaching = ("Caution-zone players can train normally with monitored "
                 "high-speed exposure. Spike-zone players should taper "
                 "high-intensity work for 48–72 h and recheck before "
                 "the next intense block.")
    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="ACWR thresholds (1.3 / 1.5) are practical monitoring guides, not universal medical rules.",
                 level="warning" if spike > 0 else "info")


# -----------------------------------------------------------------------------
# Fatigue / wellness page
# -----------------------------------------------------------------------------
def generate_fatigue_insight(df: pd.DataFrame) -> dict:
    if df.empty:
        return EMPTY_INSIGHT

    fatigue = df.groupby("Player")["Fatigue_Score"].mean().sort_values(ascending=False)
    sleep   = df.groupby("Player")["Sleep_Quality"].mean().sort_values(ascending=True)
    soreness= df.groupby("Player")["Soreness_Score"].mean().sort_values(ascending=False)

    top_fat = fatigue.head(3)
    worst_sleep = sleep.head(3)

    headline = (f"Highest mean fatigue: {top_fat.index[0]} "
                 f"({top_fat.iloc[0]:.2f}/5). Poorest mean sleep: "
                 f"{worst_sleep.index[0]} ({worst_sleep.iloc[0]:.2f}/5).")
    detail = ("Other names showing sustained fatigue: " +
                ", ".join([f"{p} ({v:.2f})" for p, v in top_fat.iloc[1:].items()]) +
                ". Highest mean soreness: " +
                f"{soreness.index[0]} ({soreness.iloc[0]:.2f}/5).")

    high_fat_count = (df["Fatigue_Score"] >= 4).sum()
    if high_fat_count >= 5:
        coaching = (f"{high_fat_count} sessions logged fatigue ≥ 4/5. Combine "
                     "with CMJ and HRV trends on the CMJ & HRV page before "
                     "modifying any plan — wellness alone is subjective.")
        level = "warning"
    else:
        coaching = ("Fatigue levels are within typical ranges. Continue "
                     "current recovery protocols and re-check after the "
                     "next high-load block.")
        level = "info"

    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="Subjective wellness scores vary by individual reporting style — compare each player to their own history.",
                 level=level)


# -----------------------------------------------------------------------------
# CMJ & HRV page
# -----------------------------------------------------------------------------
def generate_cmj_hrv_insight(df: pd.DataFrame) -> dict:
    if df.empty:
        return EMPTY_INSIGHT

    cmj_drops = df[df.get("CMJ_Height_PctChange", 0) <= -5]
    hrv_drops = df[df.get("HRV_RMSSD_PctChange", 0) <= -10]
    both = df[(df.get("CMJ_Height_PctChange", 0) <= -5) &
               (df.get("HRV_RMSSD_PctChange", 0) <= -10)]

    cmj_players = cmj_drops["Player"].value_counts().head(3)
    hrv_players = hrv_drops["Player"].value_counts().head(3)
    both_players= both["Player"].value_counts().head(3)

    if both_players.empty and cmj_players.empty and hrv_players.empty:
        return dict(
            headline="CMJ and HRV are tracking close to each player's own baseline.",
            detail="No sessions show CMJ > 5% below baseline or HRV > 10% below baseline.",
            coaching=("Neuromuscular and autonomic readiness look stable. "
                       "Maintain the current monitoring routine."),
            caution=None, level="success",
        )

    headline = (f"{len(cmj_drops)} sessions show CMJ ≥ 5% below baseline; "
                 f"{len(hrv_drops)} show HRV ≥ 10% below baseline.")

    parts = []
    if not cmj_players.empty:
        parts.append("CMJ drops most often: " +
                      ", ".join([f"{p} ({c}d)" for p, c in cmj_players.items()]))
    if not hrv_players.empty:
        parts.append("HRV drops most often: " +
                      ", ".join([f"{p} ({c}d)" for p, c in hrv_players.items()]))
    detail = "; ".join(parts) + "."

    if not both_players.empty:
        names = ", ".join([f"{p}" for p in both_players.index])
        coaching = (f"Players showing combined CMJ + HRV drops on the same "
                     f"day ({names}) are the priority for recovery management — "
                     "two converging signals strengthen the case for modified "
                     "training, where a single isolated flag would not.")
        level = "danger"
    else:
        coaching = ("Single-signal drops (only CMJ or only HRV) warrant "
                     "observation, not action. Wait for a converging signal "
                     "from wellness or workload before changing the plan.")
        level = "warning"

    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="Baselines come from each player's first 14 days; players already fatigued in that window will have biased reference values.",
                 level=level)


# -----------------------------------------------------------------------------
# Injury page
# -----------------------------------------------------------------------------
def generate_injury_pattern_insight(df: pd.DataFrame) -> dict:
    if df.empty:
        return EMPTY_INSIGHT

    n_inj = int(df["Injury_Label"].sum())
    n_total = len(df)
    rate = n_inj / max(n_total, 1) * 100

    if n_inj == 0:
        return dict(
            headline="No injuries recorded in this window.",
            detail=f"Reviewed {n_total} sessions.",
            coaching="Continue current monitoring approach.",
            caution=None, level="success",
        )

    # Pre-injury 7-day workload check
    insights_text = []
    inj_rows = df[df["Injury_Label"] == 1]
    elevated_acwr_pre = 0
    high_fatigue_pre = 0
    for _, r in inj_rows.iterrows():
        player = r["Player"]
        injury_date = r["Date"]
        pre = df[(df["Player"] == player) &
                  (df["Date"] >= injury_date - pd.Timedelta(days=7)) &
                  (df["Date"] < injury_date)]
        if not pre.empty:
            if (pre["ACWR"] > 1.3).any():
                elevated_acwr_pre += 1
            if (pre["Fatigue_Score"] >= 4).any():
                high_fatigue_pre += 1

    headline = (f"{n_inj} injury day(s) recorded — injury rate {rate:.2f}% "
                 "of sessions.")
    detail = (f"Of these, {elevated_acwr_pre}/{n_inj} were preceded (within "
                f"7 days) by at least one elevated-ACWR session and "
                f"{high_fatigue_pre}/{n_inj} by at least one high-fatigue day.")
    coaching = ("Use these cases for retrospective review with the medical "
                 "team. With such a small number, do not treat the observed "
                 "patterns as a predictive rule — they are hypotheses to "
                 "track going forward.")
    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution=("Very few positive cases. Patterns described are "
                            "associations, not proof of causation, and they "
                            "may not generalise to new players or seasons."),
                 level="warning")


# -----------------------------------------------------------------------------
# Player profile page
# -----------------------------------------------------------------------------
def generate_player_insight(df: pd.DataFrame, player: str,
                              window: int = 7) -> dict:
    if df.empty:
        return EMPTY_INSIGHT
    recent = df.sort_values("Date").tail(window)
    if recent.empty:
        return EMPTY_INSIGHT

    last = recent.iloc[-1]
    status = last["Readiness_Status"]

    signals = []
    if recent["Fatigue_Score"].mean() >= 3.5:
        signals.append(f"mean fatigue {recent['Fatigue_Score'].mean():.2f}/5 over {window} days")
    if recent["ACWR"].mean() > 1.3:
        signals.append(f"mean ACWR {recent['ACWR'].mean():.2f} (above caution)")
    if "CMJ_Height_PctChange" in recent.columns and recent["CMJ_Height_PctChange"].mean() < -5:
        signals.append(f"CMJ {recent['CMJ_Height_PctChange'].mean():.1f}% below baseline on average")
    if "HRV_RMSSD_PctChange" in recent.columns and recent["HRV_RMSSD_PctChange"].mean() < -10:
        signals.append(f"HRV {recent['HRV_RMSSD_PctChange'].mean():.1f}% below baseline on average")

    if status == "Red":
        headline = f"{player} is in the Red zone — multiple flags active today."
        coaching = ("Reduce high-speed running exposure for the next 48–72 h. "
                     "Move to a recovery-focused session and retest CMJ and "
                     "HRV before the next intense block.")
        level = "danger"
    elif status == "Yellow":
        headline = f"{player} is in the Yellow zone — modify, do not stop."
        coaching = ("Cap HSR and sprint exposure while keeping total volume. "
                     "Re-check wellness questionnaire and HRV before the "
                     "next session.")
        level = "warning"
    else:
        headline = f"{player} is in the Green zone — cleared for normal training."
        coaching = "Maintain current monitoring; no modifications needed today."
        level = "success"

    detail = (f"Last {window} d signals: " + "; ".join(signals)
               if signals else f"Last {window} d signals: nothing notable.")

    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="This recommendation is a monitoring-support output; combine with medical and coaching judgement.",
                 level=level)


# -----------------------------------------------------------------------------
# Comparison page — works across any comparison type
# -----------------------------------------------------------------------------
def generate_comparison_insight(df: pd.DataFrame, groupby: str,
                                  metrics: list[str]) -> dict:
    if df.empty or not metrics:
        return EMPTY_INSIGHT

    # Build per-group means for each metric
    means = df.groupby(groupby)[metrics].mean()

    lines = []
    for m in metrics[:4]:  # cap commentary length
        ranking = means[m].sort_values(ascending=False)
        if len(ranking) < 2:
            continue
        top, top_val = ranking.index[0], ranking.iloc[0]
        bot, bot_val = ranking.index[-1], ranking.iloc[-1]
        lines.append(f"{m}: {top} highest ({top_val:.2f}), {bot} lowest ({bot_val:.2f})")

    headline = f"Comparing {len(means)} {groupby.lower()}s on {len(metrics)} metric(s)."
    detail = "; ".join(lines) + "." if lines else "Insufficient data to rank."

    # Generate practical coaching summary
    if "Fatigue_Score" in metrics or "Soreness_Score" in metrics:
        coaching = ("Where one group shows high fatigue/soreness AND low "
                     "sleep quality, that group is the priority for recovery "
                     "management. Look for the same name appearing at the "
                     "'worst' end of multiple wellness metrics.")
    elif "ACWR" in metrics or "Session_Load" in metrics:
        coaching = ("High mean load is not automatically a problem — what "
                     "matters is whether ACWR sits in the optimal 0.8–1.3 "
                     "band. Cross-check the ACWR page for spike sessions.")
    elif "CMJ_Height" in metrics or "HRV_RMSSD" in metrics:
        coaching = ("Compare each group's CMJ and HRV to their own baseline, "
                     "not absolute values — taller players have higher CMJ; "
                     "older players have lower HRV. Use the % change columns.")
    else:
        coaching = ("Use this comparison to spot consistent outliers across "
                     "multiple metrics — a single high score is noise, two or "
                     "more converging signals deserve a conversation with "
                     "the player and medical team.")

    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="Comparisons across players with different positions and roles need contextual judgement — wingers run more HSR than centre-backs by design.",
                 level="info")


def generate_combined_readiness_insight(df: pd.DataFrame, groupby: str,
                                          selected: list[str]) -> dict:
    """Tailored insight for the 'Combined Readiness Comparison' section."""
    if df.empty or not selected:
        return EMPTY_INSIGHT

    sub = df[df[groupby].isin(selected)]
    if sub.empty:
        return EMPTY_INSIGHT

    summary = sub.groupby(groupby).agg(
        Fatigue=("Fatigue_Score", "mean"),
        Soreness=("Soreness_Score", "mean"),
        Sleep=("Sleep_Quality", "mean"),
        ACWR=("ACWR", "mean"),
        CMJ=("CMJ_Height", "mean"),
        HRV=("HRV_RMSSD", "mean"),
        Readiness=("Readiness_Score", "mean"),
    )

    if len(summary) < 2:
        return dict(
            headline=f"Need at least two {groupby.lower()}s to compare readiness.",
            detail="Add at least one more selection above.",
            coaching="—", caution=None, level="info",
        )

    # Find the "most concerning" entity
    concern = summary["Readiness"].idxmax()
    safest  = summary["Readiness"].idxmin()
    c_row = summary.loc[concern]
    s_row = summary.loc[safest]

    concerning_signals = []
    if c_row["Fatigue"] > s_row["Fatigue"]:
        concerning_signals.append(f"fatigue {c_row['Fatigue']:.2f} vs {s_row['Fatigue']:.2f}")
    if c_row["Soreness"] > s_row["Soreness"]:
        concerning_signals.append(f"soreness {c_row['Soreness']:.2f} vs {s_row['Soreness']:.2f}")
    if c_row["Sleep"] < s_row["Sleep"]:
        concerning_signals.append(f"sleep {c_row['Sleep']:.2f} vs {s_row['Sleep']:.2f}")
    if c_row["HRV"] < s_row["HRV"]:
        concerning_signals.append(f"HRV {c_row['HRV']:.1f} ms vs {s_row['HRV']:.1f} ms")
    if c_row["CMJ"] < s_row["CMJ"]:
        concerning_signals.append(f"CMJ {c_row['CMJ']:.1f} cm vs {s_row['CMJ']:.1f} cm")

    headline = (f"{concern} shows the highest mean readiness score "
                 f"({c_row['Readiness']:.2f}) — closer monitoring suggested.")
    detail = ("Relative to " + str(safest) + ": " +
                ", ".join(concerning_signals) +
                "." if concerning_signals else
                "No single dimension stands out as the driver.")

    coaching = (f"{concern} may need closer recovery monitoring before "
                 f"adding more high-speed running, while {safest} can absorb "
                 "normal training load. Re-check tomorrow before any "
                 "definitive change.")
    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="Readiness score combines flags; consult the per-flag breakdown on the Player Profile page for the underlying reason.",
                 level="warning")


# -----------------------------------------------------------------------------
# Coach recommendation
# -----------------------------------------------------------------------------
def generate_coach_recommendation(df: pd.DataFrame) -> dict:
    """One-paragraph head-coach-facing summary, used on the overview & report."""
    if df.empty:
        return EMPTY_INSIGHT

    red_today = (df[df["Date"] == df["Date"].max()]["Readiness_Status"] == "Red").sum()
    yellow_today = (df[df["Date"] == df["Date"].max()]["Readiness_Status"] == "Yellow").sum()
    spikes = _count_flag(df.tail(60), "Flag_ACWR_Spike")

    headline = (f"Today: {red_today} Red, {yellow_today} Yellow. "
                 f"Recent ACWR spikes: {spikes}.")
    detail = ("Use the Player Profile page to surface individual reasons "
                "for each Red and Yellow player.")
    if red_today > 0:
        coaching = (f"Plan today's session around the {red_today} Red player(s) — "
                     "give them recovery work or modify the session "
                     "appropriately; the Coach Report page generates a "
                     "downloadable briefing.")
        level = "danger" if red_today >= 3 else "warning"
    elif yellow_today > 0:
        coaching = ("Squad is broadly cleared with Yellow players to manage. "
                     "Cap HSR for Yellow names; full intensity for Green.")
        level = "warning"
    else:
        coaching = ("Squad is fully cleared today. Maintain monitoring "
                     "routine and re-evaluate after the next high-load block.")
        level = "success"

    return dict(headline=headline, detail=detail, coaching=coaching,
                 caution="Monitoring outputs support — they do not replace — clinical and coaching judgement.",
                 level=level)
