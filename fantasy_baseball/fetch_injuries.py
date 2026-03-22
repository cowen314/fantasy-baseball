#!/usr/bin/env python3
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
        # txn_type = txn.get("typeDesc", "")
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

            injuries.append(
                {
                    "name": name,
                    "position": player.get("primaryPosition", {}).get(
                        "abbreviation", ""
                    ),
                    "status": status,
                    "comment": desc[:200],
                    "date": date,
                    "est_return": "",
                    "fantasy_status": "IL" if "IL" in status else "OUT",
                }
            )
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

                injuries.append(
                    {
                        "name": name,
                        "position": pos,
                        "est_return": est_return,
                        "status": status,
                        "comment": comment,
                        "fantasy_status": fantasy_status,
                    }
                )

    return injuries


def main():
    parser = argparse.ArgumentParser(description="Fetch MLB injury data")
    parser.add_argument("--output", default="inputs/injuries.json")
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
        json.dump(
            {"updated": datetime.now().isoformat(), "injuries": injuries}, f, indent=2
        )

    print(f"\nSaved {len(injuries)} injuries to {args.output}")


if __name__ == "__main__":
    main()
