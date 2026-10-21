# T019: Simple after-the-fact logging + on-ramp floor

- **Owner:** DeepSeek
- **Depends on:** T018 (start this only after T018 is accepted)
- **Size:** moderate

## Goal
The athlete doesn't log at the gym. They fill things in afterwards, only on days they did something, and don't want to be asked about soreness, sleep, or energy (D24). Make logging a lift a single prefilled form with one Save. Add the on-ramp floor rule (D23).

## Read first
1. `DEEPSEEK.md`
2. `docs/DECISIONS.md` D20, D23, D24; `docs/training/ONRAMP.md` (Floor, Gate); `docs/training/METHODOLOGY.md` §4
3. `src/gigalegs/services.py` (`plan_for`, `start_session`, `finish_session`, `resolve_gate`, `save_parsed`), `web/app.py`, `templates/today.html`, `session.html`, and your T018 edit flow

## Scope
**Do:**
1. **Engine (pure):**
   - `can_advance_onramp(soreness: int | None, pain, all_sets_ok)`: when `soreness is None`, skip the soreness check.
   - New `onramp_floor(scaled_lb: float | None, clean_lb: float | None) -> float | None` = the max of the two (None-safe).
2. **Services:**
   - `plan_for` (on-ramp phase, `kind == "weight"`): apply `onramp_floor` with the heaviest weight from any finished on-ramp session where **every** set of that exercise had reps ≥ prescribed reps, form OK, no pain, and (RPE ≤ cap **or** RPE missing). Example: week A squat logged 135×7×2 clean → week B prescribes 135, not 130; week C prescribes 155 (scaled is higher).
   - The gate must resolve at the **next lift logged by any path** (web form or quick log), with or without soreness. Use soreness if that session or that date has one, else `None`. Today `save_parsed` only resolves the gate when readiness is given, so an on-ramp week can get stuck. Fix that.
   - `log_lift(db, uid, d, day, entries, note) -> SessionSummary`: create a session for queue position (phase, week, `day`) on date `d`, resolve the gate first if pending, create SetLogs with prescriptions from `plan_for` plus the actuals, then `finish_session`. One transaction. Entries with no reps and no seconds are skipped. No readiness XP (nothing asked).
3. **Web:**
   - **Today:** remove the morning check-in card, the readiness selects, and the recovery/rest controls. Keep, in order:
     1. The suggestion card.
     2. The queued plan table.
     3. Two big buttons: **Log a lift**, **Log a ride**.
     4. A small "Quick log" link.
     5. Recent.

     Recovery and rest stay available via quick log only (add `recovery [date] <min>min` and `rest [date]` lines to the parser + LOGGING.md cheat sheet).
   - **`GET /lift`** shows a single form:
     - A date (default today, `max` = today).
     - A program-day select (default: the queued day, listing Days 1–3 of the current week).
     - Every planned set prefilled: weight = prescribed, reps = prescribed, RPE blank, "form broke" unchecked, pain empty. Holds have seconds blank.
     - When the user changes set 1's weight or reps for an exercise, copy it to that exercise's later sets that are still untouched (small inline JS).
     - An optional note, and a single **Save** button → `POST /lift` → `log_lift` → the existing summary page.
     - Changing the day select re-renders the prefilled plan for that day (a plain GET with `?day=` is fine).
   - Remove the old start-session flow (`/session/start` and the open-session redirect on Today) **unless** T018's edit view needs parts of it. Keep `/session/{id}` for viewing and editing finished sessions.
   - The ride form stays as is (it has a date field already).
4. **Tests** (named):
   - `onramp_floor` cases.
   - The week B squat prescription is 135 after a clean 135×7×2 in week A (fake program: adapt the numbers to the fixture; assert floor > scaled).
   - The floor ignores a set with `!pain` or `!form`.
   - The gate resolves with no soreness anywhere (3 clean sessions → the 4th log advances to B).
   - The gate still repeats if pain was flagged.
   - `POST /lift` with a past date saves on that date.
   - Untouched empty rows are skipped.
   - The Today page has no "How sore" text.

**Do not:**
- Change XP amounts or other training rules.
- Read `program/private/` or `athlete/`. Tests use the fake program.
- Run `git commit`.

## Acceptance criteria
1. `uv run pytest -q` passes, with all new tests present; ruff check/format clean.
2. `grep -n "How sore\|session/start" src/gigalegs/web/templates/*.html` prints nothing.
3. Manual, on a scratch DB, port 8001:
   - Log a lift for yesterday via `/lift`, changing set 1's weight (later sets follow), and save.
   - It appears on History with yesterday's date, and the summary shows XP.
   - Paste the summary text into the report.

## Report
Follow `DEEPSEEK.md` steps 5–8.
