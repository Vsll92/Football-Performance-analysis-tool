"""Basic project smoke check."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.preprocessing import build_master_dataframe
from src.ml_model import train_injury_model


def main():
    df = build_master_dataframe()
    assert not df.empty, "processed dataframe is empty"
    required = ["Date", "Player", "Position", "ACWR_Calc", "Readiness_Score", "Readiness_Status"]
    missing = [c for c in required if c not in df.columns]
    assert not missing, f"missing columns: {missing}"
    assert df["ACWR_Calc"].notna().any(), "ACWR_Calc all missing"
    result = train_injury_model(df, features=["Session_Load", "ACWR", "Fatigue_Score", "HRV_RMSSD", "CMJ_Height"], model_name="Logistic Regression", oversample=False)
    assert result.get("status") in {"ok", "insufficient"}, result
    print("PASS smoke_check")
    print(f"Rows={len(df):,}, players={df['Player'].nunique()}, injuries={int(df['Injury_Label'].sum())}")
    print(f"ML status={result.get('status')}: {result.get('message','trained')}")

if __name__ == "__main__":
    main()
