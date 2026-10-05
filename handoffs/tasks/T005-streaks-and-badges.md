# T005: Weekly streaks and badges

- **Owner:** DeepSeek
- **Depends on:** the MVP (D21, already in the repo)
- **Size:** moderate

## Goal
Add the two remaining game mechanics from `docs/GAMIFICATION.md`, a **weekly streak** and **badges**, as pure engine functions plus a small amount of UI. The game must keep rewarding the plan, not volume (D5).

## Read first
1. `DEEPSEEK.md`
2. `docs/GAMIFICATION.md` (Streaks, Badges) and `docs/training/METHODOLOGY.md` §3b (flexible schedule)
3. The existing code: `src/gigalegs/engine/` (style: pure, frozen dataclasses), `src/gigalegs/services.py` (how DB facts are gathered), `src/gigalegs/web/templates/insights.html` and `path.html`, and `tests/` (fixtures use `tests/fixtures/fake-program.json`).

## Scope
**Do:**
1. **`engine/streaks.py`** (pure):
   - `WeekFacts(lift_sessions: int, active_days: int, protected: bool)`. `active_days` = days with a lift, ride, or recovery. `protected` = the week had a smart rest or a gated repeat.
   - `week_counts(f) -> bool`: true if `protected`, or (`lift_sessions >= 2` and `active_days >= 4`).
   - `weekly_streak(weeks: list[WeekFacts], freezes_available: int) -> tuple[int, int]`. `weeks` runs oldest → newest and **excludes the current, unfinished week**. Count back from the newest week; a non-counting week consumes a freeze if one is available, otherwise the streak stops there. Returns `(streak_weeks, freezes_used)`. A frozen week doesn't add to the count.
   - `freezes_available(total_weeks_since_start: int, used: int) -> int`: one freeze per 6 started weeks, minus used, never negative.
2. **`engine/badges.py`** (pure): `BadgeFacts` dataclass and `earned(facts) -> set[str]` with exactly these keys:
   - `patience_pays`: reached the program phase through the on-ramp gate (`facts.finished_onramp`)
   - `first_session`: ≥ 1 finished lifting session
   - `iron_lungs`: ≥ 100 commute miles (rides with `commute` set)
   - `smart_rest`: ≥ 3 combined gated repeats + smart rest days
   - `plate_225`, `plate_275`, `plate_315`, `plate_365`, `plate_405`: best squat-pattern e1RM ≥ that number
   - `commuter`: bike stage 5
3. **DB:** a `badges` table (`id`, `user_id`, `key`, `earned_on`, unique `(user_id, key)`) via a new Alembic migration (autogenerate, then review it). Badges are awarded once, never revoked.
4. **Services:**
   - `week_facts(db, uid, start, end)` (local Mon–Sun weeks, starting from the first week with any activity).
   - `streak(db, uid)`.
   - `award_badges(db, uid) -> list[str]` (newly earned keys), called at the end of `finish_session`, `log_ride`, `log_day`, and `resolve_gate`. Return newly earned badges so finish/summary pages can show "Badge earned: …". Badges give no XP.
   - `finished_onramp` is true when `phase_state.phase` is anything other than `onramp`. Smart rests come from `day_logs.kind == "smart_rest"`, and gated repeats from `xp_events.source == "gated_repeat"`.
5. **UI:**
   - A "Week streak" tile on Insights (with freezes left).
   - The streak in the Today hero card (`🔥 N-week streak` is fine).
   - A Badges section on Path: earned badges are prominent, unearned ones muted with how to earn them.
   - Badge names and copy are in GAMIFICATION.md. For the plate badges, use "Plate Collector 225" and so on.
6. **Tests:** every rule above as a named test, including:
   - The freeze consumption order.
   - The current week is excluded.
   - A protected week counts.
   - Badges are awarded only once (call `award_badges` twice).
   - Web: logging a 10-mile `in` commute ten times awards `iron_lungs` and shows it on /path.

**Do not:**
- Change any XP values, training rules, or existing engine behavior.
- Read `program/private/` or `athlete/`.
- Run `git commit`.

## Acceptance criteria
1. `uv run pytest -q` passes, with all new tests present.
2. `uv run ruff check .` and `uv run ruff format --check .` are clean.
3. `DATABASE_URL=sqlite:///./data/t005-check.db uv run gigalegs migrate` succeeds, and the table exists (`sqlite3 data/t005-check.db ".schema badges"`). Then delete the file.
4. `grep -rnE "^\s*(import|from) (sqlalchemy|fastapi|os|datetime)" src/gigalegs/engine/streaks.py src/gigalegs/engine/badges.py` prints nothing except `from datetime import date` if you need it. Engine stays pure.
5. Manual: `uv run gigalegs serve --port 8001`, then load `/insights` and `/path` with no errors. Paste the `/path` badge section HTML into the report.

## Report
Follow `DEEPSEEK.md` steps 5–8.
