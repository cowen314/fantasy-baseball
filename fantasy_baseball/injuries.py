"""
Injury Tracker
---------------
Fetches and manages MLB injury data.

Data sources (in priority order):
  1. MLB Stats API (when run locally with internet)
  2. Manual injury list (JSON/CSV)
  3. Hardcoded snapshot (updated via web search)

Integrates with lineup optimizer to flag injured/IL players.
"""

import pandas as pd
import json


# === Status classifications for fantasy purposes ===
# These map various injury statuses to actionable fantasy categories
STATUS_PRIORITY = {
    "60-Day-IL": "IL",
    "60-day-IL": "IL",
    "15-Day-IL": "IL",
    "15-day-IL": "IL",
    "10-Day-IL": "IL",
    "10-day-IL": "IL",
    "7-Day-IL": "IL",
    "Out": "OUT",
    "Day-To-Day": "DTD",
    "day-to-day": "DTD",
    "Suspension": "SUSP",
    "Paternity": "OUT",
    "Bereavement": "OUT",
}


def classify_status(status: str) -> str:
    """Map raw status to fantasy-relevant category: IL, OUT, DTD, HEALTHY."""
    if not status:
        return "HEALTHY"
    for key, val in STATUS_PRIORITY.items():
        if key.lower() in status.lower():
            return val
    return "HEALTHY"


def parse_espn_injury_text(text: str) -> list[dict]:
    """
    Parse ESPN-style injury report text into structured records.
    Expected format per player line:
      Name | POS | Est Return | Status | Comment
    """
    injuries = []
    lines = text.strip().split("\n")

    for line in lines:
        line = line.strip()
        if not line or line.startswith("|") and "NAME" in line:
            continue
        # Try pipe-delimited format
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 4:
            injury = {
                "name": parts[0].strip(),
                "position": parts[1].strip() if len(parts) > 1 else "",
                "est_return": parts[2].strip() if len(parts) > 2 else "",
                "status": parts[3].strip() if len(parts) > 3 else "",
                "comment": parts[4].strip() if len(parts) > 4 else "",
            }
            injury["fantasy_status"] = classify_status(injury["status"])
            injuries.append(injury)

    return injuries


def parse_injury_csv(filepath: str) -> list[dict]:
    """Load injuries from a CSV file (name, status, est_return, comment)."""
    df = pd.read_csv(filepath)
    injuries = []
    for _, row in df.iterrows():
        injury = {
            "name": str(row.get("name", row.get("Name", ""))),
            "position": str(row.get("position", row.get("POS", ""))),
            "est_return": str(row.get("est_return", row.get("EST. RETURN DATE", ""))),
            "status": str(row.get("status", row.get("STATUS", ""))),
            "comment": str(row.get("comment", row.get("COMMENT", ""))),
        }
        injury["fantasy_status"] = classify_status(injury["status"])
        injuries.append(injury)
    return injuries


def parse_injury_json(filepath: str) -> list[dict]:
    """Load injuries from a JSON file."""
    with open(filepath) as f:
        data = json.load(f)
    injuries = data if isinstance(data, list) else data.get("injuries", [])
    for inj in injuries:
        inj["fantasy_status"] = classify_status(inj.get("status", ""))
    return injuries


def build_injury_map(injuries: list[dict]) -> dict:
    """
    Build a name -> injury info lookup dict.
    Uses fuzzy-ish matching (lowercase, strip accents).
    """
    import unicodedata

    injury_map = {}
    for inj in injuries:
        name = inj.get("name", "")
        # Normalize for matching
        name_key = unicodedata.normalize("NFD", name.lower().strip())
        name_key = "".join(c for c in name_key if unicodedata.category(c) != "Mn")
        injury_map[name_key] = inj
        # Also store original name for exact match
        injury_map[name.lower().strip()] = inj
    return injury_map


def match_injuries_to_roster(roster_df: pd.DataFrame, injury_map: dict) -> pd.DataFrame:
    """
    Add injury columns to roster DataFrame.
    Adds: injury_status, injury_detail, est_return
    """
    import unicodedata

    df = roster_df.copy()

    statuses = []
    details = []
    returns = []

    for _, row in df.iterrows():
        name = str(row.get("name", ""))
        # Try normalized match
        name_key = unicodedata.normalize("NFD", name.lower().strip())
        name_key = "".join(c for c in name_key if unicodedata.category(c) != "Mn")

        inj = injury_map.get(name_key) or injury_map.get(name.lower().strip())

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
    """Show injury report for rostered players."""
    injured = roster_df[roster_df["injury_status"] != "HEALTHY"]

    if len(injured) == 0:
        print("\n  No injuries on your roster. Full steam ahead!")
        return

    print("\n  ROSTER INJURY REPORT")
    print("  " + "=" * 70)
    print(f"  {'Name':<25} {'Status':<8} {'Return':<12} {'Detail'}")
    print("  " + "-" * 70)

    for _, row in injured.iterrows():
        status = row["injury_status"]
        # Color-code via text markers
        if status == "IL":
            marker = "[IL]  "
        elif status == "OUT":
            marker = "[OUT] "
        elif status == "DTD":
            marker = "[DTD] "
        else:
            marker = "      "

        detail = str(row.get("injury_detail", ""))[:40]
        ret = str(row.get("est_return", ""))[:11]
        print(f"  {row['name']:<25} {marker:<8} {ret:<12} {detail}")

    healthy = len(roster_df) - len(injured)
    print(f"\n  {healthy} healthy / {len(injured)} injured or IL")


# === Local API Fetcher (for use when running locally with internet) ===

FETCH_SCRIPT = '''#!/usr/bin/env python3
"""
Fetch current MLB injuries from the MLB Stats API.
Run this locally to update injury data.

Usage:
    python fetch_injuries.py
    python fetch_injuries.py --output data/injuries.json
"""

import json
import sys
import argparse
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("Please install requests: pip install requests")
    sys.exit(1)


def fetch_mlb_injuries():
    """Fetch current injuries from MLB Stats API transactions endpoint."""
    today = datetime.now()
    start = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    url = (
        f"https://statsapi.mlb.com/api/v1/transactions"
        f"?sportId=1"
        f"&startDate={start}"
        f"&endDate={end}"
        f"&transactionType=injured_list"
    )

    print(f"Fetching: {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    injuries = []
    seen = set()

    for txn in data.get("transactions", []):
        player = txn.get("player", {})
        name = player.get("fullName", "")

        if not name or name in seen:
            continue

        desc = txn.get("description", "")
        txn_type = txn.get("typeDesc", "")
        date = txn.get("date", "")

        # Only keep IL placements (not activations)
        if "placed" in desc.lower() or "transferred" in desc.lower():
            # Determine IL type from description
            status = "Out"
            if "60-day" in desc.lower():
                status = "60-Day-IL"
            elif "15-day" in desc.lower():
                status = "15-Day-IL"
            elif "10-day" in desc.lower():
                status = "10-Day-IL"

            injuries.append({
                "name": name,
                "position": player.get("primaryPosition", {}).get("abbreviation", ""),
                "status": status,
                "comment": desc[:200],
                "date": date,
                "est_return": "",
                "fantasy_status": "IL" if "IL" in status else "OUT",
            })
            seen.add(name)

    # Remove players who were later activated
    activated = set()
    for txn in data.get("transactions", []):
        player = txn.get("player", {})
        desc = txn.get("description", "")
        if "activated" in desc.lower() or "reinstated" in desc.lower():
            activated.add(player.get("fullName", ""))

    injuries = [i for i in injuries if i["name"] not in activated]

    return injuries


def fetch_espn_roster_status():
    """
    Alternative: Fetch from ESPN injury page.
    Requires beautifulsoup4: pip install beautifulsoup4
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("beautifulsoup4 not installed, skipping ESPN fetch")
        return []

    url = "https://www.espn.com/mlb/injuries"
    resp = requests.get(url, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")

    injuries = []
    tables = soup.find_all("table")

    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:  # skip header
            cols = row.find_all("td")
            if len(cols) >= 4:
                name = cols[0].get_text(strip=True)
                pos = cols[1].get_text(strip=True)
                est_return = cols[2].get_text(strip=True)
                status = cols[3].get_text(strip=True)
                comment = cols[4].get_text(strip=True) if len(cols) > 4 else ""

                fantasy_status = "HEALTHY"
                if "IL" in status:
                    fantasy_status = "IL"
                elif "Out" in status:
                    fantasy_status = "OUT"
                elif "Day-To-Day" in status:
                    fantasy_status = "DTD"

                injuries.append({
                    "name": name,
                    "position": pos,
                    "est_return": est_return,
                    "status": status,
                    "comment": comment,
                    "fantasy_status": fantasy_status,
                })

    return injuries


def main():
    parser = argparse.ArgumentParser(description="Fetch MLB injury data")
    parser.add_argument("--output", default="data/injuries.json")
    parser.add_argument("--source", choices=["mlb", "espn", "both"], default="mlb")
    args = parser.parse_args()

    injuries = []

    if args.source in ("mlb", "both"):
        print("Fetching from MLB Stats API...")
        injuries.extend(fetch_mlb_injuries())
        print(f"  Found {len(injuries)} IL transactions")

    if args.source in ("espn", "both"):
        print("Fetching from ESPN...")
        espn = fetch_espn_roster_status()
        # Merge: ESPN has better status/return data
        existing = {i["name"] for i in injuries}
        for inj in espn:
            if inj["name"] not in existing:
                injuries.append(inj)
        print(f"  Total after ESPN merge: {len(injuries)}")

    import os
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump({"updated": datetime.now().isoformat(), "injuries": injuries}, f, indent=2)

    print(f"\\nSaved {len(injuries)} injuries to {args.output}")


if __name__ == "__main__":
    main()
'''


def generate_fetch_script(output_path: str = "fetch_injuries.py"):
    """Write the fetch script to disk."""
    with open(output_path, "w") as f:
        f.write(FETCH_SCRIPT)
    print(f"  Fetch script written: {output_path}")
    print("  Run locally: python fetch_injuries.py --source mlb")
