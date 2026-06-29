"""Tests for chart generation."""

from pathlib import Path

from medal_report import clean_medals, compute_leaderboard, dedupe_to_event_medals, make_chart


class TestMakeChart:
    """Test chart generation."""

    def test_chart_creates_file(self, sample_individual_data, tmp_path) -> None:
        """Should create a PNG file."""
        df, stats = clean_medals(sample_individual_data)
        df, stats = dedupe_to_event_medals(df, stats)
        board = compute_leaderboard(df)

        outfile = str(tmp_path / "test_chart.png")
        result = make_chart(board, outfile=outfile)
        assert Path(result).exists()
        assert result == outfile

    def test_chart_file_is_valid_png(self, sample_individual_data, tmp_path) -> None:
        """Output file should be a valid PNG (check magic bytes)."""
        df, stats = clean_medals(sample_individual_data)
        df, stats = dedupe_to_event_medals(df, stats)
        board = compute_leaderboard(df)

        outfile = str(tmp_path / "test_chart.png")
        make_chart(board, outfile=outfile)

        with open(outfile, "rb") as f:
            magic = f.read(8)
        # PNG magic bytes
        assert magic[:4] == b"\x89PNG"

    def test_chart_prints_save_message(self, sample_individual_data, tmp_path, capsys) -> None:
        """Should print confirmation message."""
        df, stats = clean_medals(sample_individual_data)
        df, stats = dedupe_to_event_medals(df, stats)
        board = compute_leaderboard(df)

        outfile = str(tmp_path / "test_chart.png")
        make_chart(board, outfile=outfile)
        captured = capsys.readouterr()
        assert "Chart saved" in captured.out
