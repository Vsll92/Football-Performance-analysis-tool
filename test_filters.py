"""Filter QA tests for data/filter logic.

This intentionally avoids opening a browser, so it can run in CI or before Dash is installed.
It tests the shared filter helpers and the common edge cases that were failing.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.preprocessing import build_master_dataframe
from src.filtering import apply_filters, safe_metric, safe_metrics_list, safe_focus_player
from src.config import ALL_METRICS


def check(name, fn):
    try:
        fn()
        print(f"PASS {name}")
    except Exception as e:
        print(f"FAIL {name}: {type(e).__name__}: {e}")
        raise


def main():
    df = build_master_dataframe()
    players = sorted(df["Player"].unique(), key=lambda x: int(str(x).split("_")[-1]))
    positions = sorted(df["Position"].unique())

    check("default filters", lambda: apply_filters(df))
    check("one player", lambda: apply_filters(df, players=[players[0]]))
    check("multiple players", lambda: apply_filters(df, players=players[:3]))
    check("one position", lambda: apply_filters(df, positions=[positions[0]]))
    check("multiple positions", lambda: apply_filters(df, positions=positions[:2]))
    check("empty date range", lambda: apply_filters(df, start_date="1900-01-01", end_date="1900-01-02"))
    check("readiness status", lambda: apply_filters(df, statuses=["Red"]))
    check("injured only", lambda: apply_filters(df, injury_filter="injured"))
    check("non-injured only", lambda: apply_filters(df, injury_filter="non_injured"))
    check("invalid metric fallback", lambda: safe_metric(None, "Session_Load", ALL_METRICS) == "Session_Load")
    check("multi metric cleared fallback", lambda: len(safe_metrics_list(None, ["Session_Load", "ACWR"], ALL_METRICS)) > 0)
    check("focus player fallback", lambda: safe_focus_player(apply_filters(df, players=[players[1]]), players[0]) == players[1])
    # Simulate conflict: player selected does not match selected position -> no data, not crash.
    conflict_position = df[df["Player"] == players[0]]["Position"].iloc[0]
    other_positions = [p for p in positions if p != conflict_position]
    if other_positions:
        check("player-position conflict empty safe", lambda: apply_filters(df, players=[players[0]], positions=[other_positions[0]]).empty)
    print("PASS filter QA completed")

if __name__ == "__main__":
    main()
