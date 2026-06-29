# Olympic Medal Leaderboard Reporter

A corrected analytics tool that reads the Olympic medals dataset and produces an accurate country medal leaderboard with proper handling of team-event deduplication, medal text normalization, and data quality transparency.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the tool (tool contract)
python medal_report.py data/olympic_medals.csv
```

## What It Does

Reads the medals CSV and produces:

- A corrected country medal leaderboard (printed to console)
- A reconciliation table showing data transformations at each stage
- A bar chart of top nations (`leaderboard.png`)

## Data Pipeline

The tool applies the following corrections in order:

1. **Medal Normalization** — Maps all medal text variants (`GOLD`, `gold`, `G`, `1st`, etc.) to canonical `Gold`/`Silver`/`Bronze`
2. **Exact Dedup** — Removes fully identical rows
3. **Event-Level Dedup** — Collapses team events (1 medal per country per event, not per athlete) and deduplicates athlete-level repeats in individual events
4. **Conflict Resolution** — When a country has conflicting medal types in the same team event (a data quality issue), takes the best medal and reports the conflict count

## Bugs Fixed (from original `data/medal_report.py`)

| #   | Issue                                                              | Impact                                          |
| --- | ------------------------------------------------------------------ | ----------------------------------------------- |
| 1   | **Unit-of-analysis mismatch** — counted athlete rows as medals     | Team events (60% of data) inflated counts ~4.6× |
| 2   | **Strict medal matching** — only recognized exact Gold/Silver/Bronze | 579 rows (3%) silently dropped                  |
| 3   | **Bare `except: pass`** — swallowed all errors                     | Hid the medal normalization failures            |
| 4   | **Truncated Y-axis** — chart zoomed in to exaggerate differences   | Misleading visualization                        |
| 5   | **Hardcoded API token** — secret in source code                    | Security risk                                   |
| 6   | **`os.system()` call** — shell execution in data tool              | Command injection vector                        |

## Data Files

- `data/olympic_medals.csv` — Summer Games medal records (1960-2016), one row per athlete per event
- `data/population_reference.csv` — Country populations (millions), optional for per-capita analysis

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests with coverage
pytest

# Lint (scoped to corrected code; data/medal_report_original.py is the broken reference)
ruff check medal_report.py tests/
ruff format --check medal_report.py tests/

# Type check
mypy medal_report.py --strict

# Security scan
bandit -r medal_report.py -c pyproject.toml
```

## Project Structure

```text
├── agent_config.json          # Required — harness execution config
├── olympics.json              # Required — tool contract (challenge_id, outputs)
├── medal_report.py            # Main tool (corrected)
├── olympic_medals.csv         # Dataset at root (for harness)
├── requirements.txt           # Pinned Python dependencies (JFrog-compatible)
├── approach_summary.md        # 400-word summary (3 sections)
├── data/
│   ├── olympic_medals.csv     # Source dataset
│   ├── population_reference.csv
│   ├── medal_report_original.py # Original (broken) script for reference
│   └── README.md
├── tests/
│   ├── conftest.py            # Shared fixtures
│   ├── test_normalization.py  # Medal text normalization
│   ├── test_load_data.py      # CSV loading & validation
│   ├── test_clean_medals.py   # Cleaning pipeline
│   ├── test_dedup.py          # Event-level deduplication
│   ├── test_leaderboard.py    # Leaderboard computation
│   ├── test_chart.py          # Chart generation
│   ├── test_reconciliation.py # Stats output
│   └── test_integration.py    # End-to-end & CLI tests
├── pyproject.toml             # Project config (ruff, mypy, pytest, bandit)
├── requirements-dev.txt       # Development dependencies
└── README.md
```

## Tool Contract

```bash
python medal_report.py <input_csv>
```

The tool reads the specified CSV, applies the full cleaning pipeline, and produces:

1. Data reconciliation table (row counts at each stage) — stdout
2. Top-N medal leaderboard — stdout
3. `leaderboard.csv` — machine-readable output (`country_code,medals`)
4. `leaderboard.png` — bar chart visualization
