"""Integration tests for the full pipeline and CLI."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from medal_report import (
    clean_medals,
    compute_leaderboard,
    dedupe_to_event_medals,
    load_data,
    main,
)


class TestMainCLI:
    """Test the CLI entry point."""

    def test_missing_argument_exits(self) -> None:
        """Should exit with error when no CSV path provided."""
        with patch("sys.argv", ["medal_report.py"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_missing_argument_shows_usage(self, capsys) -> None:
        """Should print usage message on missing argument."""
        with (
            patch("sys.argv", ["medal_report.py"]),
            pytest.raises(SystemExit),
        ):
            main()
        captured = capsys.readouterr()
        assert "Usage" in captured.err

    def test_valid_csv_runs_successfully(self, tmp_csv, capsys, monkeypatch, tmp_path) -> None:
        """Should run the full pipeline without errors."""
        monkeypatch.chdir(tmp_path)
        with patch("sys.argv", ["medal_report.py", str(tmp_csv)]):
            main()
        captured = capsys.readouterr()
        assert "MEDAL LEADERBOARD" in captured.out
        assert "DATA RECONCILIATION" in captured.out
        # Must produce leaderboard.csv
        leaderboard_csv = tmp_path / "leaderboard.csv"
        assert leaderboard_csv.exists()
        content = leaderboard_csv.read_text()
        assert "country_code,medals" in content

    def test_nonexistent_file_raises(self, tmp_path) -> None:
        """Should raise FileNotFoundError for missing input file."""
        with (
            patch("sys.argv", ["medal_report.py", str(tmp_path / "ghost.csv")]),
            pytest.raises(FileNotFoundError),
        ):
            main()


class TestEndToEndPipeline:
    """Integration tests running the full pipeline on crafted data."""

    def test_full_pipeline_mixed_data(self, tmp_path) -> None:
        """Test full pipeline with mixed individual and team data."""
        data = pd.DataFrame(
            {
                "year": [2016, 2016, 2016, 2016, 2016, 2016],
                "host_city": ["Rio"] * 6,
                "host_country": ["BRA"] * 6,
                "country_code": ["USA", "USA", "USA", "GBR", "GBR", "FRA"],
                "country_name": [
                    "United States",
                    "United States",
                    "United States",
                    "Great Britain",
                    "Great Britain",
                    "France",
                ],
                "sport": [
                    "Basketball",
                    "Basketball",
                    "Swimming",
                    "Basketball",
                    "Swimming",
                    "Swimming",
                ],
                "event": [
                    "Basketball team event",
                    "Basketball team event",
                    "Swimming event",
                    "Basketball team event",
                    "Swimming event",
                    "Swimming event",
                ],
                "athlete_name": ["P1", "P2", "Phelps", "P3", "Peaty", "Manaudou"],
                "medal": ["Gold", "Gold", "Gold", "Silver", "Silver", "Bronze"],
            }
        )
        csv_path = tmp_path / "mixed.csv"
        data.to_csv(csv_path, index=False)

        with patch("sys.argv", ["medal_report.py", str(csv_path)]):
            main()

        # Verify: USA should have 2 medals (1 team Gold + 1 individual Gold)
        # GBR: 2 medals (1 team Silver + 1 individual Silver)
        # FRA: 1 medal (1 individual Bronze)

    def test_dirty_medal_variants_normalized(self, tmp_path) -> None:
        """Non-standard medal representations should all be counted."""
        data = pd.DataFrame(
            {
                "year": [2016] * 6,
                "host_city": ["Rio"] * 6,
                "host_country": ["BRA"] * 6,
                "country_code": ["USA", "USA", "USA", "GBR", "GBR", "GBR"],
                "country_name": ["United States"] * 3 + ["Great Britain"] * 3,
                "sport": ["Swimming"] * 6,
                "event": [
                    "Swimming event",
                    "Diving event",
                    "Boxing event",
                    "Swimming event",
                    "Diving event",
                    "Boxing event",
                ],
                "athlete_name": ["A", "B", "C", "D", "E", "F"],
                "medal": ["GOLD ", "1st", "G", "Silver ", "2nd", "S"],
            }
        )
        csv_path = tmp_path / "dirty.csv"
        data.to_csv(csv_path, index=False)

        df = load_data(csv_path)
        df, stats = clean_medals(df)
        df, stats = dedupe_to_event_medals(df, stats)
        board = compute_leaderboard(df)

        # USA: 3 gold medals, GBR: 3 silver medals
        assert board.loc["USA", "gold"] == 3
        assert board.loc["GBR", "silver"] == 3

    def test_subprocess_execution(self, tmp_csv) -> None:
        """Script should be executable as a subprocess (tool contract)."""
        result = subprocess.run(  # noqa: S603
            [sys.executable, "medal_report.py", str(tmp_csv)],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        assert "MEDAL LEADERBOARD" in result.stdout

    def test_real_data_file(self) -> None:
        """Integration test against the actual dataset."""
        data_path = Path(__file__).parent.parent / "data" / "olympic_medals.csv"
        if not data_path.exists():
            pytest.skip("Real data file not available")

        df = load_data(data_path)
        df, stats = clean_medals(df)
        df, stats = dedupe_to_event_medals(df, stats)
        board = compute_leaderboard(df)

        # Sanity checks on real data
        assert stats["raw_rows"] == 19326
        assert stats["exact_duplicates_removed"] == 165
        assert stats["unrecognized_medals"] == 0
        assert stats["final_event_medals"] > 5000
        assert stats["final_event_medals"] < 15000
        assert board.index[0] == "USA"  # USA should be #1
        assert board.loc["USA", "total"] > 500
