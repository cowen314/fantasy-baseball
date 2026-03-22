"""
Pitching Planner
-----------------
SP start planning, 2-start pitcher identification, and streaming analysis.
"""

import pandas as pd


def classify_pitchers(roster_df: pd.DataFrame) -> dict:
    pitchers = roster_df[roster_df["player_type"] == "pitcher"].copy()
    sps = pitchers[pitchers["positions"].str.contains("SP", na=False)].copy()
    rps = pitchers[pitchers["positions"].str.contains("RP", na=False)].copy()
    if "dollar_value" in sps.columns:
        sps = sps.sort_values("dollar_value", ascending=False)
    if "dollar_value" in rps.columns:
        rps = rps.sort_values("dollar_value", ascending=False)
    return {"SP": sps, "RP": rps}


def analyze_sp_value(sps: pd.DataFrame) -> pd.DataFrame:
    df = sps.copy()

    # Estimate starts — use GS if available, else IP/6, minimum 1
    if "GS" in df.columns:
        df["est_starts"] = pd.to_numeric(df["GS"], errors="coerce").fillna(0)
    else:
        df["est_starts"] = 0

    # Fallback: estimate from IP
    ip = pd.to_numeric(df["IP"], errors="coerce").fillna(0)
    df.loc[df["est_starts"] < 1, "est_starts"] = (ip[df["est_starts"] < 1] / 6).clip(
        lower=1
    )
    df["est_starts"] = df["est_starts"].clip(lower=1)  # safety

    df["K_per_start"] = (
        pd.to_numeric(df["K"], errors="coerce").fillna(0) / df["est_starts"]
    )
    df["W_per_start"] = (
        pd.to_numeric(df["W"], errors="coerce").fillna(0) / df["est_starts"]
    )
    df["IP_per_start"] = ip / df["est_starts"]

    era = pd.to_numeric(df["ERA"], errors="coerce").fillna(5)
    whip = pd.to_numeric(df["WHIP"], errors="coerce").fillna(1.5)

    df["era_risk"] = pd.cut(
        era,
        bins=[0, 3.00, 3.50, 4.00, 4.50, 99],
        labels=["Elite", "Good", "Average", "Risky", "Sit"],
    )

    df["start_value"] = (
        df["K_per_start"] * 0.4
        + df["W_per_start"] * 2.0
        + (4.50 - era) * 0.3
        + (1.35 - whip) * 1.0
    )

    return df


def find_streaming_candidates(
    all_pitchers: pd.DataFrame,
    roster_names: list,
    n: int = 10,
) -> pd.DataFrame:
    fa = all_pitchers[
        (~all_pitchers["name"].isin(roster_names))
        & (all_pitchers["positions"].str.contains("SP", na=False))
    ].copy()

    # Only consider pitchers with meaningful IP
    ip = pd.to_numeric(fa["IP"], errors="coerce").fillna(0)
    fa = fa[ip >= 50]

    fa = analyze_sp_value(fa)

    era = pd.to_numeric(fa["ERA"], errors="coerce").fillna(5)
    fa = fa[era <= 4.50]

    return fa.nlargest(n, "start_value")


def display_pitching_plan(roster_df: pd.DataFrame, all_pitchers: pd.DataFrame = None):
    pitchers = classify_pitchers(roster_df)
    sps = pitchers["SP"]
    rps = pitchers["RP"]

    print("\n  PITCHING PLANNER")
    print("  " + "=" * 70)

    print("\n  YOUR STARTING PITCHERS")
    print("  " + "-" * 70)
    if len(sps) > 0:
        sp_analysis = analyze_sp_value(sps)
        print(
            f"  {'Name':<25} {'K/GS':>5} {'W/GS':>5} {'ERA':>5} {'WHIP':>6} {'Risk':<8} {'Value':>6}"
        )
        print("  " + "-" * 70)
        for _, row in sp_analysis.sort_values(
            "start_value", ascending=False
        ).iterrows():
            print(
                f"  {row['name']:<25} "
                f"{row['K_per_start']:>5.1f} "
                f"{row['W_per_start']:>5.2f} "
                f"{row.get('ERA', 0):>5.2f} "
                f"{row.get('WHIP', 0):>6.3f} "
                f"{str(row['era_risk']):<8} "
                f"{row['start_value']:>6.2f}"
            )
    else:
        print("  No SPs on roster.")

    print("\n  YOUR RELIEF PITCHERS")
    print("  " + "-" * 70)
    if len(rps) > 0:
        print(f"  {'Name':<25} {'SV':>4} {'K':>5} {'ERA':>5} {'WHIP':>6}")
        print("  " + "-" * 70)
        for _, row in rps.iterrows():
            print(
                f"  {row['name']:<25} "
                f"{row.get('SV', 0):>4.0f} "
                f"{row.get('K', 0):>5.0f} "
                f"{row.get('ERA', 0):>5.2f} "
                f"{row.get('WHIP', 0):>6.3f}"
            )
    else:
        print("  No RPs on roster.")

    if all_pitchers is not None:
        print("\n  TOP STREAMING CANDIDATES (Free Agents)")
        print("  " + "-" * 70)
        roster_names = roster_df["name"].tolist()
        streamers = find_streaming_candidates(all_pitchers, roster_names, n=10)
        if len(streamers) > 0:
            print(
                f"  {'Name':<25} {'K/GS':>5} {'W/GS':>5} {'ERA':>5} {'WHIP':>6} {'Value':>6}"
            )
            print("  " + "-" * 70)
            for _, row in streamers.iterrows():
                print(
                    f"  {row['name']:<25} "
                    f"{row['K_per_start']:>5.1f} "
                    f"{row['W_per_start']:>5.2f} "
                    f"{row.get('ERA', 0):>5.2f} "
                    f"{row.get('WHIP', 0):>6.3f} "
                    f"{row['start_value']:>6.2f}"
                )
    print()
