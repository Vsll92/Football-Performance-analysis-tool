"""Build transparent processed-data outputs for the dashboard.

Run from project root:
    python tools/build_processed_data.py
"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.preprocessing import build_master_dataframe
from src.config import PROCESSED_DIR, VARIABLE_LABELS


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df = build_master_dataframe()
    df.to_csv(PROCESSED_DIR / "monitoring_processed.csv", index=False)

    dictionary = []
    for col in df.columns:
        dictionary.append({
            "column": col,
            "label": VARIABLE_LABELS.get(col, col.replace("_", " ")),
            "dtype": str(df[col].dtype),
            "missing": int(df[col].isna().sum()),
            "min": df[col].min() if pd.api.types.is_numeric_dtype(df[col]) else "",
            "mean": df[col].mean() if pd.api.types.is_numeric_dtype(df[col]) else "",
            "max": df[col].max() if pd.api.types.is_numeric_dtype(df[col]) else "",
            "type": "derived/proxy" if col.endswith(("_Calc", "_Baseline", "_PctChange")) or col.startswith("Flag_") or "Proxy" in col or col in {"Readiness_Score", "Readiness_Status", "ACWR_Calc_Zone", "High_Load_Day_Flag"} else "raw/cleaned",
        })
    pd.DataFrame(dictionary).to_csv(PROCESSED_DIR / "data_dictionary.csv", index=False)

    flags = (df.groupby(["Readiness_Status"])
               .size().reset_index(name="rows"))
    flags.to_csv(PROCESSED_DIR / "readiness_flags_summary.csv", index=False)

    acwr = pd.DataFrame({
        "metric": ["Dataset ACWR", "Calculated ACWR"],
        "mean": [df["ACWR"].mean(), df["ACWR_Calc"].mean()],
        "min": [df["ACWR"].min(), df["ACWR_Calc"].min()],
        "max": [df["ACWR"].max(), df["ACWR_Calc"].max()],
    })
    acwr.loc[:, "note"] = "Calculated ACWR uses 7-day average / 28-day average."
    acwr.to_csv(PROCESSED_DIR / "acwr_quality_check.csv", index=False)

    print("Processed outputs written to", PROCESSED_DIR)
    print(f"Rows: {len(df):,} | Players: {df['Player'].nunique()} | Injuries: {int(df['Injury_Label'].sum())}")
    print(f"Mean dataset ACWR={df['ACWR'].mean():.3f} | Mean ACWR_Calc={df['ACWR_Calc'].mean():.3f}")

if __name__ == "__main__":
    main()
