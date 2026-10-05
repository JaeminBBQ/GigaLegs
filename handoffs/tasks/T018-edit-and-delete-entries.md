# T018: Edit and delete logged entries

- **Owner:** DeepSeek
- **Depends on:** T005 (done)
- **Size:** moderate

## Goal
Let the athlete fix mistakes. From History, each logged item (lifting session, single set, ride, recovery/rest day, soreness/bodyweight metric) can be edited or deleted, and **XP stays consistent**: the total always equals what the engine would award for the data as it now stands.

## Read first
1. `DEEPSEEK.md`
2. `src/gigalegs/services.py` (how XP is written: `add_xp`, `finish_session`, `log_ride`, `log_day`, `log_metric`; the `ref` strings on `XpEvent`), `src/gigalegs/models.py`, `web/templates/history.html`
3. `docs/GAMIFICATION.md` (XP table)

## Scope
**Do:**
1. **XP bookkeeping.** Every XP event must be traceable to what earned it:
   - Rides use `ride-{id}`.
   - Set XP uses `set-{id}` and the session bonus `session-{id}`.
   - Day logs: change the ref to `day-{id}` (currently the ISO date).
   - Metrics: change to `metric-{id}`.
   - Readiness check-ins: change to `session-{id}` with source `readiness_checkin`. The `start_session` one currently uses ref `"session"`: create the session first, flush, then use its id.
   - **Do not** change any XP amounts.
2. **Services:**
   - `delete_ride(db, uid, ride_id)`, `delete_day(...)`, `delete_metric(...)`: remove the row and its XP events (by ref).
   - `delete_session(db, uid, session_id)`: remove the session, its sets, and every XP event whose ref is `session-{id}` or `set-{set_id}` for its sets. **Never** change `phase_state`. Instead, show a notice: "If this changed where you are in the program, fix it on Path → Adjust position."
   - `update_ride(...)` and `update_set(db, uid, set_id, weight, reps, seconds, rpe, form_ok, pain)` (for finished sessions): update the row, then **recompute** its XP via the existing rules (`_set_xp`, `E.ride_xp`). Replace the event's amount; if the set or ride now earns 0, delete the event. For a set, also recompute the session bonus (`session_xp`, using the same "covers the plan" rule as `finish_session`) and replace that event too.
   - E1RM PR XP and gated-repeat XP are not recomputed on edit (documented limitation; note it in the report).
   - Badges are never revoked (D-rule from T005), even if the data that earned them is deleted.
3. **Web:**
   - History lists each entry with an "Edit" link. Sessions link to the existing `/session/{id}` page, which for `done` sessions now shows editable set rows (reuse `_set_row.html`, posting to a new `/session/{id}/edit-set/{set_id}`) plus a **Delete session** button.
   - Rides get `/ride/{id}/edit` (reuse the ride form, prefilled) and a delete button.
   - Days and metrics get a small delete button.
   - Every delete is a POST with a `confirm()` prompt.
   - Only the owner's rows: use `current_user`, and return 404 for anything else.
4. **Tests** (named):
   - Edit a set's RPE from on target to over the cap: set XP goes 10 → 0, the event is removed, and the session bonus drops to 0.
   - Edit it back: both return.
   - Delete a ride: total XP falls by exactly its XP.
   - Delete a session: all its set and session XP disappears, and `phase_state` is unchanged.
   - Deleting someone else's row (user 2) returns 404.
   - The `level_info` total equals the sum of XP events after a random mix of edits (just a fixed scripted sequence, no randomness).

**Do not:**
- Change XP amounts, training rules, or progression logic.
- Read `program/private/` or `athlete/`.
- Run `git commit`.

## Acceptance criteria
1. `uv run pytest -q` passes, with all new tests present.
2. `uv run ruff check .` and `uv run ruff format --check .` are clean.
3. `grep -n 'ref' src/gigalegs/services.py` shows no XP event with a date-only or bare `"session"` ref.
4. Manual, on a scratch DB (`DATABASE_URL=sqlite:///./data/t018.db uv run gigalegs serve --port 8001`, then delete `data/t018.db`):
   - Log a session via quick log, edit a set from History, and delete a ride.
   - List the XP total before and after each step in the report.

## Report
Follow `DEEPSEEK.md` steps 5–8.
