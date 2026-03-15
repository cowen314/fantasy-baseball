"""
Weekly Matchup Tracker
-----------------------
Track H2H category matchup for the week and generate strategy adjustments.
"""

import pandas as pd
import numpy as np
from typing import Optional

import config


def create_empty_matchup() -> dict:
    """Create an empty matchup scorecard."""
    return {
        "my_stats": {
            "R": 0, "HR": 0, "RBI": 0, "SB": 0, "OBP": 0.0,
            "K": 0, "W": 0, "SV": 0, "ERA": 0.0, "WHIP": 0.0,
            "AB": 0, "H": 0, "BB_h": 0, "PA": 0,
            "IP": 0, "ER": 0, "H_p": 0, "BB_p": 0,
        },
        "opp_stats": {
            "R": 0, "HR": 0, "RBI": 0, "SB": 0, "OBP": 0.0,
            "K": 0, "W": 0, "SV": 0, "ERA": 0.0, "WHIP": 0.0,
            "AB": 0, "H": 0, "BB_h": 0, "PA": 0,
            "IP": 0, "ER": 0, "H_p": 0, "BB_p": 0,
        },
    }


def update_rate_stats(stats: dict) -> dict:
    """Recalculate OBP, ERA, WHIP from underlying counting stats."""
    s = stats.copy()
    if s["PA"] > 0:
        s["OBP"] = round((s["H"] + s["BB_h"]) / s["PA"], 4)
    if s["IP"] > 0:
        s["ERA"] = round(s["ER"] * 9 / s["IP"], 2)
        s["WHIP"] = round((s["H_p"] + s["BB_p"]) / s["IP"], 3)
    return s


def score_matchup(my_stats: dict, opp_stats: dict) -> dict:
    """Compare stats across all 10 categories."""
    results = {}

    for cat in ["R", "HR", "RBI", "SB"]:
        mine = my_stats.get(cat, 0)
        theirs = opp_stats.get(cat, 0)
        diff = mine - theirs
        status = "WIN" if diff > 0 else ("LOSE" if diff < 0 else "TIE")
        results[cat] = {"mine": mine, "theirs": theirs, "diff": diff, "status": status}

    # OBP (higher is better)
    mine = my_stats.get("OBP", 0)
    theirs = opp_stats.get("OBP", 0)
    diff = mine - theirs
    results["OBP"] = {
        "mine": mine, "theirs": theirs,
        "diff": round(diff, 4),
        "status": "WIN" if diff > 0 else ("LOSE" if diff < 0 else "TIE"),
    }

    for cat in ["K", "W", "SV"]:
        mine = my_stats.get(cat, 0)
        theirs = opp_stats.get(cat, 0)
        diff = mine - theirs
        results[cat] = {
            "mine": mine, "theirs": theirs, "diff": diff,
            "status": "WIN" if diff > 0 else ("LOSE" if diff < 0 else "TIE"),
        }

    # ERA, WHIP (lower is better)
    for cat in ["ERA", "WHIP"]:
        mine = my_stats.get(cat, 0)
        theirs = opp_stats.get(cat, 0)
        diff = theirs - mine  # positive = I'm better
        results[cat] = {
            "mine": mine, "theirs": theirs, "diff": round(diff, 3),
            "status": "WIN" if diff > 0 else ("LOSE" if diff < 0 else "TIE"),
        }

    return results


def get_matchup_summary(results: dict) -> dict:
    wins = sum(1 for r in results.values() if r["status"] == "WIN")
    losses = sum(1 for r in results.values() if r["status"] == "LOSE")
    ties = sum(1 for r in results.values() if r["status"] == "TIE")
    return {"wins": wins, "losses": losses, "ties": ties}


def recommend_category_weights(results: dict) -> tuple[dict, dict, list]:
    """
    Based on current matchup, recommend category weights for lineup optimizer.

    Strategy:
      - Closely losing: increase weight (can still flip)
      - Winning big: decrease weight (safe)
      - Losing big: decrease weight (hard to flip)
      - Close lead: maintain/slightly increase (protect)
    """
    h_weights = {"R": 1.0, "HR": 1.0, "RBI": 1.0, "SB": 1.0, "OBP": 1.0}
    p_weights = {"K": 1.0, "W": 1.0, "SV": 1.0, "ERA": 1.0, "WHIP": 1.0}
    notes = []

    thresholds = {
        "R": (5, 15), "HR": (3, 8), "RBI": (5, 15), "SB": (3, 8),
        "OBP": (0.010, 0.030),
        "K": (5, 15), "W": (3, 8), "SV": (3, 8),
        "ERA": (0.50, 1.50), "WHIP": (0.05, 0.15),
    }

    for cat, r in results.items():
        close, far = thresholds.get(cat, (3, 10))
        abs_diff = abs(r["diff"])
        w = h_weights if cat in h_weights else p_weights

        if r["status"] == "LOSE" and abs_diff <= close:
            w[cat] = 1.5
            notes.append(f"  CHASE {cat}: losing by a small margin ({r['mine']} vs {r['theirs']})")
        elif r["status"] == "LOSE" and abs_diff > far:
            w[cat] = 0.3
            notes.append(f"  PUNT  {cat}: too far behind to flip ({r['mine']} vs {r['theirs']})")
        elif r["status"] == "WIN" and abs_diff > far:
            w[cat] = 0.5
            notes.append(f"  SAFE  {cat}: comfortable lead ({r['mine']} vs {r['theirs']})")
        elif r["status"] == "WIN" and abs_diff <= close:
            w[cat] = 1.3
            notes.append(f"  HOLD  {cat}: slim lead, keep pushing ({r['mine']} vs {r['theirs']})")

    return h_weights, p_weights, notes


def display_matchup(results: dict):
    """Pretty-print the matchup scoreboard."""
    summary = get_matchup_summary(results)

    print("\n  WEEKLY MATCHUP TRACKER")
    print("  " + "=" * 60)
    print(f"  Score: {summary['wins']}-{summary['losses']}-{summary['ties']}")
    print()

    print("  HITTING")
    print("  " + "-" * 55)
    print(f"  {'Cat':<6} {'You':>8} {'Opp':>8} {'Diff':>8} {'':>6}")
    print("  " + "-" * 55)
    for cat in ["R", "HR", "RBI", "SB", "OBP"]:
        r = results[cat]
        if cat == "OBP":
            mine = f"{r['mine']:.3f}"
            theirs = f"{r['theirs']:.3f}"
            diff_str = f"{r['diff']:+.3f}"
        else:
            mine = str(r["mine"])
            theirs = str(r["theirs"])
            diff_str = f"{r['diff']:+d}"
        icon = {"WIN": "W", "LOSE": "L", "TIE": "T"}[r["status"]]
        print(f"  {cat:<6} {mine:>8} {theirs:>8} {diff_str:>8}    {icon}")

    print()
    print("  PITCHING")
    print("  " + "-" * 55)
    print(f"  {'Cat':<6} {'You':>8} {'Opp':>8} {'Diff':>8} {'':>6}")
    print("  " + "-" * 55)
    for cat in ["K", "W", "SV", "ERA", "WHIP"]:
        r = results[cat]
        if cat == "ERA":
            mine, theirs = f"{r['mine']:.2f}", f"{r['theirs']:.2f}"
            diff_str = f"{r['diff']:+.2f}"
        elif cat == "WHIP":
            mine, theirs = f"{r['mine']:.3f}", f"{r['theirs']:.3f}"
            diff_str = f"{r['diff']:+.3f}"
        else:
            mine, theirs = str(r["mine"]), str(r["theirs"])
            diff_str = f"{r['diff']:+d}"
        icon = {"WIN": "W", "LOSE": "L", "TIE": "T"}[r["status"]]
        print(f"  {cat:<6} {mine:>8} {theirs:>8} {diff_str:>8}    {icon}")
    print()


def display_strategy(results: dict) -> tuple[dict, dict]:
    """Show recommended strategy and return adjusted weights."""
    h_w, p_w, notes = recommend_category_weights(results)

    print("  MATCHUP STRATEGY")
    print("  " + "=" * 60)
    if notes:
        for note in notes:
            print(note)
    else:
        print("  All categories fairly even — stick with balanced lineup.")
    print()
    print("  Adjusted Category Weights:")
    print(f"    Hit: R={h_w['R']:.1f} HR={h_w['HR']:.1f} RBI={h_w['RBI']:.1f} SB={h_w['SB']:.1f} OBP={h_w['OBP']:.1f}")
    print(f"    Pit: K={p_w['K']:.1f} W={p_w['W']:.1f} SV={p_w['SV']:.1f} ERA={p_w['ERA']:.1f} WHIP={p_w['WHIP']:.1f}")
    print()

    return h_w, p_w
