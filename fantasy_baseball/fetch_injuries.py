#!/usr/bin/env python3
"""
Fetch current MLB injuries and save to data/injuries.json.
Run locally (requires internet access).

Usage:
    python fetch_injuries.py                # MLB Stats API (default)
    python fetch_injuries.py --source espn  # ESPN (requires beautifulsoup4)
    python fetch_injuries.py --source both  # Merge both sources

Dependencies:
    pip install requests
    pip install beautifulsoup4   # only needed for --source espn/both
"""

import json
import os
import argparse
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
import requests


def classify_status(status: str) -> str:
    lower = status.lower()
    if "60-day" in lower or "15-day" in lower or "10-day" in lower or "7-day" in lower:
        return "IL"
    if "out" in lower:
        return "OUT"
    if "day-to-day" in lower:
        return "DTD"
    return "HEALTHY"


def fetch_from_mlb_api() -> list[dict]:
    """Pull recent IL transactions from the MLB Stats API."""
    today = datetime.now()
    start = (today - timedelta(days=60)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    url = (
        f"https://statsapi.mlb.com/api/v1/transactions"
        f"?sportId=1&startDate={start}&endDate={end}"
        f"&transactionType=injured_list"
    )

    print(f"  Fetching: {url}")
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    placed = {}
    activated = set()

    for txn in data.get("transactions", []):
        player = txn.get("player", {})
        name = player.get("fullName", "")
        desc = txn.get("description", "")
        date = txn.get("date", "")

        if not name:
            continue

        if "activated" in desc.lower() or "reinstated" in desc.lower():
            activated.add(name)
            continue

        if "placed" in desc.lower() or "transferred" in desc.lower():
            status = "Out"
            if "60-day" in desc.lower():
                status = "60-Day-IL"
            elif "15-day" in desc.lower():
                status = "15-Day-IL"
            elif "10-day" in desc.lower():
                status = "10-Day-IL"

            placed[name] = {
                "name": name,
                "position": player.get("primaryPosition", {}).get("abbreviation", ""),
                "status": status,
                "comment": desc[:200],
                "date": date,
                "est_return": "",
                "fantasy_status": classify_status(status),
            }

    # Remove anyone who was later activated
    return [inj for name, inj in placed.items() if name not in activated]


def fetch_from_espn() -> list[dict]:
    """Scrape ESPN's MLB injury page for structured data."""

    url = "https://www.espn.com/mlb/injuries"
    print(f"  Fetching: {url}")
    resp = requests.get(url, timeout=30)
    soup = BeautifulSoup(resp.text, "html.parser")

    injuries = []
    for table in soup.find_all("table"):
        for row in table.find_all("tr")[1:]:
            cols = row.find_all("td")
            if len(cols) < 4:
                continue
            name = cols[0].get_text(strip=True)
            pos = cols[1].get_text(strip=True)
            est_return = cols[2].get_text(strip=True)
            status = cols[3].get_text(strip=True)
            comment = cols[4].get_text(strip=True) if len(cols) > 4 else ""

            injuries.append(
                {
                    "name": name,
                    "position": pos,
                    "est_return": est_return,
                    "status": status,
                    "comment": comment,
                    "fantasy_status": classify_status(status),
                }
            )

    return injuries


def merge_sources(mlb: list[dict], espn: list[dict]) -> list[dict]:
    """Merge two injury lists, preferring ESPN data when both have the same player."""
    by_name = {}
    for inj in mlb:
        by_name[inj["name"].lower()] = inj
    for inj in espn:
        by_name[inj["name"].lower()] = inj  # ESPN overwrites MLB for same player
    return list(by_name.values())


def main():
    parser = argparse.ArgumentParser(description="Fetch current MLB injury data")
    parser.add_argument(
        "--output",
        default="data/injuries.json",
        help="Output path (default: data/injuries.json)",
    )
    parser.add_argument(
        "--source",
        choices=["mlb", "espn", "both"],
        default="mlb",
        help="Data source (default: mlb)",
    )
    args = parser.parse_args()

    injuries = []

    if args.source in ("mlb", "both"):
        print("Fetching from MLB Stats API...")
        mlb_injuries = fetch_from_mlb_api()
        print(f"  {len(mlb_injuries)} active IL placements found")
        injuries = mlb_injuries

    if args.source in ("espn", "both"):
        print("Fetching from ESPN...")
        espn_injuries = fetch_from_espn()
        print(f"  {len(espn_injuries)} injuries found")
        if args.source == "both":
            injuries = merge_sources(injuries, espn_injuries)
        else:
            injuries = espn_injuries

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(
            {"updated": datetime.now().isoformat(), "injuries": injuries}, f, indent=2
        )

    print(f"\nSaved {len(injuries)} injuries to {args.output}")


if __name__ == "__main__":
    main()
