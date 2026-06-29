#!/usr/bin/env python3
"""
medal_report.py  --  Olympic Medal Leaderboard Reporter
=========================================================
Reads the Olympic medals dataset and produces a corrected country medal
leaderboard, properly handling team-event deduplication, medal text
normalization, and data quality issues.

Usage:
    python medal_report.py <input_csv>

Example:
    python medal_report.py data/olympic_medals.csv
"""

import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.use("Agg")


# ─── Configuration ────────────────────────────────────────────────────────────
TOP_N = 10
MEDAL_RANK = {"Gold": 1, "Silver": 2, "Bronze": 3}


# ─── Medal Normalization Map ──────────────────────────────────────────────────
_MEDAL_NORMALIZE: dict[str, str] = {
    "gold": "Gold",
    "g": "Gold",
    "1st": "Gold",
    "silver": "Silver",
    "s": "Silver",
    "2nd": "Silver",
    "bronze": "Bronze",
    "b": "Bronze",
    "3rd": "Bronze",
}


def normalize_medal(value: str) -> str | None:
    """Normalize medal text to Gold/Silver/Bronze or None if unrecognized."""
    cleaned = str(value).strip().lower()
    return _MEDAL_NORMALIZE.get(cleaned)


def load_data(path: str | Path) -> pd.DataFrame:
    """Load the CSV and perform schema validation."""
    filepath = Path(path)
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")

    df = pd.read_csv(filepath)

    required_cols = {
        "year",
        "host_city",
        "host_country",
        "country_code",
        "country_name",
        "sport",
        "event",
        "athlete_name",
        "medal",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    print(f"Loaded {len(df):,} rows from {filepath}")
    return df


def recover_country_codes(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Recover missing country_code values from country_name where possible.

    Some rows have a valid country_name but a null country_code due to a data
    quality issue. Without recovery, groupby silently drops these rows from the
    leaderboard while they are still counted in the reconciliation total —
    causing the two numbers to diverge.

    Returns:
        Tuple of (DataFrame with codes recovered, count of rows recovered)
    """
    null_mask = df["country_code"].isna() & df["country_name"].notna()
    if not null_mask.any():
        return df, 0

    # Build name→code map from rows that have both fields populated
    name_to_code = (
        df[df["country_code"].notna()].groupby("country_name")["country_code"].first().to_dict()
    )

    df = df.copy()
    recovered = df.loc[null_mask, "country_name"].map(name_to_code)
    df.loc[null_mask, "country_code"] = recovered

    # Count how many were successfully recovered vs still null
    still_null = df["country_code"].isna().sum()
    recovered_count = int(null_mask.sum()) - still_null
    return df, recovered_count


def clean_medals(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Normalize medal text and report what was cleaned.

    Returns:
        Tuple of (cleaned DataFrame, stats dict with counts at each stage)
    """
    stats: dict[str, int] = {"raw_rows": len(df)}

    # Step 1: Recover missing country codes from country_name
    df, recovered = recover_country_codes(df)
    stats["country_codes_recovered"] = recovered
    if recovered > 0:
        print(f"Recovered {recovered} missing country_code values from country_name")

    # Step 2: Normalize medal values
    df = df.copy()
    df["medal_clean"] = df["medal"].apply(normalize_medal)

    unrecognized = df[df["medal_clean"].isna()]
    stats["unrecognized_medals"] = len(unrecognized)
    if len(unrecognized) > 0:
        print(f"WARNING: {len(unrecognized)} rows with unrecognized medal values dropped")
        print(f"  Values: {unrecognized['medal'].unique().tolist()}")

    df = df[df["medal_clean"].notna()].copy()
    stats["after_normalization"] = len(df)

    # Step 3: Remove exact duplicate rows
    before_dedup = len(df)
    df = df.drop_duplicates()
    exact_dupes = before_dedup - len(df)
    stats["exact_duplicates_removed"] = exact_dupes
    stats["after_exact_dedup"] = len(df)
    if exact_dupes > 0:
        print(f"Removed {exact_dupes} exact duplicate rows")

    # Step 4: Drop any remaining rows with null country_code (unrecoverable)
    still_null = df["country_code"].isna().sum()
    stats["unrecoverable_null_country"] = int(still_null)
    if still_null > 0:
        print(f"WARNING: {still_null} rows with unrecoverable null country_code dropped")
        df = df[df["country_code"].notna()].copy()
    stats["after_null_country_drop"] = len(df)

    return df, stats


def is_team_event(event_name: str) -> bool:
    """Determine if an event is a team event based on naming convention."""
    return "team" in str(event_name).lower()


def dedupe_to_event_medals(
    df: pd.DataFrame, stats: dict[str, int]
) -> tuple[pd.DataFrame, dict[str, int]]:
    """
    Deduplicate to event-level medals.

    - Team events: 1 medal per (year, sport, event, country_code).
      If a country has conflicting medal types (data error), take the best.
    - Individual events: 1 medal per (year, sport, event, country_code, athlete_name).
      Deduplicate athlete-level repeats.

    Returns:
        Tuple of (deduped DataFrame, updated stats dict)
    """
    df = df.copy()
    df["is_team"] = df["event"].apply(is_team_event)

    team_df = df[df["is_team"]].copy()
    indiv_df = df[~df["is_team"]].copy()

    stats["team_event_rows"] = len(team_df)
    stats["individual_event_rows"] = len(indiv_df)

    # ─── Team events: one medal per country per event ─────────────────────
    team_key = ["year", "sport", "event", "country_code"]
    team_conflicts = team_df.groupby(team_key)["medal_clean"].nunique()
    conflict_count = int((team_conflicts > 1).sum())
    stats["team_medal_conflicts"] = conflict_count
    if conflict_count > 0:
        print(
            f"DATA QUALITY: {conflict_count} team-event entries have conflicting "
            f"medal types for the same country (resolved by taking best medal)"
        )

    # Take the best medal per team-event-country (Gold > Silver > Bronze)
    team_df["medal_rank"] = team_df["medal_clean"].map(MEDAL_RANK)
    team_deduped = (
        team_df.sort_values("medal_rank")
        .drop_duplicates(subset=team_key, keep="first")
        .drop(columns=["medal_rank"])
    )

    # ─── Individual events: one medal per athlete per event ───────────────
    indiv_key = ["year", "sport", "event", "country_code", "athlete_name", "medal_clean"]
    indiv_dupes = indiv_df.duplicated(subset=indiv_key, keep="first").sum()
    stats["individual_athlete_dupes_removed"] = int(indiv_dupes)
    if indiv_dupes > 0:
        print(f"Removed {indiv_dupes} duplicate athlete entries in individual events")
    indiv_deduped = indiv_df.drop_duplicates(subset=indiv_key, keep="first")

    # ─── Recombine ────────────────────────────────────────────────────────
    result = pd.concat([team_deduped, indiv_deduped], ignore_index=True)
    result = result.drop(columns=["is_team"], errors="ignore")

    stats["final_event_medals"] = len(result)
    stats["team_medals"] = len(team_deduped)
    stats["individual_medals"] = len(indiv_deduped)

    return result, stats


def compute_leaderboard(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute country leaderboard with medal counts and weighted points.

    Returns DataFrame with columns: gold, silver, bronze, total, points
    sorted by total descending, then by gold descending.
    """
    medal_counts = df.groupby(["country_code", "medal_clean"]).size().unstack(fill_value=0)

    for medal in ["Gold", "Silver", "Bronze"]:
        if medal not in medal_counts.columns:
            medal_counts[medal] = 0

    board = pd.DataFrame(
        {
            "gold": medal_counts["Gold"],
            "silver": medal_counts["Silver"],
            "bronze": medal_counts["Bronze"],
        }
    )
    board["total"] = board["gold"] + board["silver"] + board["bronze"]
    board["points"] = board["gold"] * 3 + board["silver"] * 2 + board["bronze"] * 1
    board = board.sort_values(["total", "gold"], ascending=[False, False])

    return board


def make_chart(board: pd.DataFrame, outfile: str = "leaderboard.png") -> str:
    """Generate a bar chart of top nations. Y-axis starts at 0 for honesty."""
    top = board.head(TOP_N)
    fig, ax = plt.subplots(figsize=(10, 6))

    x = range(len(top))
    width = 0.25

    ax.bar([i - width for i in x], top["gold"], width, label="Gold", color="#FFD700")
    ax.bar(x, top["silver"], width, label="Silver", color="#C0C0C0")
    ax.bar([i + width for i in x], top["bronze"], width, label="Bronze", color="#CD7F32")

    ax.set_xlabel("Country")
    ax.set_ylabel("Medals")
    ax.set_title(f"Top {TOP_N} Nations by Total Event Medals (1960-2016)")
    ax.set_xticks(x)
    ax.set_xticklabels(top.index, rotation=45, ha="right")
    ax.set_ylim(0, None)
    ax.legend()
    plt.tight_layout()
    plt.savefig(outfile, dpi=150)
    plt.close(fig)
    print(f"Chart saved to {outfile}")
    return outfile


def print_reconciliation(stats: dict[str, int]) -> None:
    """Print a reconciliation table showing row counts at each pipeline stage."""
    print("\n=== DATA RECONCILIATION ===")
    print(f"  Raw rows loaded:                  {stats['raw_rows']:>7,}")
    print(f"  Country codes recovered:          {stats['country_codes_recovered']:>7,}")
    print(f"  Unrecognized medal values:        {stats['unrecognized_medals']:>7,}")
    print(f"  After medal normalization:        {stats['after_normalization']:>7,}")
    print(f"  Exact duplicates removed:         {stats['exact_duplicates_removed']:>7,}")
    print(f"  Unrecoverable null country:       {stats['unrecoverable_null_country']:>7,}")
    print(f"  After exact dedup + null drop:    {stats['after_null_country_drop']:>7,}")
    print(f"  ├─ Team event rows:               {stats['team_event_rows']:>7,}")
    print(f"  │  Team medal conflicts resolved: {stats['team_medal_conflicts']:>7,}")
    print(f"  │  Final team medals:             {stats['team_medals']:>7,}")
    print(f"  ├─ Individual event rows:         {stats['individual_event_rows']:>7,}")
    print(f"  │  Athlete dupes removed:         {stats['individual_athlete_dupes_removed']:>7,}")
    print(f"  │  Final individual medals:       {stats['individual_medals']:>7,}")
    print(f"  └─ TOTAL event-level medals:      {stats['final_event_medals']:>7,}")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python medal_report.py <input_csv>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]

    # Pipeline
    df = load_data(path)
    df, stats = clean_medals(df)
    df, stats = dedupe_to_event_medals(df, stats)
    board = compute_leaderboard(df)

    # Output
    print_reconciliation(stats)
    print(f"\n=== MEDAL LEADERBOARD (Top {TOP_N}) ===")
    print(board.head(TOP_N).to_string())
    make_chart(board)

    # Write leaderboard.csv for the automated verifier
    leaderboard_out = board[["total"]].rename(columns={"total": "medals"})
    leaderboard_out.to_csv("leaderboard.csv", index=True, index_label="country_code")
    print("Leaderboard written to leaderboard.csv")


if __name__ == "__main__":
    main()
