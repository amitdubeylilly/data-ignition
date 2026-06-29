"""Tests for the reconciliation output."""

from medal_report import clean_medals, dedupe_to_event_medals, print_reconciliation


class TestPrintReconciliation:
    """Test reconciliation table printing."""

    def test_prints_all_stats(self, sample_team_data, capsys) -> None:
        """Should print all reconciliation lines."""
        df, stats = clean_medals(sample_team_data)
        _, stats = dedupe_to_event_medals(df, stats)
        print_reconciliation(stats)

        captured = capsys.readouterr()
        assert "DATA RECONCILIATION" in captured.out
        assert "Raw rows loaded" in captured.out
        assert "Exact duplicates removed" in captured.out
        assert "Team event rows" in captured.out
        assert "Individual event rows" in captured.out
        assert "TOTAL event-level medals" in captured.out

    def test_reconciliation_numbers_are_formatted(self, sample_team_data, capsys) -> None:
        """Numbers should be formatted with commas for readability."""
        df, stats = clean_medals(sample_team_data)
        _, stats = dedupe_to_event_medals(df, stats)
        # Manually inflate a number to test comma formatting
        stats["raw_rows"] = 19326
        print_reconciliation(stats)
        captured = capsys.readouterr()
        assert "19,326" in captured.out
