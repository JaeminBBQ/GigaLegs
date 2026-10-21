# T018 Report

**Status:** done
**Implementer:** DeepSeek

## Summary
Every logged entry can now be fixed from History: sessions link to their page (done sessions show editable set rows via `_set_row.html` plus a Delete session button), rides get a prefilled edit form and delete, and day logs/metrics get delete buttons. XP stays consistent: all XP events now carry id-based refs (`ride-{id}`, `set-{id}`, `session-{id}`, `day-{id}`, `metric-{id}`), and edits upsert or remove the matching event(s) by recomputing through the existing engine rules (`_set_xp`, `E.ride_xp`, and the same "covers the plan" rule as `finish_session`, now shared via `_session_bonus`). Deleting never touches `phase_state` and never revokes badges. All acceptance criteria pass.

## Files changed
- `src/gigalegs/services.py`:
  - XP refs: readiness now uses `session-{id}` (session is flushed first), day logs `day-{id}`, metrics `metric-{id}`. No XP amounts changed.
  - `_session_bonus(db, uid, sess) -> (all_logged, xp)` extracted from `finish_session` (behavior identical) and reused by `update_set`.
  - New: `_sync_xp_event` (upsert/remove one event), `_remove_xp_events` (by refs), `delete_ride`, `delete_day`, `delete_metric`, `delete_session`, `update_ride` (includes date), `update_set`. All return `None` for missing/unowned rows; web maps that to 404.
  - `history()` returns structured items (`kind`, `id`, `label`) so History can render actions.
- `src/gigalegs/web/app.py`: routes `GET /ride/{id}/edit`, `POST /ride/{id}/update`, `POST /ride/{id}/delete`, `POST /day/{id}/delete`, `POST /metric/{id}/delete`, `POST /session/{sid}/edit-set/{set_id}`, `POST /session/{sid}/delete`; `/history` accepts a `note` query param (delete notices).
- Templates: `history.html` (Edit/Delete per entry, note banner), `today.html` (renders `i.label`), `_set_row.html` (`row_verb` param so the same partial drives log and edit), `summary.html` (done view: "Fix a set" editable rows + Delete session + Path notice), `ride.html` (prefill, dynamic action, delete button).
- `src/gigalegs/web/static/style.css`: history entry rows.
- `tests/test_edit_and_delete.py` (new): 6 named tests.

## Acceptance criteria
| Criterion | Result | Evidence (command + key output) |
|---|---|---|
| 1. `uv run pytest -q` passes, all new tests present | pass | `110 passed, 1 warning in 1.03s`; 6 new tests in `tests/test_edit_and_delete.py` (over-cap edit and back, ride delete/update, session delete + phase_state, user-2 404, mixed-sequence consistency) |
| 2. `uv run ruff check .` + `uv run ruff format --check .` clean | pass | `All checks passed!` / `59 files already formatted` |
| 3. No date-only or bare `"session"` refs | pass | Every `add_xp` ref is `onramp-{week}`, `session-{id}`, `set-{id}`, `ride-{id}`, `day-{id}`, or `metric-{id}` (verified by grep) |
| 4. Manual on scratch DB (port 8001, then `data/t018.db` deleted) | pass | Totals below |

Manual sequence (`DATABASE_URL=sqlite:///./data/t018.db uv run gigalegs serve --port 8001`):

| Step | XP total | Note |
|---|---|---|
| 1. Quick log: `lift / ready 2 7 7 / sq 135x5x2 @6 / plank 45s x2 / ride 6mi 30min z2` | 36 | 10 readiness + 4×5 sets + 6 ride; no session bonus (the quick log didn't cover the real program's full day plan) |
| 2. Edit set 1 (`/session/1/edit-set/1`) with form broken | 31 | Set event removed (−5) |
| 3. Edit set 1 back | 36 | Event recreated (+5) |
| 4. Delete ride 1 | 30 | Ride event removed (−6) |
| 5. Delete session 1 | 0 | Readiness + set events removed (−30) |

`/history` rendered 200 at every step, and the server log had no errors. A second ride delete correctly returned 404. Scratch DB deleted afterwards.

## Deviations from the spec
- `_sync_xp_event` also *creates* an event when a recompute yields XP > 0 but none exists (e.g. a set that earned 0 at finish, later edited to earn). The spec said "replace"; creating is required by the Goal so the total equals what the engine would award.
- `update_ride` takes the date too (the prefilled form has a date field; silently ignoring it would discard the athlete's fix). Spec left the signature open ("...").
- A single set can be edited but not deleted (Scope defines `delete_session` and `update_set` only). Blanking the set's reps/seconds via edit makes it "not logged".

## Dependencies added
None.

## Questions / proposals for Claude
1. Edits/deletes don't call `award_badges`. Badges are never revoked, but if an edit changes what *should* be earned (e.g. ride miles edited up past 100), the badge waits for the next logged activity. One-line fix in `update_ride`/`update_set` if you want it.
2. Editing a set doesn't recompute e1RM PR XP (documented limitation per spec), so a PR event can remain after the set that earned it is edited down. Same for gated-repeat XP. Acceptable?
3. After an HTMX set edit, the "N XP from sets" header on the done-session page is stale until reload. Fine as-is, or should the row swap also refresh the header?

## Known issues / follow-ups
None.
