"""Shared test fixtures for medal_report tests."""

import pandas as pd
import pytest


@pytest.fixture
def sample_individual_data() -> pd.DataFrame:
    """Basic individual event data with standard medals."""
    return pd.DataFrame(
        {
            "year": [2016, 2016, 2016, 2012, 2012],
            "host_city": ["Rio", "Rio", "Rio", "London", "London"],
            "host_country": ["BRA", "BRA", "BRA", "GBR", "GBR"],
            "country_code": ["USA", "GBR", "CHN", "USA", "FRA"],
            "country_name": [
                "United States",
                "Great Britain",
                "China",
                "United States",
                "France",
            ],
            "sport": ["Swimming", "Swimming", "Swimming", "Athletics", "Athletics"],
            "event": [
                "Swimming event",
                "Swimming event",
                "Swimming event",
                "Athletics event",
                "Athletics event",
            ],
            "athlete_name": ["Phelps", "Peaty", "Sun", "Bolt", "Lemaitre"],
            "medal": ["Gold", "Silver", "Bronze", "Gold", "Bronze"],
        }
    )


@pytest.fixture
def sample_team_data() -> pd.DataFrame:
    """Team event data with multiple athletes per country."""
    rows = []
    # USA Basketball 2016 - Gold (3 athletes)
    for athlete in ["Player1", "Player2", "Player3"]:
        rows.append(
            {
                "year": 2016,
                "host_city": "Rio",
                "host_country": "BRA",
                "country_code": "USA",
                "country_name": "United States",
                "sport": "Basketball",
                "event": "Basketball team event",
                "athlete_name": athlete,
                "medal": "Gold",
            }
        )
    # GBR Basketball 2016 - Silver (2 athletes)
    for athlete in ["PlayerA", "PlayerB"]:
        rows.append(
            {
                "year": 2016,
                "host_city": "Rio",
                "host_country": "BRA",
                "country_code": "GBR",
                "country_name": "Great Britain",
                "sport": "Basketball",
                "event": "Basketball team event",
                "athlete_name": athlete,
                "medal": "Silver",
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def sample_dirty_medals() -> pd.DataFrame:
    """Data with non-standard medal representations."""
    return pd.DataFrame(
        {
            "year": [2016] * 13,
            "host_city": ["Rio"] * 13,
            "host_country": ["BRA"] * 13,
            "country_code": ["USA"] * 13,
            "country_name": ["United States"] * 13,
            "sport": ["Athletics"] * 13,
            "event": ["Athletics event"] * 13,
            "athlete_name": [f"Athlete{i}" for i in range(13)],
            "medal": [
                "Gold",
                "Silver",
                "Bronze",
                "GOLD ",
                "gold",
                "G",
                "1st",
                "Silver ",
                "S",
                "2nd",
                "bronze",
                "B",
                "3rd",
            ],
        }
    )


@pytest.fixture
def sample_with_duplicates() -> pd.DataFrame:
    """Data containing exact duplicate rows."""
    base = pd.DataFrame(
        {
            "year": [2016, 2016, 2012],
            "host_city": ["Rio", "Rio", "London"],
            "host_country": ["BRA", "BRA", "GBR"],
            "country_code": ["USA", "GBR", "FRA"],
            "country_name": ["United States", "Great Britain", "France"],
            "sport": ["Swimming", "Swimming", "Athletics"],
            "event": ["Swimming event", "Swimming event", "Athletics event"],
            "athlete_name": ["Phelps", "Peaty", "Lemaitre"],
            "medal": ["Gold", "Silver", "Bronze"],
        }
    )
    # Duplicate first two rows
    return pd.concat([base, base.iloc[:2]], ignore_index=True)


@pytest.fixture
def sample_team_conflicts() -> pd.DataFrame:
    """Team event data where same country has conflicting medal types (data error)."""
    rows = []
    # USA Basketball 2016 - some say Gold, some say Bronze (impossible in reality)
    for i, medal in enumerate(["Gold", "Gold", "Bronze", "Bronze"]):
        rows.append(
            {
                "year": 2016,
                "host_city": "Rio",
                "host_country": "BRA",
                "country_code": "USA",
                "country_name": "United States",
                "sport": "Basketball",
                "event": "Basketball team event",
                "athlete_name": f"Player{i}",
                "medal": medal,
            }
        )
    return pd.DataFrame(rows)


@pytest.fixture
def tmp_csv(tmp_path, sample_individual_data):
    """Write sample data to a temporary CSV file."""
    csv_path = tmp_path / "test_medals.csv"
    sample_individual_data.to_csv(csv_path, index=False)
    return csv_path
