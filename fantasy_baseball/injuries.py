"""
Injury Tracker
---------------
Parses, stores, and matches MLB injury data against your roster.

Data is loaded from JSON or CSV files produced by fetch_injuries.py
or maintained manually.
"""

import pandas as pd
import json
import unicodedata

STATUS_MAP = {
    "60-day-il": "IL",
    "15-day-il": "IL",
    "10-day-il": "IL",
    "7-day-il": "IL",
    "out": "OUT",
    "day-to-day": "DTD",
    "suspension": "SUSP",
    "paternity": "OUT",
    "bereavement": "OUT",
}


def classify_status(status: str) -> str:
    """Map a raw status string to a fantasy-relevant category: IL, OUT, DTD, or HEALTHY."""
    if not status:
        return "HEALTHY"
    lower = status.lower()
    for key, val in STATUS_MAP.items():
        if key in lower:
            return val
    return "HEALTHY"


def _normalize_name(name: str) -> str:
    """Lowercase and strip accents for fuzzy matching."""
    name = unicodedata.normalize("NFD", name.lower().strip())
    return "".join(c for c in name if unicodedata.category(c) != "Mn")


def parse_injury_json(filepath: str) -> list[dict]:
    """Load injuries from a JSON file (fetch_injuries.py output format)."""
    with open(filepath) as f:
        data = json.load(f)
    injuries = data if isinstance(data, list) else data.get("injuries", [])
    for inj in injuries:
        inj["fantasy_status"] = classify_status(inj.get("status", ""))
    return injuries


def parse_injury_csv(filepath: str) -> list[dict]:
    """Load injuries from a CSV (columns: name, status, est_return, comment)."""
    df = pd.read_csv(filepath)
    injuries = []
    for _, row in df.iterrows():
        inj = {
            "name": str(row.get("name", row.get("Name", ""))),
            "position": str(row.get("position", row.get("POS", ""))),
            "est_return": str(row.get("est_return", row.get("EST. RETURN DATE", ""))),
            "status": str(row.get("status", row.get("STATUS", ""))),
            "comment": str(row.get("comment", row.get("COMMENT", ""))),
        }
        inj["fantasy_status"] = classify_status(inj["status"])
        injuries.append(inj)
    return injuries


def build_injury_map(injuries: list[dict]) -> dict:
    """Build a normalized-name -> injury record lookup."""
    injury_map = {}
    for inj in injuries:
        name = inj.get("name", "")
        injury_map[_normalize_name(name)] = inj
        injury_map[name.lower().strip()] = inj
    return injury_map


def match_injuries_to_roster(roster_df: pd.DataFrame, injury_map: dict) -> pd.DataFrame:
    """Add injury_status, injury_detail, and est_return columns to a roster DataFrame."""
    df = roster_df.copy()
    statuses, details, returns = [], [], []

    for _, row in df.iterrows():
        name = str(row.get("name", ""))
        inj = injury_map.get(_normalize_name(name)) or injury_map.get(
            name.lower().strip()
        )

        if inj:
            statuses.append(inj.get("fantasy_status", "HEALTHY"))
            details.append(inj.get("comment", inj.get("status", "")))
            returns.append(inj.get("est_return", ""))
        else:
            statuses.append("HEALTHY")
            details.append("")
            returns.append("")

    df["injury_status"] = statuses
    df["injury_detail"] = details
    df["est_return"] = returns
    return df


def display_roster_injuries(roster_df: pd.DataFrame):
    """Print injury report for rostered players."""
    injured = roster_df[roster_df["injury_status"] != "HEALTHY"]

    if len(injured) == 0:
        print("\n  No injuries on your roster. Full steam ahead!")
        return

    print("\n  ROSTER INJURY REPORT")
    print("  " + "=" * 70)
    print(f"  {'Name':<25} {'Status':<8} {'Return':<12} {'Detail'}")
    print("  " + "-" * 70)

    for _, row in injured.iterrows():
        tag = {"IL": "[IL]", "OUT": "[OUT]", "DTD": "[DTD]", "SUSP": "[SUSP]"}.get(
            row["injury_status"], ""
        )
        detail = str(row.get("injury_detail", ""))[:40]
        ret = str(row.get("est_return", ""))[:11]
        print(f"  {row['name']:<25} {tag:<8} {ret:<12} {detail}")

    healthy = len(roster_df) - len(injured)
    print(f"\n  {healthy} healthy / {len(injured)} injured or IL")
