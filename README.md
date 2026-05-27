# ⚽  Football Performance \& Injury-Risk Dashboard  — v2

> Master in Sports Analytics — final project.
> Built with \*\*Python + Dash + Plotly\*\*.
> Acts as a club-grade Performance Department dashboard: workload monitoring,
> readiness flags, neuromuscular and autonomic markers, an interactive
> comparison lab, an exploratory injury-risk model, and an auto-generated
> coach briefing.

!\[status](https://img.shields.io/badge/status-v2-blue)
!\[python](https://img.shields.io/badge/python-3.10%2B-blue)
!\[dash](https://img.shields.io/badge/dash-2.17%2B-blue)

\---

## 1\. Quick start

```bash
# 1. Clone or unzip the project
cd football\_dashboard

# 2. (Optional) virtualenv
python -m venv .venv \&\& source .venv/bin/activate

# 3. Install
pip install -r requirements.txt

# 4. Run
python app.py
# → http://xxxxxxxxxx
```

The Excel dataset is expected at
`data/raw/sports\_analytics\_master\_datasets.xlsx`.

\---

## 2\. What the dashboard does

12 pages organised into 4 sections:

|Section|Pages|
|-|-|
|**Monitoring**|Executive Overview · Workload · ACWR \& Spikes · Fatigue \& Wellness · CMJ \& HRV|
|**Risk \& Analysis**|Injury Patterns · Machine Learning|
|**Drill-down**|Player Profile · Position Comparison · Comparison Lab|
|**Communication**|Coach Report · Methodology|

Every chart on every page comes with a **data-driven insight box** carrying
three layers:

1. **Main insight** — what the chart shows (numbers, names, ranking).
2. **Coaching meaning** — what the head coach should do with it.
3. **Caution** — a caveat about interpretation (not a diagnosis, small n, etc.).

The Comparison Lab is mode-driven (Player vs Player, Position vs Position,
Workload vs Wellness, CMJ vs HRV, Combined Readiness, Injured vs Non-injured,
or Custom) with adaptive chart-type and aggregation selectors.

\---

## 3\. Project structure

```
football\_dashboard/
├── app.py                    # Dash entry point: sidebar + topbar + router
├── requirements.txt
├── README.md
├── assets/
│   └── style.css             # "Performance Lab" dark theme
├── data/
│   ├── raw/                  # Excel dataset
│   └── processed/
├── docs/
│   ├── methodology.md
│   ├── page\_guide.md
│   └── presentation\_notes.md
├── src/
│   ├── config.py             # palette, thresholds, variable labels
│   ├── data\_loader.py        # Excel I/O + cleaning
│   ├── metrics.py            # ACWR, baselines, rolling means, flags
│   ├── readiness.py          # readiness score + traffic-light
│   ├── preprocessing.py      # build\_master\_dataframe() — single entry point
│   ├── visuals.py            # Plotly chart factories
│   ├── insights.py           # data-driven insight generators
│   ├── layout.py             # page\_header, kpi, chart\_card, render\_insight
│   ├── ml\_model.py           # exploratory injury classifier
│   └── report.py             # markdown coach report
└── pages/
    ├── overview.py
    ├── workload.py
    ├── acwr\_page.py
    ├── fatigue.py
    ├── cmj\_hrv.py
    ├── injury.py
    ├── player\_profile.py
    ├── position\_page.py
    ├── comparison.py         # ← redesigned mode-driven page
    ├── ml\_page.py
    ├── coach\_report.py
    └── methodology.py
```

\---

## 4\. Readiness scoring (the single most-used derived variable)

A monitoring-support score. Higher = more flags triggered. **Not a medical
diagnosis.**

|Rule|Threshold|Points|
|-|-|-|
|ACWR > 1.3|Caution zone|+1|
|ACWR > 1.5|Extra penalty|+1 (so total +2)|
|Fatigue ≥ 4 / 5|Self-report|+1|
|Soreness ≥ 4 / 5|Self-report|+1|
|Sleep ≤ 2.5 / 5|Self-report|+1|
|HRV ≤ −10 % vs baseline|Autonomic|+1|
|CMJ ≤ −5 % vs baseline|Neuromuscular|+1|
|Resting HR ≥ +5 % vs baseline|Autonomic|+1|

* 0–1 → 🟢 **Green** — cleared
* 2–3 → 🟡 **Yellow** — modify
* 4 +  → 🔴 **Red** — recover

Baselines are each player's first 14 sessions. See `docs/methodology.md` for
the full derivation.

\---

## 5\. Limitations (read before drawing conclusions)

* The dataset contains only **2 injury-labelled sessions** out of 1,800 (\~0.1 %).
Any predictive model is **exploratory only**.
* ACWR thresholds (1.3 / 1.5) are practical monitoring guides from applied
sport-science literature, **not universal medical rules**.
* Baselines from a 14-day window can be biased if the player was already
fatigued during that window.
* Subjective wellness varies by reporting style — always compare a player
against their own history before drawing squad-level conclusions.

\---

## 6\. Running a smoke test

```bash
python - <<'PY'
import sys; sys.path.insert(0, '.')
from src.preprocessing import build\_master\_dataframe
df = build\_master\_dataframe()
import app
for path, mod in app.PAGES.items():
    mod.layout()       # raises if a page is broken
print("OK")
PY
```

Expected output: `OK`.

\---

## 7\. License \& attribution

Project deliverable for the **Master in Sports Analytics** programme.
Data is synthetic, generated for the assignment.

