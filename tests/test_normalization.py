"""Tests for medal normalization logic."""

import pytest

from medal_report import normalize_medal


class TestNormalizeMedal:
    """Test medal value normalization."""

    @pytest.mark.parametrize(
        "input_val,expected",
        [
            ("Gold", "Gold"),
            ("Silver", "Silver"),
            ("Bronze", "Bronze"),
            # Uppercase / mixed case
            ("GOLD ", "Gold"),
            ("gold", "Gold"),
            ("SILVER", "Silver"),
            ("BRONZE", "Bronze"),
            # Abbreviated forms
            ("G", "Gold"),
            ("S", "Silver"),
            ("B", "Bronze"),
            # Ordinal forms
            ("1st", "Gold"),
            ("2nd", "Silver"),
            ("3rd", "Bronze"),
            # Trailing/leading whitespace
            ("Silver ", "Silver"),
            (" Gold", "Gold"),
            ("  Bronze  ", "Bronze"),
            (" G ", "Gold"),
        ],
    )
    def test_valid_medal_values(self, input_val: str, expected: str) -> None:
        """All known medal representations should normalize correctly."""
        assert normalize_medal(input_val) == expected

    @pytest.mark.parametrize(
        "input_val",
        [
            "",
            "Platinum",
            "4th",
            "None",
            "DNF",
            "  ",
        ],
    )
    def test_unrecognized_values_return_none(self, input_val: str) -> None:
        """Unrecognized medal values should return None."""
        assert normalize_medal(input_val) is None

    def test_numeric_input_handled(self) -> None:
        """Non-string input should be handled gracefully via str() conversion."""
        # int/float get str()'d first
        assert normalize_medal(1) is None  # type: ignore[arg-type]
        assert normalize_medal(3.0) is None  # type: ignore[arg-type]
