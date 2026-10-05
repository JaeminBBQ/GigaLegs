# To Claude

**Task:** T005 (streaks-and-badges)
**Status:** done
**Report:** handoffs/reports/T005-report.md
**Updated:** 2026-10-04 19:20

## In one paragraph
Weekly streaks and badges are in: pure `engine/streaks.py` and `engine/badges.py`, a `badges` table via a new reviewed Alembic migration, service glue (`week_facts`, `streak`, `award_badges` hooked into `finish_session`/`log_ride`/`log_day`/`resolve_gate`), and UI (streak tile on Insights, 🔥 streak in the Today hero, Badges section on Path with earned/unearned styling). All five acceptance criteria pass: 102 tests (20 new, including freeze order, current-week exclusion, protected weeks, award-twice, and the 10×10 mi commute web test), ruff clean, fresh-DB migration verified, engine purity grep clean, and `/insights` + `/path` load with no errors on port 8001.

## Needs Claude's attention
1. Gated-repeat week mapping: the `gated_repeat` XP event fires on the first lift *after* the repeated week, so it protects the event's week, not the repeated week. Should it protect the prior week instead? (Details + 3 smaller questions in the report.)
2. `/path/bike-stage` doesn't call `award_badges` (spec named only four call sites) — `commuter` awards at the next logged activity. Worth adding?
