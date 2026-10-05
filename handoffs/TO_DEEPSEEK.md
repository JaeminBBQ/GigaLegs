# To DeepSeek

**Current task:** T005: Weekly streaks and badges
**Spec:** `handoffs/tasks/T005-streaks-and-badges.md`

1. Read `DEEPSEEK.md` first (unchanged), then the spec.
2. When you're finished: write the report, overwrite `handoffs/TO_CLAUDE.md`, set T005 to `review`, **send the Discord notification**, and tell the user.

## Notes
- **T001 is cancelled.** Claude built the MVP directly (D21) because training started 2026-10-05: engine, shorthand parser, DB, and web app. Read `src/gigalegs/` before starting; your work extends it.
- Port 8765 belongs to another project; use 8001 for manual checks.
- The real program lives in `program/private/` (gitignored, paid content). Tests must use `tests/fixtures/fake-program.json`.
