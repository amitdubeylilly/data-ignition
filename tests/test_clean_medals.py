"""Tests for data cleaning pipeline."""

import pandas as pd

from medal_report import clean_medals, recover_country_codes


class TestRecoverCountryCodes:
    """Test null country_code recovery from country_name."""

    def test_recovers_from_country_name(self) -> None:
        """Rows with null country_code but valid country_name should be recovered."""
        df = pd.DataFrame(
            {
                "year": [2016, 2016],
                "host_city": ["Rio", "Rio"],
                "host_country": ["BRA", "BRA"],
                "country_code": ["USA", None],  # second row has null code
                "country_name": ["United States", "United States"],
                "sport": ["Swimming", "Athletics"],
                "event": ["Swimming event", "Athletics event"],
                "athlete_name": ["A", "B"],
                "medal": ["Gold", "Silver"],
            }
        )
        result, recovered = recover_country_codes(df)
        assert recovered == 1
        assert result.iloc[1]["country_code"] == "USA"

    def test_no_nulls_returns_zero(self, sample_individual_data) -> None:
        """Should return 0 recovered when no nulls exist."""
        _, recovered = recover_country_codes(sample_individual_data)
        assert recovered == 0

    def test_unrecoverable_remains_null(self) -> None:
        """Rows with null code and unknown country_name stay null (no map entry)."""
        df = pd.DataFrame(
            {
                "year": [2016, 2016],
                "host_city": ["Rio", "Rio"],
                "host_country": ["BRA", "BRA"],
                "country_code": ["USA", None],
                "country_name": ["United States", "Unknown Nation XYZ"],
                "sport": ["Swimming", "Swimming"],
                "event": ["Swimming event", "Athletics event"],
                "athlete_name": ["A", "B"],
                "medal": ["Gold", "Silver"],
            }
        )
        result, recovered = recover_country_codes(df)
        assert recovered == 0
        assert pd.isna(result.iloc[1]["country_code"])


class TestCleanMedals:
    """Test medal cleaning (normalization + exact dedup)."""

    def test_normalizes_all_medal_variants(self, sample_dirty_medals) -> None:
        """All known medal variants should be normalized."""
        df, stats = clean_medals(sample_dirty_medals)
        assert stats["unrecognized_medals"] == 0
        assert set(df["medal_clean"].unique()) == {"Gold", "Silver", "Bronze"}

    def test_removes_exact_duplicates(self, sample_with_duplicates) -> None:
        """Exact duplicate rows should be removed."""
        _df, stats = clean_medals(sample_with_duplicates)
        assert stats["exact_duplicates_removed"] == 2
        assert stats["after_exact_dedup"] == 3

    def test_stats_counts_are_consistent(self, sample_individual_data) -> None:
        """Stats should form a consistent pipeline narrative."""
        _df, stats = clean_medals(sample_individual_data)
        assert stats["raw_rows"] == 5
        assert stats["after_normalization"] == 5
        assert stats["exact_duplicates_removed"] == 0
        assert stats["after_exact_dedup"] == 5

    def test_null_country_code_recovered(self, capsys) -> None:
        """Null country_code rows recovered from country_name should be kept."""
        df = pd.DataFrame(
            {
                "year": [2016, 2016],
                "host_city": ["Rio", "Rio"],
                "host_country": ["BRA", "BRA"],
                "country_code": ["USA", None],
                "country_name": ["United States", "United States"],
                "sport": ["Swimming", "Athletics"],
                "event": ["Swimming event", "Athletics event"],
                "athlete_name": ["A", "B"],
                "medal": ["Gold", "Silver"],
            }
        )
        result, stats = clean_medals(df)
        assert stats["country_codes_recovered"] == 1
        assert stats["unrecoverable_null_country"] == 0
        assert len(result) == 2  # both rows kept
        assert "Recovered 1" in capsys.readouterr().out

    def test_unrecoverable_null_country_dropped(self) -> None:
        """Rows with null country_code that cannot be recovered are dropped."""
        df = pd.DataFrame(
            {
                "year": [2016, 2016],
                "host_city": ["Rio", "Rio"],
                "host_country": ["BRA", "BRA"],
                "country_code": ["USA", None],
                "country_name": ["United States", "Unknown Nation XYZ"],
                "sport": ["Swimming", "Athletics"],
                "event": ["Swimming event", "Athletics event"],
                "athlete_name": ["A", "B"],
                "medal": ["Gold", "Silver"],
            }
        )
        result, stats = clean_medals(df)
        assert stats["unrecoverable_null_country"] == 1
        assert len(result) == 1

    def test_reconciliation_totals_tie(self) -> None:
        """final_event_medals from stats must equal leaderboard row sum."""
        from medal_report import compute_leaderboard, dedupe_to_event_medals

        df = pd.DataFrame(
            {
                "year": [2016, 2016, 2016],
                "host_city": ["Rio"] * 3,
                "host_country": ["BRA"] * 3,
                "country_code": ["USA", None, "GBR"],
                "country_name": ["United States", "United States", "Great Britain"],
                "sport": ["Swimming"] * 3,
                "event": ["Swimming event", "Diving event", "Boxing event"],
                "athlete_name": ["A", "B", "C"],
                "medal": ["Gold", "Silver", "Bronze"],
            }
        )
        df_clean, stats = clean_medals(df)
        df_event, stats = dedupe_to_event_medals(df_clean, stats)
        board = compute_leaderboard(df_event)
        assert board["total"].sum() == stats["final_event_medals"]

    def test_unrecognized_medals_dropped(self) -> None:
        """Rows with completely unrecognized medals should be dropped."""
        df = pd.DataFrame(
            {
                "year": [2016, 2016],
                "host_city": ["Rio", "Rio"],
                "host_country": ["BRA", "BRA"],
                "country_code": ["USA", "GBR"],
                "country_name": ["United States", "Great Britain"],
                "sport": ["Swimming", "Swimming"],
                "event": ["Swimming event", "Swimming event"],
                "athlete_name": ["Phelps", "Peaty"],
                "medal": ["Gold", "Platinum"],
            }
        )
        result, stats = clean_medals(df)
        assert stats["unrecognized_medals"] == 1
        assert len(result) == 1
        assert result.iloc[0]["country_code"] == "USA"

    def test_preserves_medal_clean_column(self, sample_individual_data) -> None:
        """Output should contain medal_clean column."""
        df, _ = clean_medals(sample_individual_data)
        assert "medal_clean" in df.columns

    def test_original_medal_column_preserved(self, sample_individual_data) -> None:
        """Original medal column should be preserved alongside medal_clean."""
        df, _ = clean_medals(sample_individual_data)
        assert "medal" in df.columns

    def test_warns_on_unrecognized(self, capsys) -> None:
        """Should print a warning when medals are unrecognized."""
        df = pd.DataFrame(
            {
                "year": [2016],
                "host_city": ["Rio"],
                "host_country": ["BRA"],
                "country_code": ["USA"],
                "country_name": ["United States"],
                "sport": ["Swimming"],
                "event": ["Swimming event"],
                "athlete_name": ["Test"],
                "medal": ["Platinum"],
            }
        )
        clean_medals(df)
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "unrecognized" in captured.out.lower()
