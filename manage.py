#!/usr/bin/env python3
"""
Fantasy Baseball Lineup Manager (Module 2)
=============================================
Usage:
    python manage.py --roster-file data/my_roster.txt \
                     --hitters data/hitters.csv --pitchers data/pitchers.csv

    # With injuries:
    python manage.py --roster-file data/my_roster.txt \
                     --hitters data/hitters.csv --pitchers data/pitchers.csv \
                     --injuries data/injuries.json

    # With mid-week matchup data:
    python manage.py --roster-file data/my_roster.txt \
                     --hitters data/hitters.csv --pitchers data/pitchers.csv \
                     --injuries data/injuries.json \
                     --my-stats "R=25,HR=8,..." --opp-stats "R=30,HR=10,..."
"""

import argparse
import os
import io
from contextlib import redirect_stdout


from fantasy_baseball.roster import (
    load_valued_projections, parse_roster_text, build_roster,
    save_roster, load_saved_roster, display_roster,
)
from fantasy_baseball.lineup import recommend_lineup, display_lineup, display_start_sit
from fantasy_baseball.matchup import (
    create_empty_matchup, score_matchup, display_matchup, display_strategy,
)
from fantasy_baseball.pitching import display_pitching_plan
from fantasy_baseball.injuries import (
    parse_injury_json, build_injury_map, match_injuries_to_roster,
    display_roster_injuries, generate_fetch_script,
)


def parse_stat_string(stat_str: str) -> dict:
    stats = {}
    for pair in stat_str.split(","):
        pair = pair.strip()
        if "=" in pair:
            key, val = pair.split("=", 1)
            key = key.strip().upper()
            val = val.strip()
            try:
                if "." in val:
                    stats[key] = float(val)
                else:
                    stats[key] = int(val)
            except ValueError:
                pass
    return stats


def print_header():
    print()
    print("=" * 65)
    print("  FANTASY BASEBALL LINEUP MANAGER")
    print("  12-Team H2H Categories | Daily Lineups | ESPN")
    print("=" * 65)
    print()


def main():
    parser = argparse.ArgumentParser(description="Fantasy Baseball Lineup Manager")
    parser.add_argument("--hitters", required=True)
    parser.add_argument("--pitchers", required=True)

    roster_group = parser.add_mutually_exclusive_group(required=True)
    roster_group.add_argument("--roster", help="Comma or newline-separated player names")
    roster_group.add_argument("--roster-file", help="Path to text file with player names")
    roster_group.add_argument("--load-roster", action="store_true")

    parser.add_argument("--injuries", help="Path to injuries JSON file")
    parser.add_argument("--my-stats", help="Your weekly stats: 'R=25,HR=8,...'")
    parser.add_argument("--opp-stats", help="Opponent weekly stats")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--output", default="output")
    parser.add_argument("--generate-fetcher", action="store_true",
                        help="Generate fetch_injuries.py script for local use")

    args = parser.parse_args()

    if args.generate_fetcher:
        generate_fetch_script()
        return

    print_header()

    # Load projections
    print("Loading projections and computing valuations...")
    hitters_df, pitchers_df = load_valued_projections(args.hitters, args.pitchers)
    print(f"  {len(hitters_df)} hitters, {len(pitchers_df)} pitchers valued")

    # Load roster
    print("\nLoading roster...")
    if args.load_roster:
        roster_df = load_saved_roster()
    else:
        if args.roster_file:
            with open(args.roster_file) as f:
                roster_text = f.read()
        else:
            roster_text = args.roster
        player_names = parse_roster_text(roster_text)
        print(f"  Parsed {len(player_names)} player names")
        roster_df = build_roster(player_names, hitters_df, pitchers_df)
        print(f"  Matched {len(roster_df)} players to projections")

    if args.save:
        save_roster(roster_df)

    # Load and apply injuries
    injury_map = {}
    if args.injuries and os.path.exists(args.injuries):
        print(f"\nLoading injuries from {args.injuries}...")
        injury_list = parse_injury_json(args.injuries)
        injury_map = build_injury_map(injury_list)
        roster_df = match_injuries_to_roster(roster_df, injury_map)
        injured_count = len(roster_df[roster_df["injury_status"] != "HEALTHY"])
        print(f"  {len(injury_list)} league injuries loaded, {injured_count} on your roster")
    else:
        roster_df["injury_status"] = "HEALTHY"
        roster_df["injury_detail"] = ""
        roster_df["est_return"] = ""

    # Display roster
    display_roster(roster_df)

    # Display injuries
    if injury_map:
        display_roster_injuries(roster_df)

    # Matchup tracking
    h_weights = None
    p_weights = None

    if args.my_stats and args.opp_stats:
        print("=" * 65)
        my_stats = parse_stat_string(args.my_stats)
        opp_stats = parse_stat_string(args.opp_stats)
        matchup = create_empty_matchup()
        matchup["my_stats"].update(my_stats)
        matchup["opp_stats"].update(opp_stats)
        results = score_matchup(matchup["my_stats"], matchup["opp_stats"])
        display_matchup(results)
        h_weights, p_weights = display_strategy(results)

    # Lineup recommendation (exclude IL players)
    print("=" * 65)
    active_roster = roster_df[roster_df["injury_status"] != "IL"].copy()
    if len(active_roster) < len(roster_df):
        il_players = roster_df[roster_df["injury_status"] == "IL"]["name"].tolist()
        print(f"\n  Excluding {len(il_players)} IL players from lineup: {', '.join(il_players)}")

    result = recommend_lineup(active_roster, h_weights=h_weights, p_weights=p_weights)
    display_lineup(result)

    # Flag DTD/OUT players in the lineup
    if injury_map:
        lineup_names = set(result["lineup"].values())
        dtd_in_lineup = roster_df[
            (roster_df["name"].isin(lineup_names)) &
            (roster_df["injury_status"].isin(["DTD", "OUT"]))
        ]
        if len(dtd_in_lineup) > 0:
            print("  *** INJURY WARNINGS ***")
            for _, row in dtd_in_lineup.iterrows():
                print(f"  ⚠ {row['name']} is {row['injury_status']}: {row['injury_detail'][:50]}")
            print()

    display_start_sit(result)

    # Pitching planner
    print("=" * 65)
    display_pitching_plan(active_roster, all_pitchers=pitchers_df)

    # Save report
    os.makedirs(args.output, exist_ok=True)
    report_path = os.path.join(args.output, "daily_report.txt")
    f_out = io.StringIO()
    with redirect_stdout(f_out):
        print_header()
        display_roster(roster_df)
        if injury_map:
            display_roster_injuries(roster_df)
        if args.my_stats and args.opp_stats:
            display_matchup(results)
            display_strategy(results)
        display_lineup(result)
        display_start_sit(result)
        display_pitching_plan(active_roster, all_pitchers=pitchers_df)
    with open(report_path, "w") as f:
        f.write(f_out.getvalue())
    print(f"\n  Full report saved: {report_path}")


if __name__ == "__main__":
    main()
