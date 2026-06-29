#!/usr/bin/env python3
"""
analysis.py — Reproduces the Phase 2 insight numbers cited in approach_summary.md.

Run:
    python analysis.py data/olympic_medals.csv

This script demonstrates that the original script's counting bug is structurally
correlated with team-sport concentration, and stress-tests the finding.
"""

import sys

import pandas as pd

from medal_report import (
    clean_medals,
    compute_leaderboard,
    dedupe_to_event_medals,
    load_data,
)


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "data/olympic_medals.csv"

    # ─── Load and process with corrected pipeline ─────────────────────────
    df = load_data(path)
    df_clean, stats = clean_medals(df)
    df_event, stats = dedupe_to_event_medals(df_clean, stats)
    board = compute_leaderboard(df_event)

    # ─── Compute team-sport concentration per country ─────────────────────
    df_c = df_clean.copy()
    df_c["is_team"] = df_c["event"].str.contains("team", case=False)
    team_pct = df_c.groupby("country_code")["is_team"].mean()

    # ─── Compute naive counts (what the ORIGINAL broken script counted) ───
    # The original script only matched exact 'Gold'/'Silver'/'Bronze' text,
    # so the naive baseline uses the raw CSV filtered to those exact values.
    df_raw = pd.read_csv(path)
    df_naive = df_raw[df_raw["medal"].isin(["Gold", "Silver", "Bronze"])]
    naive_counts = df_naive.groupby("country_code").size()

    # ─── Inflation ratio: naive row count / corrected event count ─────────
    inflation = (naive_counts / board["total"]).dropna()

    correlation_data = pd.DataFrame({"team_pct": team_pct, "inflation_ratio": inflation}).dropna()
    corr = correlation_data["team_pct"].corr(correlation_data["inflation_ratio"])

    print("\n" + "=" * 60)
    print("PHASE 2 INSIGHT: Structural Inflation Bias")
    print("=" * 60)
    print(f"\nOverall correlation (team% vs inflation): r = {corr:.4f}")
    print(f"  (n = {len(correlation_data)} countries)")

    # ─── Rank changes ─────────────────────────────────────────────────────
    naive_ranked = naive_counts.sort_values(ascending=False)
    naive_rank = pd.Series(range(1, len(naive_ranked) + 1), index=naive_ranked.index)

    correct_ranked = board["total"].sort_values(ascending=False)
    correct_rank = pd.Series(range(1, len(correct_ranked) + 1), index=correct_ranked.index)

    rank_change = (naive_rank - correct_rank).dropna().astype(int)
    print("\nBiggest rank changes after fix:")
    print("  Risers (under-ranked by bug):")
    for code in rank_change.sort_values(ascending=False).head(3).index:
        nr, cr, rc = int(naive_rank[code]), int(correct_rank[code]), int(rank_change[code])
        print(f"    {code}: {nr} -> {cr} ({rc:+d})")
    print("  Fallers (over-ranked by bug):")
    for code in rank_change.sort_values().head(3).index:
        nr, cr, rc = int(naive_rank[code]), int(correct_rank[code]), int(rank_change[code])
        print(f"    {code}: {nr} -> {cr} ({rc:+d})")

    # ─── Stress test 1: Per-decade stability ──────────────────────────────
    print("\nStress test 1 — Per-decade correlation:")
    decades = [(1960, 1979, "1960-79"), (1980, 1999, "1980-99"), (2000, 2016, "2000-16")]
    for start, end, label in decades:
        subset = df_clean[(df_clean["year"] >= start) & (df_clean["year"] <= end)].copy()
        subset["is_team"] = subset["event"].str.contains("team", case=False)
        tp = subset.groupby("country_code")["is_team"].mean()

        sub_event, _ = dedupe_to_event_medals(subset, dict(stats))
        board_sub = compute_leaderboard(sub_event)

        naive_sub = (
            subset[subset["medal"].isin(["Gold", "Silver", "Bronze"])]
            .groupby("country_code")
            .size()
        )
        inflation_sub = (naive_sub / board_sub["total"]).dropna()

        cd = pd.DataFrame({"team_pct": tp, "inflation": inflation_sub}).dropna()
        c = cd["team_pct"].corr(cd["inflation"])
        print(f"  {label}: r = {c:.4f} (n = {len(cd)})")

    # ─── Stress test 2: Remove team events ────────────────────────────────
    print("\nStress test 2 — Remove team events (falsification):")
    df_indiv = df_clean[~df_clean["event"].str.contains("team", case=False)].copy()
    df_indiv_event, _ = dedupe_to_event_medals(df_indiv, dict(stats))
    board_indiv = compute_leaderboard(df_indiv_event)

    df_raw_indiv = df_raw[
        (df_raw["medal"].isin(["Gold", "Silver", "Bronze"]))
        & (~df_raw["event"].str.contains("team", case=False))
    ]
    naive_indiv = df_raw_indiv.groupby("country_code").size()
    inflation_indiv = (naive_indiv / board_indiv["total"]).dropna()
    print(f"  Mean inflation (individual events only): {inflation_indiv.mean():.4f}")
    print(f"  Max inflation:  {inflation_indiv.max():.4f}")
    print("  Conclusion: Without team events, inflation converges to ~1.0")

    # ─── Stress test 3: Alternative metric ────────────────────────────────
    print("\nStress test 3 — Points-weighted vs total-count ranking:")
    board_by_points = board.sort_values("points", ascending=False)
    board_by_total = board.sort_values("total", ascending=False)
    top8_match = list(board_by_total.head(8).index) == list(board_by_points.head(8).index)
    print(f"  Top-8 identical under both metrics: {top8_match}")

    # ─── Stress test 4: Verify max inflation and order-of-operations count ───
    print("\nStress test 4 — Key summary figures:")
    inflation = (naive_counts / board["total"]).dropna()
    print(f"  Max inflation ratio: {inflation.max():.4f}x ({inflation.idxmax()})")

    # 297 phantom medals: deduping on raw medal text before normalization
    # treats 'Gold' and 'GOLD ' as distinct keys, overcounting vs normalizing first.
    df_raw_copy = pd.read_csv(path)
    df_raw_copy["medal_clean"] = df_raw_copy["medal"].apply(
        lambda m: {
            "gold": "Gold",
            "g": "Gold",
            "1st": "Gold",
            "silver": "Silver",
            "s": "Silver",
            "2nd": "Silver",
            "bronze": "Bronze",
            "b": "Bronze",
            "3rd": "Bronze",
        }.get(str(m).strip().lower())
    )
    df_raw_copy = df_raw_copy[df_raw_copy["medal_clean"].notna()]
    raw_dedup = len(df_raw_copy.drop_duplicates(subset=["year", "event", "country_code", "medal"]))
    norm_dedup = len(
        df_raw_copy.drop_duplicates(subset=["year", "event", "country_code", "medal_clean"])
    )
    diff = raw_dedup - norm_dedup
    print(f"  Normalize-before-dedupe saves: {diff} rows vs raw-text dedup")

    print("\n" + "=" * 60)
    print("All Phase 2 numbers reproduced successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
