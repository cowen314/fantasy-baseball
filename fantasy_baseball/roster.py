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
from difflib import SequenceMatcher
from typing import Optional

from fantasy_baseball.valuations import (
    load_hitters,
    load_pitchers,
    filter_draftable,
    compute_hitter_zscores,
    compute_pitcher_zscores,
    zscores_to_dollars,
    assign_tiers,
)


def load_projections(hitters_path: str, pitchers_path: str) -> tuple:
    """Load projection data from Module 1."""
    h = load_hitters(hitters_path)
    p = load_pitchers(pitchers_path)
    return h, p


def load_valued_projections(hitters_path: str, pitchers_path: str) -> tuple:
    """Load projections AND run them through the valuation engine."""

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


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _name_similarity(a: str, b: str) -> float:
    """Score 0-1 for how similar two names are (accent-insensitive)."""
    return SequenceMatcher(
        None, _strip_accents(a.lower()), _strip_accents(b.lower())
    ).ratio()


def _last_name_matches(input_name: str, candidate: str) -> bool:
    """Check if the last name token is the same (accent-insensitive)."""
    a_parts = _strip_accents(input_name.lower()).split()
    b_parts = _strip_accents(candidate.lower()).split()
    if not a_parts or not b_parts:
        return False
    return a_parts[-1] == b_parts[-1]


def best_match(
    name: str, candidates: list[str], min_score: float = 0.6
) -> tuple[Optional[str], float]:
    """
    Find the best matching name from a list.
    Returns (matched_name, similarity_score) or (None, 0).

    Prioritizes:
      1. Exact match (accent-insensitive)
      2. Same last name + high similarity
      3. General fuzzy match above threshold
    """
    name_clean = _strip_accents(name.strip().lower())

    best_name = None
    best_score = 0.0

    for c in candidates:
        c_clean = _strip_accents(c.strip().lower())

        # Exact match
        if c_clean == name_clean:
            return c, 1.0

        score = _name_similarity(name, c)

        # Bonus for matching last name (strong signal)
        if _last_name_matches(name, c):
            score += 0.15

        if score > best_score:
            best_score = score
            best_name = c

    if best_score >= min_score:
        return best_name, best_score
    return None, 0.0


def parse_roster_text(text: str) -> list:
    """Parse pasted roster text into player names."""
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

    Uses similarity scoring to pick the right player when a name
    fuzzy-matches in both the hitter and pitcher pools.
    """
    all_hitter_names = hitters_df["name"].tolist()
    all_pitcher_names = pitchers_df["name"].tolist()

    roster = []
    unmatched = []

    for name in player_names:
        h_match, h_score = best_match(name, all_hitter_names)
        p_match, p_score = best_match(name, all_pitcher_names)

        h_row = hitters_df[hitters_df["name"] == h_match].iloc[0] if h_match else None
        p_row = pitchers_df[pitchers_df["name"] == p_match].iloc[0] if p_match else None

        chosen = None

        if h_row is not None and p_row is not None:
            # If one is an exact match, prefer it outright
            if h_score == 1.0 and p_score < 1.0:
                chosen = (h_row, h_match, "hitter")
            elif p_score == 1.0 and h_score < 1.0:
                chosen = (p_row, p_match, "pitcher")
            elif abs(h_score - p_score) > 0.05:
                # Clear winner by name similarity
                if h_score > p_score:
                    chosen = (h_row, h_match, "hitter")
                else:
                    chosen = (p_row, p_match, "pitcher")
            else:
                # Tie-break by playing time
                h_pa = pd.to_numeric(h_row.get("PA", 0), errors="coerce") or 0
                p_ip = pd.to_numeric(p_row.get("IP", 0), errors="coerce") or 0
                if h_pa >= p_ip * 3:
                    chosen = (h_row, h_match, "hitter")
                else:
                    chosen = (p_row, p_match, "pitcher")
        elif h_row is not None:
            chosen = (h_row, h_match, "hitter")
        elif p_row is not None:
            chosen = (p_row, p_match, "pitcher")

        if chosen:
            row_data, matched_name, ptype = chosen
            row = row_data.to_dict()
            row["matched_name"] = matched_name
            row["input_name"] = name
            row["player_type"] = ptype
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
        print(f"  Total roster value: ${roster_df['dollar_value'].sum():.0f}")
