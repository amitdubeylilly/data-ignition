"""Tests for leaderboard computation."""

import pandas as pd

from medal_report import clean_medals, compute_leaderboard, dedupe_to_event_medals


class TestComputeLeaderboard:
    """Test leaderboard generation."""

    def test_basic_leaderboard(self, sample_individual_data) -> None:
        """Should produce correct medal counts per country."""
        df, stats = clean_medals(sample_individual_data)
        df, stats = dedupe_to_event_medals(df, stats)
        board = compute_leaderboard(df)

        # USA: Gold (Swimming 2016) + Gold (Athletics 2012) = 2 Gold
        usa = board.loc["USA"]
        assert usa["gold"] == 2
        assert usa["silver"] == 0
        assert usa["bronze"] == 0
        assert usa["total"] == 2
        assert usa["points"] == 6  # 2 * 3

    def test_sorted_by_total_then_gold(self) -> None:
        """Leaderboard should be sorted by total desc, then gold desc."""
        df = pd.DataFrame(
            {
                "year": [2016, 2016, 2016, 2016],
                "host_city": ["Rio"] * 4,
                "host_country": ["BRA"] * 4,
                "country_code": ["USA", "GBR", "GBR", "CHN"],
                "country_name": [
                    "United States",
                    "Great Britain",
                    "Great Britain",
                    "China",
                ],
                "sport": ["Swimming"] * 4,
                "event": [
                    "Swimming event",
                    "Swimming event",
                    "Diving event",
                    "Swimming event",
                ],
                "athlete_name": ["A", "B", "C", "D"],
                "medal": ["Gold", "Silver", "Bronze", "Gold"],
                "medal_clean": ["Gold", "Silver", "Bronze", "Gold"],
                "is_team": [False] * 4,
            }
        )
        board = compute_leaderboard(df)
        # GBR has 2 total, USA and CHN have 1 each
        assert board.index[0] == "GBR"
        # USA and CHN both have 1 total, 1 gold — tie
        assert set(board.index[1:3]) == {"USA", "CHN"}

    def test_points_calculation(self) -> None:
        """Points should be Gold*3 + Silver*2 + Bronze*1."""
        df = pd.DataFrame(
            {
                "year": [2016, 2016, 2016],
                "host_city": ["Rio"] * 3,
                "host_country": ["BRA"] * 3,
                "country_code": ["USA", "USA", "USA"],
                "country_name": ["United States"] * 3,
                "sport": ["Swimming", "Athletics", "Boxing"],
                "event": ["Swimming event", "Athletics event", "Boxing event"],
                "athlete_name": ["A", "B", "C"],
                "medal": ["Gold", "Silver", "Bronze"],
                "medal_clean": ["Gold", "Silver", "Bronze"],
                "is_team": [False] * 3,
            }
        )
        board = compute_leaderboard(df)
        assert board.loc["USA", "points"] == 6  # 3 + 2 + 1

    def test_all_medal_columns_present(self, sample_individual_data) -> None:
        """Output should have gold, silver, bronze, total, points columns."""
        df, stats = clean_medals(sample_individual_data)
        df, stats = dedupe_to_event_medals(df, stats)
        board = compute_leaderboard(df)
        expected_cols = {"gold", "silver", "bronze", "total", "points"}
        assert set(board.columns) == expected_cols

    def test_empty_medal_type_handled(self) -> None:
        """Country with only some medal types should have 0 for others."""
        df = pd.DataFrame(
            {
                "year": [2016],
                "host_city": ["Rio"],
                "host_country": ["BRA"],
                "country_code": ["USA"],
                "country_name": ["United States"],
                "sport": ["Swimming"],
                "event": ["Swimming event"],
                "athlete_name": ["A"],
                "medal": ["Gold"],
                "medal_clean": ["Gold"],
                "is_team": [False],
            }
        )
        board = compute_leaderboard(df)
        assert board.loc["USA", "silver"] == 0
        assert board.loc["USA", "bronze"] == 0
