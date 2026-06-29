# Approach Summary

## The Repair

The original `medal_report.py` had six defects, but two critical correctness bugs produced plausible numbers while silently distorting rankings.

**Unit-of-analysis mismatch.** The dataset is one row per athlete per event. Team events (60% of data) have many athletes per medal, so counting rows inflated team-sport nations by up to 4.6×. Fix: deduplicate team events to one medal per (year, sport, event, country), keeping the best medal when conflicts exist (363 conflicts logged, not hidden).

**Medal normalization failure.** The script only matched exact `Gold`/`Silver`/`Bronze`, but data contains 13 representations (`GOLD `, `1st`, `G`, `bronze`, etc.). A bare `except: pass` silently dropped 579 rows. Fix: normalize via lookup map before deduplication — order matters, because deduplicating raw tokens first overcounts by 297 entries.

I also removed a hardcoded API token, an `os.system()` call, and reset the chart y-axis to zero (truncated baseline exaggerated differences).

**Verification:** Reconciliation table shows counts at every stage (19,326 → 19,161 → 8,710 final event medals). 71 tests with 100% branch coverage confirm correctness. Run `python analysis.py` to reproduce all Phase 2 numbers.

## Data Decisions

1. **Normalize before deduplicate.** Deduplicating on raw medal text treats `"Gold"` and `"GOLD "` as distinct keys, producing 297 phantom medals. Normalizing first collapses them correctly.

2. **Team conflicts: best-medal with transparency.** Conflicting medal types for one country in one team event are data artifacts. I take the best medal but report the count rather than silently resolving.

3. **Historical countries kept separate.** URS, GDR, FRG, TCH, YUG appear only in valid year ranges. Merging into successors would be editorial — I preserve them and note comparability limits.

## Your Finding

**Insight:** The counting bug is structurally correlated (Pearson r = 0.9505, n = 30) with each country's team-sport concentration. Nations emphasizing team events are systematically over-ranked; individual-sport nations are suppressed. Rank changes after fix: KEN 23→18 (+5), KOR 12→8 (+4), BRA 8→11 (−3), GRC 19→23 (−4).

**Why defensible:** Correlation holds per-decade (1960–79: r = 0.9778; 1980–99: r = 0.9101; 2000–16: r = 0.9544), survives alternative metrics (weighted points produce identical top-8), and when team events are removed, inflation ratios converge to ~1.0 (mean 0.9710, max 1.0000) — confirming team-row multiplication as sole cause.

**Caveats:** The dataset is synthetic (generated names, 20 generic events), so rankings reflect data-generation patterns, not real Olympic outcomes. Population reference lacks a stated year, limiting per-capita comparability.
