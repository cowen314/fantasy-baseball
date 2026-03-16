"""
Lineup Optimizer
-----------------
Daily start/sit recommendations for H2H Categories leagues.
"""

import pandas as pd
import numpy as np
from typing import Optional

import fantasy_baseball.config as config


def compute_per_game_rates(roster_df: pd.DataFrame) -> pd.DataFrame:
    """Convert season projections to per-game rates."""
    df = roster_df.copy()
    hitters = df["player_type"] == "hitter"
    pitchers = df["player_type"] == "pitcher"

    if "G" in df.columns:
        df.loc[hitters, "games"] = pd.to_numeric(df.loc[hitters, "G"], errors="coerce").fillna(140)
    else:
        df.loc[hitters, "games"] = (pd.to_numeric(df.loc[hitters, "PA"], errors="coerce").fillna(500) / 4.5).clip(lower=1)

    for cat in ["R", "HR", "RBI", "SB"]:
        if cat in df.columns:
            df.loc[hitters, f"{cat}_pg"] = pd.to_numeric(df.loc[hitters, cat], errors="coerce").fillna(0) / df.loc[hitters, "games"]

    if "OBP" in df.columns:
        df.loc[hitters, "OBP_pg"] = pd.to_numeric(df.loc[hitters, "OBP"], errors="coerce").fillna(0)

    if "G" in df.columns:
        df.loc[pitchers, "games"] = pd.to_numeric(df.loc[pitchers, "G"], errors="coerce").fillna(30)
    else:
        df.loc[pitchers, "games"] = (pd.to_numeric(df.loc[pitchers, "IP"], errors="coerce").fillna(100) / 6).clip(lower=1)

    for cat in ["K", "W", "SV"]:
        if cat in df.columns:
            df.loc[pitchers, f"{cat}_pg"] = pd.to_numeric(df.loc[pitchers, cat], errors="coerce").fillna(0) / df.loc[pitchers, "games"]

    for cat in ["ERA", "WHIP"]:
        if cat in df.columns:
            df.loc[pitchers, f"{cat}_pg"] = pd.to_numeric(df.loc[pitchers, cat], errors="coerce").fillna(5)

    return df


def score_hitter(row: pd.Series, weights: Optional[dict] = None) -> float:
    if weights is None:
        weights = {"R": 1.0, "HR": 1.0, "RBI": 1.0, "SB": 1.0, "OBP": 1.0}
    score = 0
    for cat, w in weights.items():
        val = row.get(f"{cat}_pg", 0)
        if pd.notna(val):
            score += val * w
    return score


def score_pitcher(row: pd.Series, weights: Optional[dict] = None) -> float:
    if weights is None:
        weights = {"K": 1.0, "W": 1.0, "SV": 1.0, "ERA": 1.0, "WHIP": 1.0}
    score = 0
    for cat, w in weights.items():
        val = row.get(f"{cat}_pg", 0)
        if pd.notna(val):
            if cat == "ERA":
                score += (4.50 - val) * w
            elif cat == "WHIP":
                score += (1.35 - val) * w
            else:
                score += val * w
    return score


def is_eligible(player_positions: str, slot_positions: list) -> bool:
    if slot_positions is None:
        return True
    for ep in slot_positions:
        if ep in player_positions:
            return True
    return False


def recommend_lineup(
    roster_df: pd.DataFrame,
    h_weights: Optional[dict] = None,
    p_weights: Optional[dict] = None,
) -> dict:
    """Generate optimal lineup recommendation."""
    df = compute_per_game_rates(roster_df)

    hitters = df[df["player_type"] == "hitter"].copy()
    pitchers = df[df["player_type"] == "pitcher"].copy()

    hitters["daily_score"] = hitters.apply(lambda r: score_hitter(r, h_weights), axis=1)
    pitchers["daily_score"] = pitchers.apply(lambda r: score_pitcher(r, p_weights), axis=1)

    slot_order = [
        ("C", ["C"]),
        ("1B", ["1B"]),
        ("2B", ["2B"]),
        ("3B", ["3B"]),
        ("SS", ["SS"]),
        ("IF", ["1B", "2B", "3B", "SS"]),
        ("OF1", ["OF"]),
        ("OF2", ["OF"]),
        ("OF3", ["OF"]),
        ("UTIL", None),
    ]

    lineup = {}
    used = set()
    reasoning = {}
    hitters_sorted = hitters.sort_values("daily_score", ascending=False)

    for slot_name, eligible_pos in slot_order:
        for idx, row in hitters_sorted.iterrows():
            if row["name"] in used:
                continue
            player_pos = str(row.get("positions", "UTIL"))
            if not is_eligible(player_pos, eligible_pos):
                continue
            lineup[slot_name] = row["name"]
            used.add(row["name"])
            reasoning[row["name"]] = f"Start at {slot_name} (score: {row['daily_score']:.3f})"
            break

    bench_hitters = [r["name"] for _, r in hitters.iterrows() if r["name"] not in used]

    pitcher_used = set()
    pitchers_sorted = pitchers.sort_values("daily_score", ascending=False)

    sp_players = pitchers_sorted[pitchers_sorted["positions"].str.contains("SP", na=False)]
    sp_count = 0
    for _, row in sp_players.iterrows():
        if sp_count >= config.PITCHER_SLOTS.get("SP", 5):
            break
        lineup[f"SP{sp_count + 1}"] = row["name"]
        pitcher_used.add(row["name"])
        reasoning[row["name"]] = f"Start at SP{sp_count + 1} (score: {row['daily_score']:.3f})"
        sp_count += 1

    rp_players = pitchers_sorted[
        (pitchers_sorted["positions"].str.contains("RP", na=False))
        & (~pitchers_sorted["name"].isin(pitcher_used))
    ]
    rp_count = 0
    for _, row in rp_players.iterrows():
        if rp_count >= config.PITCHER_SLOTS.get("RP", 3):
            break
        lineup[f"RP{rp_count + 1}"] = row["name"]
        pitcher_used.add(row["name"])
        reasoning[row["name"]] = f"Start at RP{rp_count + 1} (score: {row['daily_score']:.3f})"
        rp_count += 1

    bench_pitchers = [r["name"] for _, r in pitchers.iterrows() if r["name"] not in pitcher_used]

    return {
        "lineup": lineup,
        "bench_hitters": bench_hitters,
        "bench_pitchers": bench_pitchers,
        "reasoning": reasoning,
        "hitter_scores": hitters[["name", "positions", "daily_score"]].sort_values("daily_score", ascending=False),
        "pitcher_scores": pitchers[["name", "positions", "daily_score"]].sort_values("daily_score", ascending=False),
    }


def display_lineup(result: dict):
    lineup = result["lineup"]

    print("\n  RECOMMENDED LINEUP")
    print("  " + "=" * 60)

    print("\n  HITTERS")
    print("  " + "-" * 40)
    for slot in ["C", "1B", "2B", "3B", "SS", "IF", "OF1", "OF2", "OF3", "UTIL"]:
        player = lineup.get(slot, "--- EMPTY ---")
        display_slot = slot.replace("OF1", "OF").replace("OF2", "OF").replace("OF3", "OF")
        print(f"    {display_slot:<6} {player}")

    print("\n  PITCHERS")
    print("  " + "-" * 40)
    for i in range(1, config.PITCHER_SLOTS.get("SP", 5) + 1):
        player = lineup.get(f"SP{i}", "--- EMPTY ---")
        print(f"    SP    {player}")
    for i in range(1, config.PITCHER_SLOTS.get("RP", 3) + 1):
        player = lineup.get(f"RP{i}", "--- EMPTY ---")
        print(f"    RP    {player}")

    print("\n  BENCH")
    print("  " + "-" * 40)
    for name in result.get("bench_hitters", []):
        print(f"    BE    {name}")
    for name in result.get("bench_pitchers", []):
        print(f"    BE    {name}")
    print()


def display_start_sit(result: dict):
    print("\n  START/SIT ANALYSIS")
    print("  " + "=" * 65)

    bench_h = set(result["bench_hitters"])
    bench_p = set(result["bench_pitchers"])

    print("\n  Hitter Rankings:")
    print("  " + "-" * 60)
    print(f"    {'':5} {'Name':<25} {'Pos':<12} {'Score':>6}")
    print("  " + "-" * 60)
    for _, row in result["hitter_scores"].iterrows():
        tag = "BENCH" if row["name"] in bench_h else "START"
        pos = str(row["positions"])[:11]
        print(f"    {tag:<5} {row['name']:<25} {pos:<12} {row['daily_score']:.4f}")

    print("\n  Pitcher Rankings:")
    print("  " + "-" * 60)
    print(f"    {'':5} {'Name':<25} {'Pos':<12} {'Score':>6}")
    print("  " + "-" * 60)
    for _, row in result["pitcher_scores"].iterrows():
        tag = "BENCH" if row["name"] in bench_p else "START"
        pos = str(row["positions"])[:11]
        print(f"    {tag:<5} {row['name']:<25} {pos:<12} {row['daily_score']:.4f}")
