"""Tests for event-level deduplication logic."""

import pandas as pd
import pytest

from medal_report import clean_medals, dedupe_to_event_medals, is_team_event


class TestIsTeamEvent:
    """Test team event detection."""

    @pytest.mark.parametrize(
        "event_name,expected",
        [
            ("Basketball team event", True),
            ("Football team event", True),
            ("Handball team event", True),
            ("Rowing team event", True),
            ("Relays team event", True),
            ("Swimming event", False),
            ("Athletics event", False),
            ("Boxing event", False),
            ("Cycling event", False),
        ],
    )
    def test_team_event_detection(self, event_name: str, expected: bool) -> None:
        """Events with 'team' in name should be detected as team events."""
        assert is_team_event(event_name) == expected

    def test_case_insensitive(self) -> None:
        """Detection should be case-insensitive."""
        assert is_team_event("Basketball TEAM Event") is True
        assert is_team_event("TEAM relay") is True


class TestDedupeTeamEvents:
    """Test team event deduplication."""

    def test_team_dedup_collapses_athletes(self, sample_team_data) -> None:
        """Multiple athletes in same team event should collapse to 1 medal."""
        df, stats = clean_medals(sample_team_data)
        result, stats = dedupe_to_event_medals(df, stats)

        # USA should have 1 medal, GBR should have 1 medal
        usa_medals = result[result["country_code"] == "USA"]
        gbr_medals = result[result["country_code"] == "GBR"]
        assert len(usa_medals) == 1
        assert len(gbr_medals) == 1
        assert usa_medals.iloc[0]["medal_clean"] == "Gold"
        assert gbr_medals.iloc[0]["medal_clean"] == "Silver"

    def test_team_conflict_takes_best_medal(self, sample_team_conflicts) -> None:
        """When same country has conflicting medals in team event, take best."""
        df, stats = clean_medals(sample_team_conflicts)
        result, stats = dedupe_to_event_medals(df, stats)

        usa_medals = result[result["country_code"] == "USA"]
        assert len(usa_medals) == 1
        assert usa_medals.iloc[0]["medal_clean"] == "Gold"  # Gold > Bronze

    def test_team_conflict_count_reported(self, sample_team_conflicts) -> None:
        """Conflict count should be tracked in stats."""
        df, stats = clean_medals(sample_team_conflicts)
        _, stats = dedupe_to_event_medals(df, stats)
        assert stats["team_medal_conflicts"] == 1

    def test_different_years_counted_separately(self) -> None:
        """Same event in different years should be separate medals."""
        rows = []
        for year in [2012, 2016]:
            rows.append(
                {
                    "year": year,
                    "host_city": "City",
                    "host_country": "XXX",
                    "country_code": "USA",
                    "country_name": "United States",
                    "sport": "Basketball",
                    "event": "Basketball team event",
                    "athlete_name": "Player1",
                    "medal": "Gold",
                }
            )
        df = pd.DataFrame(rows)
        df, stats = clean_medals(df)
        result, stats = dedupe_to_event_medals(df, stats)
        assert len(result[result["country_code"] == "USA"]) == 2


class TestDedupeIndividualEvents:
    """Test individual event deduplication."""

    def test_individual_events_keep_all_athletes(self, sample_individual_data) -> None:
        """Each athlete in individual event should count as separate medal."""
        df, stats = clean_medals(sample_individual_data)
        result, stats = dedupe_to_event_medals(df, stats)
        assert len(result) == 5  # All 5 are unique athlete-event combos

    def test_individual_athlete_duplicate_removed(self) -> None:
        """Same athlete with same medal in same event should be deduped.

        Note: rows that differ in at least one non-key column survive exact-dedup
        but should still be caught by athlete-level dedup.
        """
        df = pd.DataFrame(
            {
                "year": [2016, 2016],
                "host_city": ["Rio", "Rio de Janeiro"],  # Different host_city to avoid exact dedup
                "host_country": ["BRA", "BRA"],
                "country_code": ["USA", "USA"],
                "country_name": ["United States", "United States"],
                "sport": ["Swimming", "Swimming"],
                "event": ["Swimming event", "Swimming event"],
                "athlete_name": ["Phelps", "Phelps"],  # Same athlete!
                "medal": ["Gold", "Gold"],  # Same medal!
            }
        )
        df, stats = clean_medals(df)
        result, stats = dedupe_to_event_medals(df, stats)
        assert len(result) == 1
        assert stats["individual_athlete_dupes_removed"] == 1


class TestDedupeStats:
    """Test that dedup stats are correctly computed."""

    def test_stats_completeness(self, sample_team_data) -> None:
        """All expected stats keys should be present."""
        df, stats = clean_medals(sample_team_data)
        _, stats = dedupe_to_event_medals(df, stats)

        required_keys = [
            "team_event_rows",
            "individual_event_rows",
            "team_medal_conflicts",
            "individual_athlete_dupes_removed",
            "final_event_medals",
            "team_medals",
            "individual_medals",
        ]
        for key in required_keys:
            assert key in stats, f"Missing stat: {key}"

    def test_final_count_equals_sum(self, sample_team_data) -> None:
        """final_event_medals should equal team_medals + individual_medals."""
        df, stats = clean_medals(sample_team_data)
        _, stats = dedupe_to_event_medals(df, stats)
        assert stats["final_event_medals"] == stats["team_medals"] + stats["individual_medals"]
