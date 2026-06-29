"""Tests for data cleaning pipeline."""

import pandas as pd

from medal_report import clean_medals


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
                "medal": ["Gold", "Platinum"],  # Platinum is invalid
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
