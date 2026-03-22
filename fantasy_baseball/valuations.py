"""
Valuation Engine
-----------------
Converts raw projections into auction dollar values using z-score methodology.

Approach:
1. Filter player pool to draftable players (by playing time thresholds)
2. Compute z-scores for each category relative to the replacement level pool
3. For rate stats (OBP, ERA, WHIP), use marginal value approach weighted by volume
4. Sum z-scores across categories for total value
5. Scale to auction dollars using budget constraints
"""

import pandas as pd
import numpy as np
import config
from positions import get_position, get_primary_position


def load_hitters(filepath: str) -> pd.DataFrame:
    """Load and normalize a hitter projection CSV (FanGraphs format)."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    col_map = config.FANGRAPHS_HITTER_COLS

    # Normalize columns - try to find them case-insensitively
    df.columns = df.columns.str.strip()
    available = {c.upper(): c for c in df.columns}

    renamed = {}
    for our_key, fg_key in col_map.items():
        if fg_key.upper() in available:
            renamed[available[fg_key.upper()]] = our_key
        elif our_key.upper() in available:
            renamed[available[our_key.upper()]] = our_key

    df = df.rename(columns=renamed)

    # Ensure required columns exist
    required = ["name", "PA", "R", "HR", "RBI", "SB", "OBP"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required hitter columns: {missing}\n"
            f"Available columns: {list(df.columns)}\n"
            f"Tip: Check that your CSV is a FanGraphs projection export."
        )

    # Clean up
    df["PA"] = pd.to_numeric(df["PA"], errors="coerce").fillna(0)
    for cat in ["R", "HR", "RBI", "SB", "OBP"]:
        df[cat] = pd.to_numeric(df[cat], errors="coerce").fillna(0)

    # Parse positions: use CSV column if available, else look up by MLBAMID
    if "positions" in df.columns:
        df["positions"] = df["positions"].fillna("UTIL").astype(str)
    elif "MLBAMID" in df.columns:
        df["MLBAMID"] = (
            pd.to_numeric(df["MLBAMID"], errors="coerce").fillna(0).astype(int)
        )
        df["positions"] = df["MLBAMID"].apply(lambda x: get_position(x))
        mapped = df[df["positions"] != "UTIL"]
        print(f"  Position lookup: {len(mapped)}/{len(df)} players mapped via MLBAMID")
    else:
        df["positions"] = "UTIL"

    # Add primary position for easy filtering
    df["primary_pos"] = df["positions"].apply(get_primary_position)

    df["player_type"] = "hitter"
    return df


def load_pitchers(filepath: str) -> pd.DataFrame:
    """Load and normalize a pitcher projection CSV (FanGraphs format)."""
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    col_map = config.FANGRAPHS_PITCHER_COLS

    df.columns = df.columns.str.strip()
    available = {c.upper(): c for c in df.columns}

    renamed = {}
    for our_key, fg_key in col_map.items():
        if fg_key.upper() in available:
            renamed[available[fg_key.upper()]] = our_key
        elif our_key.upper() in available:
            renamed[available[our_key.upper()]] = our_key

    df = df.rename(columns=renamed)

    required = ["name", "IP", "K", "W", "SV", "ERA", "WHIP"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing required pitcher columns: {missing}\n"
            f"Available columns: {list(df.columns)}\n"
            f"Tip: FanGraphs uses 'SO' for strikeouts. Check column names."
        )

    df["IP"] = pd.to_numeric(df["IP"], errors="coerce").fillna(0)
    for cat in ["K", "W", "SV", "ERA", "WHIP"]:
        df[cat] = pd.to_numeric(df[cat], errors="coerce").fillna(0)

    # Classify SP vs RP based on saves and IP
    if "positions" not in df.columns:
        df["positions"] = np.where(df["SV"] >= 5, "RP", "SP")

    df["player_type"] = "pitcher"
    return df


def filter_draftable(df: pd.DataFrame, player_type: str) -> pd.DataFrame:
    """Filter to players likely to be drafted based on playing time."""
    if player_type == "hitter":
        return df[df["PA"] >= config.MIN_PA].copy()
    else:
        return df[df["IP"] >= config.MIN_IP].copy()


def compute_hitter_zscores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute z-scores for hitter categories.

    Counting stats: straightforward z-score
    Rate stats (OBP): marginal approach — convert to counting-like metric
      using PA-weighted marginal OBP above replacement, so high-PA players
      get appropriate credit for maintaining a high rate over more PAs.
    """
    df = df.copy()

    # Counting stats - simple z-scores
    for cat in ["R", "HR", "RBI", "SB"]:
        mean = df[cat].mean()
        std = df[cat].std()
        if std > 0:
            df[f"z_{cat}"] = (df[cat] - mean) / std
        else:
            df[f"z_{cat}"] = 0.0

    # OBP - marginal value approach
    # Value = PA * (player_OBP - replacement_OBP)
    # This rewards both high OBP AND high PA
    replacement_obp = df["OBP"].median()  # use median as proxy for replacement
    df["OBP_marginal"] = df["PA"] * (df["OBP"] - replacement_obp)
    mean_m = df["OBP_marginal"].mean()
    std_m = df["OBP_marginal"].std()
    if std_m > 0:
        df["z_OBP"] = (df["OBP_marginal"] - mean_m) / std_m
    else:
        df["z_OBP"] = 0.0

    # Total z-score (equal weight across categories)
    z_cols = [f"z_{cat}" for cat in ["R", "HR", "RBI", "SB", "OBP"]]
    df["z_total"] = df[z_cols].sum(axis=1)

    return df


def compute_pitcher_zscores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute z-scores for pitcher categories.

    Counting stats (K, W, SV): straightforward z-score
    Rate stats (ERA, WHIP): marginal approach weighted by IP
      For inverse stats, we flip the sign so lower = better = positive z-score.
    """
    df = df.copy()

    # Counting stats
    for cat in ["K", "W", "SV"]:
        mean = df[cat].mean()
        std = df[cat].std()
        if std > 0:
            df[f"z_{cat}"] = (df[cat] - mean) / std
        else:
            df[f"z_{cat}"] = 0.0

    # ERA - marginal (inverted: lower is better)
    replacement_era = (
        df.loc[df["IP"] >= 50, "ERA"].median()
        if len(df[df["IP"] >= 50]) > 0
        else df["ERA"].median()
    )
    df["ERA_marginal"] = df["IP"] * (
        replacement_era - df["ERA"]
    )  # positive = better than replacement
    mean_m = df["ERA_marginal"].mean()
    std_m = df["ERA_marginal"].std()
    if std_m > 0:
        df["z_ERA"] = (df["ERA_marginal"] - mean_m) / std_m
    else:
        df["z_ERA"] = 0.0

    # WHIP - marginal (inverted: lower is better)
    replacement_whip = (
        df.loc[df["IP"] >= 50, "WHIP"].median()
        if len(df[df["IP"] >= 50]) > 0
        else df["WHIP"].median()
    )
    df["WHIP_marginal"] = df["IP"] * (replacement_whip - df["WHIP"])
    mean_m = df["WHIP_marginal"].mean()
    std_m = df["WHIP_marginal"].std()
    if std_m > 0:
        df["z_WHIP"] = (df["WHIP_marginal"] - mean_m) / std_m
    else:
        df["z_WHIP"] = 0.0

    z_cols = [f"z_{cat}" for cat in ["K", "W", "SV", "ERA", "WHIP"]]
    df["z_total"] = df[z_cols].sum(axis=1)

    return df


def zscores_to_dollars(
    hitters: pd.DataFrame,
    pitchers: pd.DataFrame,
    hitter_budget_pct: float = config.HITTER_BUDGET_PCT,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convert z-scores to auction dollar values.

    Method:
    1. Determine how many players at each position are "draftable" (positive value)
    2. Split the total league budget between hitters and pitchers
    3. Reserve $1 per roster spot (minimum bid)
    4. Distribute remaining dollars proportional to z-score share
    """
    total_budget = config.TOTAL_LEAGUE_BUDGET

    # Budget split
    hitter_budget = total_budget * hitter_budget_pct
    pitcher_budget = total_budget * (1 - hitter_budget_pct)

    # Number of rostered players
    n_hitters = config.HITTERS_DRAFTED
    n_pitchers = config.PITCHERS_DRAFTED

    # Reserve $1 minimum per player
    hitter_pool = hitter_budget - n_hitters * config.MIN_BID
    pitcher_pool = pitcher_budget - n_pitchers * config.MIN_BID

    # Take top N players by z-score as the "draftable" pool
    h_sorted = hitters.nlargest(n_hitters, "z_total").copy()
    p_sorted = pitchers.nlargest(n_pitchers, "z_total").copy()

    # Shift z-scores so the lowest draftable player is at 0
    h_min_z = h_sorted["z_total"].min()
    h_sorted["z_adjusted"] = h_sorted["z_total"] - h_min_z

    p_min_z = p_sorted["z_total"].min()
    p_sorted["z_adjusted"] = p_sorted["z_total"] - p_min_z

    # Convert to dollars: each player's share of the available pool
    h_z_sum = h_sorted["z_adjusted"].sum()
    if h_z_sum > 0:
        h_sorted["dollar_value"] = (
            h_sorted["z_adjusted"] / h_z_sum * hitter_pool
        ) + config.MIN_BID
    else:
        h_sorted["dollar_value"] = config.MIN_BID

    p_z_sum = p_sorted["z_adjusted"].sum()
    if p_z_sum > 0:
        p_sorted["dollar_value"] = (
            p_sorted["z_adjusted"] / p_z_sum * pitcher_pool
        ) + config.MIN_BID
    else:
        p_sorted["dollar_value"] = config.MIN_BID

    # Round to nearest dollar for auction usability
    h_sorted["dollar_value"] = h_sorted["dollar_value"].round(0).astype(int)
    p_sorted["dollar_value"] = p_sorted["dollar_value"].round(0).astype(int)

    # Also assign values to undrafted players (for reference)
    hitters = hitters.merge(
        h_sorted[["name", "dollar_value", "z_adjusted"]],
        on="name",
        how="left",
        suffixes=("", "_drafted"),
    )
    hitters["dollar_value"] = hitters["dollar_value"].fillna(config.MIN_BID).astype(int)
    hitters["z_adjusted"] = hitters["z_adjusted"].fillna(0)

    pitchers = pitchers.merge(
        p_sorted[["name", "dollar_value", "z_adjusted"]],
        on="name",
        how="left",
        suffixes=("", "_drafted"),
    )
    pitchers["dollar_value"] = (
        pitchers["dollar_value"].fillna(config.MIN_BID).astype(int)
    )
    pitchers["z_adjusted"] = pitchers["z_adjusted"].fillna(0)

    return hitters, pitchers


def assign_tiers(df: pd.DataFrame, n_tiers: int = 8) -> pd.DataFrame:
    """
    Assign players to tiers using Jenks-like natural breaks on dollar value.
    Falls back to quantile-based tiers for simplicity.
    """
    df = df.copy()
    df = df.sort_values("dollar_value", ascending=False)

    # Simple quantile-based tiers
    draftable = df[df["dollar_value"] > config.MIN_BID]
    if len(draftable) > 0:
        tier_values = pd.qcut(
            draftable["dollar_value"].rank(method="first"),
            q=min(n_tiers, len(draftable)),
            labels=range(1, min(n_tiers, len(draftable)) + 1),
        ).astype(int)
        tier_map = dict(zip(draftable["name"], tier_values))
        df["tier"] = df["name"].map(tier_map).fillna(n_tiers + 1).astype(int)
    else:
        df["tier"] = n_tiers + 1

    return df


def compute_category_strengths(df: pd.DataFrame, categories: list[str]) -> pd.DataFrame:
    """Add per-player category strength indicators (above/below average)."""
    df = df.copy()
    for cat in categories:
        z_col = f"z_{cat}"
        if z_col in df.columns:
            df[f"{cat}_strength"] = pd.cut(
                df[z_col],
                bins=[-np.inf, -1, -0.5, 0.5, 1, np.inf],
                labels=["--", "-", "avg", "+", "++"],
            )
    return df


def generate_cheatsheet(
    hitters: pd.DataFrame,
    pitchers: pd.DataFrame,
) -> pd.DataFrame:
    """
    Combine hitters and pitchers into a single ranked cheat sheet.
    """
    h_cats = ["R", "HR", "RBI", "SB", "OBP"]
    p_cats = ["K", "W", "SV", "ERA", "WHIP"]

    # Select display columns for hitters
    h_display_cols = ["name", "positions", "dollar_value", "tier"]
    h_display_cols += h_cats
    h_display_cols += [f"z_{c}" for c in h_cats]
    h_display_cols += [
        f"{c}_strength" for c in h_cats if f"{c}_strength" in hitters.columns
    ]
    h_display_cols = [c for c in h_display_cols if c in hitters.columns]

    h_out = hitters[h_display_cols].copy()
    h_out["player_type"] = "Hitter"

    # Select display columns for pitchers
    p_display_cols = ["name", "positions", "dollar_value", "tier"]
    p_display_cols += p_cats
    p_display_cols += [f"z_{c}" for c in p_cats]
    p_display_cols += [
        f"{c}_strength" for c in p_cats if f"{c}_strength" in pitchers.columns
    ]
    p_display_cols = [c for c in p_display_cols if c in pitchers.columns]

    p_out = pitchers[p_display_cols].copy()
    p_out["player_type"] = "Pitcher"

    # Combine and sort by dollar value
    combined = pd.concat([h_out, p_out], ignore_index=True, sort=False)
    combined = combined.sort_values("dollar_value", ascending=False).reset_index(
        drop=True
    )
    combined.index = combined.index + 1  # 1-based ranking
    combined.index.name = "rank"

    return combined
