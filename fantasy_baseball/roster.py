"""
Roster Management
------------------
Load, parse, and store the user's fantasy roster.
Matches player names against projection data to pull stats and positions.
"""

import pandas as pd
import os
import re
import unicodedata
from difflib import get_close_matches
from typing import Optional


def load_projections(hitters_path: str, pitchers_path: str) -> tuple:
    """Load projection data from Module 1."""
    from valuations import load_hitters, load_pitchers

    h = load_hitters(hitters_path)
    p = load_pitchers(pitchers_path)
    return h, p


def load_valued_projections(hitters_path: str, pitchers_path: str) -> tuple:
    """Load projections AND run them through the valuation engine."""
    from valuations import (
        load_hitters,
        load_pitchers,
        filter_draftable,
        compute_hitter_zscores,
        compute_pitcher_zscores,
        zscores_to_dollars,
        assign_tiers,
    )

    h = load_hitters(hitters_path)
    p = load_pitchers(pitchers_path)

    h_draft = filter_draftable(h, "hitter")
    p_draft = filter_draftable(p, "pitcher")

    h_draft = compute_hitter_zscores(h_draft)
    p_draft = compute_pitcher_zscores(p_draft)

    h_draft, p_draft = zscores_to_dollars(h_draft, p_draft)
    h_draft = assign_tiers(h_draft)
    p_draft = assign_tiers(p_draft)

    return h_draft, p_draft


def strip_accents(s: str) -> str:
    """Remove accent marks for comparison."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def fuzzy_match_player(
    name: str, all_names: list, cutoff: float = 0.6
) -> Optional[str]:
    """Fuzzy match a player name against a name list."""
    name_clean = strip_accents(name.strip().lower())

    # Exact match (accent-insensitive)
    for n in all_names:
        if strip_accents(n).lower() == name_clean:
            return n

    # Contains match (accent-insensitive)
    for n in all_names:
        n_clean = strip_accents(n).lower()
        if name_clean in n_clean or n_clean in name_clean:
            return n

    # Last name + first initial
    parts = name_clean.split()
    if len(parts) >= 2:
        last = parts[-1]
        first_init = parts[0][0]
        for n in all_names:
            n_clean = strip_accents(n).lower()
            n_parts = n_clean.split()
            if n_parts and n_parts[-1] == last and n_clean[0] == first_init:
                return n

    # Fuzzy
    matches = get_close_matches(name, all_names, n=1, cutoff=cutoff)
    return matches[0] if matches else None


def parse_roster_text(text: str) -> list:
    """Parse a pasted roster into player names."""
    players = []
    lines = text.strip().split("\n")
    if len(lines) == 1 and "," in lines[0]:
        lines = lines[0].split(",")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        line = re.sub(
            r"^(C|1B|2B|3B|SS|IF|OF|UTIL|SP|RP|P|DH|BE|IL|BN)\s*[-:\.]\s*",
            "",
            line,
            flags=re.IGNORECASE,
        )
        line = re.sub(r"^\d+[\.\)\-]\s*", "", line)
        line = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", line)
        line = re.sub(r"\s+(C|1B|2B|3B|SS|OF|SP|RP|DH)\s*$", "", line)
        line = line.strip()
        if line and len(line) > 2:
            players.append(line)

    return players


def build_roster(
    player_names: list, hitters_df: pd.DataFrame, pitchers_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Match player names to projection data.

    Handles ambiguity: if a name matches both a hitter and pitcher,
    picks the one with more playing time (higher PA or IP).
    """
    all_hitter_names = hitters_df["name"].tolist()
    all_pitcher_names = pitchers_df["name"].tolist()

    roster = []
    unmatched = []

    for name in player_names:
        # Match in both pools separately
        h_match_name = fuzzy_match_player(name, all_hitter_names)
        p_match_name = fuzzy_match_player(name, all_pitcher_names)

        h_row = None
        p_row = None

        if h_match_name:
            h_hits = hitters_df[hitters_df["name"] == h_match_name]
            if len(h_hits) > 0:
                h_row = h_hits.iloc[0]

        if p_match_name:
            p_hits = pitchers_df[pitchers_df["name"] == p_match_name]
            if len(p_hits) > 0:
                p_row = p_hits.iloc[0]

        # Decide: hitter or pitcher?
        if h_row is not None and p_row is not None:
            # Both matched — pick the "real" player (more playing time)
            h_pa = pd.to_numeric(h_row.get("PA", 0), errors="coerce") or 0
            p_ip = pd.to_numeric(p_row.get("IP", 0), errors="coerce") or 0

            # Heuristic: a hitter with 200+ PA is more likely the intended match
            # than a pitcher with 200+ IP if both exist.
            # But a hitter with 1 PA is clearly not the intended match vs a pitcher with 66 IP.
            h_score = h_pa
            p_score = p_ip * 3  # weight IP higher since fewer raw innings than PA

            if h_score >= p_score:
                row = h_row.to_dict()
                row["matched_name"] = h_match_name
                row["input_name"] = name
                row["player_type"] = "hitter"
            else:
                row = p_row.to_dict()
                row["matched_name"] = p_match_name
                row["input_name"] = name
                row["player_type"] = "pitcher"
            roster.append(row)
        elif h_row is not None:
            row = h_row.to_dict()
            row["matched_name"] = h_match_name
            row["input_name"] = name
            row["player_type"] = "hitter"
            roster.append(row)
        elif p_row is not None:
            row = p_row.to_dict()
            row["matched_name"] = p_match_name
            row["input_name"] = name
            row["player_type"] = "pitcher"
            roster.append(row)
        else:
            unmatched.append(name)

    roster_df = pd.DataFrame(roster)

    if unmatched:
        print(f"\n  WARNING: Could not match {len(unmatched)} players:")
        for n in unmatched:
            print(f"    - {n}")

    return roster_df


def save_roster(roster_df: pd.DataFrame, path: str = "data/my_roster.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    roster_df.to_csv(path, index=False)
    print(f"  Roster saved: {path}")


def load_saved_roster(path: str = "data/my_roster.csv") -> pd.DataFrame:
    return pd.read_csv(path)


def display_roster(roster_df: pd.DataFrame):
    """Pretty-print the roster."""
    hitters = roster_df[roster_df["player_type"] == "hitter"].copy()
    pitchers = roster_df[roster_df["player_type"] == "pitcher"].copy()

    if "dollar_value" in hitters.columns:
        hitters = hitters.sort_values("dollar_value", ascending=False)
    if "dollar_value" in pitchers.columns:
        pitchers = pitchers.sort_values("dollar_value", ascending=False)

    print("\n  YOUR ROSTER")
    print("  " + "=" * 70)

    print(f"\n  HITTERS ({len(hitters)})")
    print("  " + "-" * 70)
    print(f"  {'Name':<25} {'Pos':<12} {'$':>4}   R   HR  RBI   SB   OBP")
    print("  " + "-" * 70)
    for _, row in hitters.iterrows():
        pos = str(row.get("positions", ""))[:11]
        dv = row.get("dollar_value", 0)
        print(
            f"  {row['name']:<25} {pos:<12} ${dv:>3}  "
            f"{row.get('R', 0):>4.0f} {row.get('HR', 0):>4.0f} {row.get('RBI', 0):>4.0f} "
            f"{row.get('SB', 0):>4.0f}  {row.get('OBP', 0):.3f}"
        )

    print(f"\n  PITCHERS ({len(pitchers)})")
    print("  " + "-" * 70)
    print(f"  {'Name':<25} {'Pos':<12} {'$':>4}    K    W   SV   ERA  WHIP")
    print("  " + "-" * 70)
    for _, row in pitchers.iterrows():
        pos = str(row.get("positions", ""))[:11]
        dv = row.get("dollar_value", 0)
        print(
            f"  {row['name']:<25} {pos:<12} ${dv:>3}  "
            f"{row.get('K', 0):>4.0f} {row.get('W', 0):>5.0f} {row.get('SV', 0):>4.0f}  "
            f"{row.get('ERA', 0):>5.2f} {row.get('WHIP', 0):.3f}"
        )

    print()
    if "dollar_value" in roster_df.columns:
        total_value = roster_df["dollar_value"].sum()
        print(f"  Total roster value: ${total_value:.0f}")
