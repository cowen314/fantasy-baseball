#!/usr/bin/env python3
"""
Fantasy Baseball Draft Prep Tool
==================================
Generates auction dollar values and a ranked cheat sheet
from FanGraphs projection CSVs.

Usage:
    python main.py --hitters data/hitters.csv --pitchers data/pitchers.csv

Output:
    - output/cheatsheet.csv        Full ranked cheat sheet
    - output/hitters_valued.csv    Hitter valuations detail
    - output/pitchers_valued.csv   Pitcher valuations detail
    - output/draft_summary.txt     Quick reference summary
"""

import argparse
import sys
import os

import pandas as pd

import fantasy_baseball.config as config
from fantasy_baseball.valuations import (
    load_hitters,
    load_pitchers,
    filter_draftable,
    compute_hitter_zscores,
    compute_pitcher_zscores,
    zscores_to_dollars,
    assign_tiers,
    compute_category_strengths,
    generate_cheatsheet,
)


def print_header():
    print("=" * 60)
    print("  FANTASY BASEBALL DRAFT PREP")
    print(
        f"  {config.NUM_TEAMS}-Team H2H Categories | Auction ${config.AUCTION_BUDGET}"
    )
    print("=" * 60)
    print()


def print_league_settings():
    print("League Settings:")
    print(f"  Teams: {config.NUM_TEAMS}")
    print(
        f"  Budget: ${config.AUCTION_BUDGET} per team (${config.TOTAL_LEAGUE_BUDGET} total)"
    )
    print(f"  Hitter slots: {config.TOTAL_HITTER_SLOTS} starters")
    print(f"  Pitcher slots: {config.TOTAL_PITCHER_SLOTS} starters")
    print(f"  Bench: {config.BENCH_SLOTS} | IL: {config.IL_SLOTS}")
    print(
        f"  Budget split: {config.HITTER_BUDGET_PCT:.0%} hitters / {config.PITCHER_BUDGET_PCT:.0%} pitchers"
    )
    print()
    print("  Hitting categories:  R | HR | RBI | SB | OBP")
    print("  Pitching categories: K | W  | SV  | ERA| WHIP")
    print()


def print_top_players(cheatsheet: pd.DataFrame, n: int = 30):
    """Print a formatted top-N summary."""
    print(f"Top {n} Players by Auction Value:")
    print("-" * 75)
    print(f"{'Rank':>4}  {'Name':<25} {'Type':<8} {'Pos':<11} {'$':>4} {'Tier':>4}")
    print("-" * 75)

    for rank, row in cheatsheet.head(n).iterrows():
        pos = str(row.get("positions", ""))[:10]
        print(
            f"{rank:>4}  {row['name']:<25} {row['player_type']:<8} "
            f"{pos:<11} ${row['dollar_value']:>3}  T{row.get('tier', '?')}"
        )
    print()


def print_positional_scarcity(hitters: pd.DataFrame):
    """Show how value drops off by position."""
    print("Positional Scarcity (Top players by position):")
    print("-" * 50)

    positions = ["C", "1B", "2B", "3B", "SS", "OF"]
    for pos in positions:
        # Filter players eligible at this position
        pos_players = hitters[
            hitters["positions"].str.contains(pos, case=False, na=False)
        ]
        pos_players = pos_players.nlargest(5, "dollar_value")

        values = pos_players["dollar_value"].tolist()
        names = pos_players["name"].tolist()

        if values:
            top_val = values[0]
            drop = values[0] - values[-1] if len(values) > 1 else 0
            print(
                f"  {pos:<3}: ${top_val:>3} (top: {names[0]:<20}) | drop to #{len(values)}: ${drop}"
            )

    print()


def print_category_values(hitters: pd.DataFrame, pitchers: pd.DataFrame):
    """Show which categories have the most/least variance (opportunity)."""
    print("Category Value Spread (std dev of z-scores):")
    print("-" * 40)

    for cat in ["R", "HR", "RBI", "SB", "OBP"]:
        z_col = f"z_{cat}"
        if z_col in hitters.columns:
            std = hitters[z_col].std()
            print(f"  {cat:<5}: {std:.3f}")

    for cat in ["K", "W", "SV", "ERA", "WHIP"]:
        z_col = f"z_{cat}"
        if z_col in pitchers.columns:
            std = pitchers[z_col].std()
            print(f"  {cat:<5}: {std:.3f}")
    print()


def save_outputs(
    cheatsheet: pd.DataFrame,
    hitters: pd.DataFrame,
    pitchers: pd.DataFrame,
    output_dir: str = "output",
):
    """Save all output files."""
    os.makedirs(output_dir, exist_ok=True)

    # Cheat sheet
    cs_path = os.path.join(output_dir, "cheatsheet.csv")
    cheatsheet.to_csv(cs_path)
    print(f"  Saved: {cs_path}")

    # Detailed hitter valuations
    h_path = os.path.join(output_dir, "hitters_valued.csv")
    h_cols = [
        "name",
        "positions",
        "dollar_value",
        "tier",
        "R",
        "HR",
        "RBI",
        "SB",
        "OBP",
        "PA",
        "z_R",
        "z_HR",
        "z_RBI",
        "z_SB",
        "z_OBP",
        "z_total",
    ]
    h_cols = [c for c in h_cols if c in hitters.columns]
    hitters.sort_values("dollar_value", ascending=False)[h_cols].to_csv(
        h_path, index=False
    )
    print(f"  Saved: {h_path}")

    # Detailed pitcher valuations
    p_path = os.path.join(output_dir, "pitchers_valued.csv")
    p_cols = [
        "name",
        "positions",
        "dollar_value",
        "tier",
        "K",
        "W",
        "SV",
        "ERA",
        "WHIP",
        "IP",
        "z_K",
        "z_W",
        "z_SV",
        "z_ERA",
        "z_WHIP",
        "z_total",
    ]
    p_cols = [c for c in p_cols if c in pitchers.columns]
    pitchers.sort_values("dollar_value", ascending=False)[p_cols].to_csv(
        p_path, index=False
    )
    print(f"  Saved: {p_path}")


def generate_summary(
    cheatsheet: pd.DataFrame, hitters: pd.DataFrame, pitchers: pd.DataFrame
) -> str:
    """Generate a text summary for quick reference."""
    lines = []
    lines.append("DRAFT DAY QUICK REFERENCE")
    lines.append("=" * 50)
    lines.append(f"Total players valued: {len(cheatsheet)}")
    lines.append(f"  Hitters: {len(hitters[hitters['dollar_value'] > 1])}")
    lines.append(f"  Pitchers: {len(pitchers[pitchers['dollar_value'] > 1])}")
    lines.append("")

    # Top 10 overall
    lines.append("TOP 10 OVERALL:")
    for rank, row in cheatsheet.head(10).iterrows():
        lines.append(
            f"  {rank:>2}. {row['name']:<25} ${row['dollar_value']:>3}  ({row['player_type']})"
        )
    lines.append("")

    # Top 5 by position
    for pos in ["C", "1B", "2B", "3B", "SS", "OF", "SP", "RP"]:
        if pos in ["SP", "RP"]:
            pool = pitchers
        else:
            pool = hitters
        pos_players = pool[pool["positions"].str.contains(pos, case=False, na=False)]
        top5 = pos_players.nlargest(5, "dollar_value")
        lines.append(f"TOP 5 {pos}:")
        for _, row in top5.iterrows():
            lines.append(f"  {row['name']:<25} ${row['dollar_value']:>3}")
        lines.append("")

    # Budget strategy suggestion
    lines.append("BUDGET STRATEGY:")
    lines.append(
        f"  Hitter budget: ${config.AUCTION_BUDGET * config.HITTER_BUDGET_PCT:.0f}"
    )
    lines.append(
        f"  Pitcher budget: ${config.AUCTION_BUDGET * config.PITCHER_BUDGET_PCT:.0f}"
    )
    lines.append("  Target 2-3 elite hitters ($30+), fill with $10-20 mid-tier")
    lines.append("  Target 1-2 ace SP ($25+), grab saves late if possible")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fantasy Baseball Draft Prep Tool")
    parser.add_argument(
        "--hitters", required=True, help="Path to hitter projections CSV"
    )
    parser.add_argument(
        "--pitchers", required=True, help="Path to pitcher projections CSV"
    )
    parser.add_argument(
        "--output", default="output", help="Output directory (default: output)"
    )
    parser.add_argument(
        "--min-pa", type=int, default=None, help="Override minimum PA threshold"
    )
    parser.add_argument(
        "--min-ip", type=int, default=None, help="Override minimum IP threshold"
    )
    parser.add_argument(
        "--hitter-budget-pct",
        type=float,
        default=None,
        help="Override hitter budget % (0-1)",
    )
    args = parser.parse_args()

    # Apply overrides
    if args.min_pa is not None:
        config.MIN_PA = args.min_pa
    if args.min_ip is not None:
        config.MIN_IP = args.min_ip
    if args.hitter_budget_pct is not None:
        config.HITTER_BUDGET_PCT = args.hitter_budget_pct
        config.PITCHER_BUDGET_PCT = 1 - args.hitter_budget_pct

    print_header()
    print_league_settings()

    # Load data
    print("Loading projections...")
    try:
        hitters_raw = load_hitters(args.hitters)
        print(f"  Hitters loaded: {len(hitters_raw)} players")
    except Exception as e:
        print(f"  ERROR loading hitters: {e}")
        sys.exit(1)

    try:
        pitchers_raw = load_pitchers(args.pitchers)
        print(f"  Pitchers loaded: {len(pitchers_raw)} players")
    except Exception as e:
        print(f"  ERROR loading pitchers: {e}")
        sys.exit(1)

    # Filter
    print(f"\nFiltering (min PA={config.MIN_PA}, min IP={config.MIN_IP})...")
    hitters = filter_draftable(hitters_raw, "hitter")
    pitchers = filter_draftable(pitchers_raw, "pitcher")
    print(f"  Draftable hitters: {len(hitters)}")
    print(f"  Draftable pitchers: {len(pitchers)}")

    # Compute z-scores
    print("\nComputing valuations...")
    hitters = compute_hitter_zscores(hitters)
    pitchers = compute_pitcher_zscores(pitchers)

    # Convert to dollars
    hitters, pitchers = zscores_to_dollars(hitters, pitchers)

    # Assign tiers
    hitters = assign_tiers(hitters)
    pitchers = assign_tiers(pitchers)

    # Category strengths
    hitters = compute_category_strengths(hitters, ["R", "HR", "RBI", "SB", "OBP"])
    pitchers = compute_category_strengths(pitchers, ["K", "W", "SV", "ERA", "WHIP"])

    # Generate cheat sheet
    cheatsheet = generate_cheatsheet(hitters, pitchers)

    print("\n" + "=" * 60)
    print()
    print_top_players(cheatsheet, n=30)
    print_positional_scarcity(hitters)
    print_category_values(hitters, pitchers)

    # Save outputs
    print("Saving outputs...")
    save_outputs(cheatsheet, hitters, pitchers, args.output)

    # Summary
    summary = generate_summary(cheatsheet, hitters, pitchers)
    summary_path = os.path.join(args.output, "draft_summary.txt")
    with open(summary_path, "w") as f:
        f.write(summary)
    print(f"  Saved: {summary_path}")

    print("\nDone! Review the cheat sheet and adjust as needed.")
    print("Good luck on draft day!")


if __name__ == "__main__":
    main()
