"""Tests for data loading functionality."""

import pytest

from medal_report import load_data


class TestLoadData:
    """Test CSV loading and validation."""

    def test_load_valid_csv(self, tmp_csv) -> None:
        """Should load a valid CSV successfully."""
        df = load_data(tmp_csv)
        assert len(df) == 5
        assert "medal" in df.columns

    def test_file_not_found_raises(self, tmp_path) -> None:
        """Should raise FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError, match="Data file not found"):
            load_data(tmp_path / "nonexistent.csv")

    def test_missing_columns_raises(self, tmp_path) -> None:
        """Should raise ValueError when required columns are missing."""
        import pandas as pd

        bad_csv = tmp_path / "bad.csv"
        pd.DataFrame({"year": [2016], "country_code": ["USA"]}).to_csv(bad_csv, index=False)
        with pytest.raises(ValueError, match="Missing required columns"):
            load_data(bad_csv)

    def test_load_prints_row_count(self, tmp_csv, capsys) -> None:
        """Should print the number of rows loaded."""
        load_data(tmp_csv)
        captured = capsys.readouterr()
        assert "5 rows" in captured.out
