"""
Auto-generate a short professional report addressed to the head coach.

Pure functions only — no Dash imports. The page imports the markdown
string and renders/downloads it.
"""
from __future__ import annotations

import pandas as pd
from datetime import date


def _latest_readiness_snapshot(df: pd.DataFrame, lookback_days: int = 7) -> pd.DataFrame:
    if df.empty:
        return df
    latest = df["Date"].max()
    cutoff = latest - pd.Timedelta(days=lookback_days)
    recent = df[df["Date"] >= cutoff]
    snap = (recent.groupby("Player")
                  .agg(Position=("Position", "first"),
                       Mean_Score=("Readiness_Score", "mean"),
                       Max_Score=("Readiness_Score", "max"),
                       Mean_ACWR=("ACWR", "mean"),
                       Max_ACWR=("ACWR", "max"),
                       Mean_Fatigue=("Fatigue_Score", "mean"),
                       Mean_HRV_Pct=("HRV_RMSSD_PctChange", "mean"),
                       Mean_CMJ_Pct=("CMJ_Height_PctChange", "mean"),
                       Last_Status=("Readiness_Status", "last"))
                  .reset_index())
    return snap.sort_values("Mean_Score", ascending=False)


def players_to_watch(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    snap = _latest_readiness_snapshot(df)
    return snap.head(n)


def workload_concerns(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    notes = []
    latest = df["Date"].max()
    recent = df[df["Date"] >= latest - pd.Timedelta(days=7)]

    spike_players = (recent[recent["ACWR"] > 1.5]
                     .groupby("Player").size()
                     .sort_values(ascending=False))
    if not spike_players.empty:
        names = ", ".join(spike_players.head(5).index)
        notes.append(f"ACWR spikes (> 1.5) in last 7 days for: {names}.")

    high_load = (recent.groupby("Player")["Session_Load"].mean()
                       .sort_values(ascending=False).head(5))
    if not high_load.empty:
        names = ", ".join(high_load.index)
        notes.append(f"Highest mean session load last 7 days: {names}.")
    return notes


def fatigue_concerns(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    notes = []
    latest = df["Date"].max()
    recent = df[df["Date"] >= latest - pd.Timedelta(days=7)]

    high_fatigue = (recent.groupby("Player")["Fatigue_Score"].mean()
                          .sort_values(ascending=False).head(5))
    high_fatigue = high_fatigue[high_fatigue >= 3.5]
    if not high_fatigue.empty:
        names = ", ".join(high_fatigue.index)
        notes.append(f"Sustained high fatigue (≥ 3.5/5 mean): {names}.")

    poor_sleep = (recent.groupby("Player")["Sleep_Quality"].mean()
                        .sort_values().head(5))
    poor_sleep = poor_sleep[poor_sleep <= 3.0]
    if not poor_sleep.empty:
        names = ", ".join(poor_sleep.index)
        notes.append(f"Below-average sleep quality (≤ 3.0/5 mean): {names}.")
    return notes


def readiness_concerns(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    notes = []
    latest = df["Date"].max()
    recent = df[df["Date"] >= latest - pd.Timedelta(days=7)]

    hrv_drops = (recent.groupby("Player")["HRV_RMSSD_PctChange"].mean()
                       .sort_values().head(5))
    hrv_drops = hrv_drops[hrv_drops <= -5]
    if not hrv_drops.empty:
        names = ", ".join(hrv_drops.index)
        notes.append(f"Mean HRV below baseline (≥ 5%): {names}.")

    cmj_drops = (recent.groupby("Player")["CMJ_Height_PctChange"].mean()
                       .sort_values().head(5))
    cmj_drops = cmj_drops[cmj_drops <= -3]
    if not cmj_drops.empty:
        names = ", ".join(cmj_drops.index)
        notes.append(f"Mean CMJ below baseline (≥ 3%): {names}.")
    return notes


def injury_observations(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    inj = df[df["Injury_Label"] == 1]
    n = len(inj)
    if n == 0:
        return ["No recorded injuries in the current dataset window."]
    notes = [f"Recorded injuries in window: {n} (~ {n / len(df) * 100:.2f}% of sessions)."]
    notes.append("Pre-injury patterns observed (n is very small — descriptive only):")
    for _, row in inj.iterrows():
        notes.append(f"  • {row['Player']} on {row['Date'].date()} (Pos {row['Position']}): "
                     f"ACWR={row['ACWR']:.2f}, Fatigue={row['Fatigue_Score']:.1f}, "
                     f"CMJ={row['CMJ_Height']:.1f}, HRV={row['HRV_RMSSD']:.1f}.")
    return notes


def generate_coach_report(df: pd.DataFrame) -> str:
    today = date.today().isoformat()
    watch = players_to_watch(df, n=6)
    w_concerns = workload_concerns(df)
    f_concerns = fatigue_concerns(df)
    r_concerns = readiness_concerns(df)
    i_obs = injury_observations(df)

    n_players = df["Player"].nunique()
    n_sessions = len(df)
    n_injuries = int(df["Injury_Label"].sum())
    dr_start = df["Date"].min().date()
    dr_end = df["Date"].max().date()

    md = []
    md.append(f"# Performance & Readiness Report — {today}")
    md.append("")
    md.append(f"**Reporting window:** {dr_start} → {dr_end}  ")
    md.append(f"**Players monitored:** {n_players}  ·  **Sessions:** {n_sessions}  ·  "
              f"**Recorded injuries:** {n_injuries}")
    md.append("")
    md.append("> ⚠️  *This report is a monitoring-support tool, not a medical or "
              "diagnostic system. Readings should be combined with clinical, "
              "coaching and contextual judgement.*")
    md.append("")
    md.append("---")
    md.append("## 1. Key Findings")
    md.append("")
    md.append(f"- Squad-mean ACWR: **{df['ACWR'].mean():.2f}** "
              f"(optimal target range 0.8–1.3).")
    md.append(f"- Squad-mean Fatigue: **{df['Fatigue_Score'].mean():.2f}/5**.")
    md.append(f"- Squad-mean Sleep Quality: **{df['Sleep_Quality'].mean():.2f}/5**.")
    md.append(f"- Squad-mean CMJ Height: **{df['CMJ_Height'].mean():.1f} cm**.")
    md.append(f"- Squad-mean HRV RMSSD: **{df['HRV_RMSSD'].mean():.1f} ms**.")
    md.append("")
    md.append("## 2. Players Requiring Closer Monitoring")
    md.append("")
    if watch.empty:
        md.append("_No players currently flagged._")
    else:
        md.append("| Player | Position | Mean Readiness Score (last 7d) | Max ACWR | Mean Fatigue | Last Status |")
        md.append("|---|---|---|---|---|---|")
        for _, r in watch.iterrows():
            md.append(f"| {r['Player']} | {r['Position']} | {r['Mean_Score']:.1f} | "
                      f"{r['Max_ACWR']:.2f} | {r['Mean_Fatigue']:.1f} | {r['Last_Status']} |")
    md.append("")

    md.append("## 3. Workload Concerns")
    md.extend([f"- {n}" for n in w_concerns] or ["- No workload spikes flagged."])
    md.append("")
    md.append("## 4. Fatigue & Sleep Concerns")
    md.extend([f"- {n}" for n in f_concerns] or ["- No fatigue concerns flagged."])
    md.append("")
    md.append("## 5. Neuromuscular / Autonomic Readiness")
    md.extend([f"- {n}" for n in r_concerns] or ["- CMJ and HRV broadly within baseline."])
    md.append("")
    md.append("## 6. Injury Observations")
    md.extend([f"- {n}" for n in i_obs])
    md.append("")

    md.append("## 7. Recommendations for Coaching Staff")
    md.append("")
    md.append("- **Individualise load:** taper high-speed exposure for players in the Caution / "
              "High-Spike ACWR zones for at least 48 h.")
    md.append("- **Recovery priority:** add active-recovery sessions and sleep-hygiene reminders "
              "for players showing sustained fatigue or HRV below baseline.")
    md.append("- **Avoid abrupt jumps:** never schedule a > 50 % weekly load increase after a "
              "low-load week — drives ACWR into spike zones.")
    md.append("- **Use individual baselines:** team averages mask risk; flag deltas vs each "
              "player's own first-2-week reference.")
    md.append("- **Combine signals:** a single yellow flag is informational; two or more "
              "concurrent flags (e.g. CMJ drop + high fatigue) warrants modified training.")
    md.append("")
    md.append("## 8. Communication Plan with Head Coach")
    md.append("")
    md.append("1. Open the daily briefing with the **traffic-light board** — Green/Yellow/Red counts.")
    md.append("2. Name the 3–5 players to manage today and the specific reason for each.")
    md.append("3. Translate metrics into actions: *\"reduce high-speed volume by 20 %\"*, not "
              "*\"ACWR = 1.62\"*.")
    md.append("4. Keep the technical detail in the appendix; the coach receives one page.")
    md.append("5. Close with the squad-level question: *is the planned session compatible with "
              "today's collective readiness?*")
    md.append("")
    md.append("---")
    md.append("*Generated automatically by the Performance Analytics Dashboard.*")
    return "\n".join(md)
