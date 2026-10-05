# T001: Scaffold and pure engine core

> **Cancelled (D21).** Claude built this as part of the MVP on 2026-10-04. Kept for history.

- **Owner:** DeepSeek
- **Depends on:** none
- **Size:** moderate

## Goal
Create the Python project skeleton and the pure rules engine that turns the training rulebook into tested functions. No DB, no web, no program data yet (T002–T004 add those). Everything here is deterministic math with exact numbers given below.

## Read first
1. `DEEPSEEK.md`
2. `docs/ARCHITECTURE.md` (Stack, Layout, Core principle)
3. `docs/training/METHODOLOGY.md` §2–§4 and `docs/training/ONRAMP.md` (the rules you're implementing)
4. `docs/GAMIFICATION.md` (XP table, levels)

When this spec and the docs disagree, **this spec wins**. Note the disagreement in your report.

## Scope
**Do:**

1. **Project setup** with `uv`:
   - `pyproject.toml`: name `gigalegs`, `requires-python = ">=3.12"`, `src/` layout, build backend `hatchling`, **no runtime dependencies**. Dev dependency group: `pytest`, `ruff`.
   - Ruff: line length 100, target py312, default rules plus `I`.
   - `uv python pin 3.12`.
   - Create `src/gigalegs/__init__.py` and `src/gigalegs/engine/__init__.py`. The engine `__init__` re-exports every public name below.
   - Keep the existing `.gitignore` and add anything else uv/ruff/pytest need.

2. **`engine/types.py`**: frozen dataclasses:
   - `Prescription(sets: int, reps: int, weight_lb: float | None, rpe_cap: float | None)`
   - `SetResult(prescribed_reps: int, reps: int, target_rpe: float | None, rpe: float | None, form_ok: bool)`
   - `Adjustment(load_factor: float, rpe_cap_delta: float, flag_repeat_week: bool, suggest_smart_rest: bool)`
   - `Decision`: a `StrEnum` with `ADVANCE`, `REPEAT`, `RESET`.

3. **`engine/rounding.py`**
   - `round_to_increment(x: float, inc: float = 5.0) -> float` rounds to the nearest increment, **halves round up**: `math.floor(x / inc + 0.5) * inc`. (Don't use the built-in `round`; it uses banker's rounding.)
   - `plates_per_side(total_lb: float, bar_lb: float = 45.0, plates: tuple[float, ...] = (45, 35, 25, 10, 5, 2.5)) -> list[float]` uses greedy largest-first. `total == bar` → `[]`. It raises `ValueError` if `total < bar` or the weight can't be loaded exactly.

4. **`engine/onramp.py`**
   - Week parameters (constants): `A = (load 0.60, sets 0.50, cap 6.0)`, `B = (0.75, 0.70, 7.0)`, `C = (0.90, 1.00, 8.0)`.
   - `onramp_prescription(week: str, sets: int, reps: int, weight_lb: float | None, target_rpe: float | None) -> Prescription`:
     - sets: if `sets <= 1` keep it; otherwise `min(sets, max(2, ceil(sets * frac)))`. Use integer math (store the fractions as percent ints, e.g. `ceil(sets * 70 / 100)` via `-(-sets * 70 // 100)`) so float error can't push an exact product over an integer.
     - weight: `round_to_increment(weight_lb * load)`, or `None` if `weight_lb` is `None`.
     - rpe_cap: `min(week_cap, target_rpe - 1)` if `target_rpe` is given, else `week_cap`.
     - reps unchanged. Unknown week → `ValueError`.
   - `can_advance_onramp(soreness: int, pain: bool, all_sets_ok: bool) -> bool` returns `soreness <= 5 and not pain and all_sets_ok`.
   - `next_phase_step(week: str, advance: bool) -> str`: `A→B→C→"program"` when `advance`, otherwise returns `week` unchanged.

5. **`engine/e1rm.py`**: `e1rm(weight_lb: float, reps: int, rpe: float) -> float | None` returns `weight * (1 + (reps + (10 - rpe)) / 30)`. Return `None` if `rpe < 7`, `rpe > 10`, or `reps < 1`.

6. **`engine/progression.py`**
   - `decide(sets: list[SetResult], previous_misses: int) -> tuple[Decision, int]` (returns the decision and the new miss count):
     1. Empty list → `ValueError`.
     2. **Missed** = any set with `reps < prescribed_reps` or `form_ok is False`. If missed: `misses = previous_misses + 1`; if `misses >= 2` → `(RESET, 0)`, else `(REPEAT, misses)`.
     3. Otherwise, if any set has a `target_rpe` and (`rpe is None` or `rpe >= target_rpe + 1`) → `(REPEAT, 0)`.
     4. Otherwise → `(ADVANCE, 0)`.
   - `next_weight(current_lb: float, decision: Decision, category: str, rpe_based: bool, program_next_lb: float | None = None) -> float`:
     - `RESET` → `round_to_increment(current_lb * 0.90)`
     - `REPEAT` → `current_lb`
     - `ADVANCE` → if `rpe_based`: `current_lb + 10` when `category == "deadlift"`, else `current_lb + 5`. If not `rpe_based`: return `program_next_lb`; raise `ValueError` if it is `None`.
     - Valid categories: `"squat"`, `"deadlift"`, `"accessory"`; anything else → `ValueError`.

7. **`engine/readiness.py`**
   - `readiness_adjust(soreness: int, sleep: int, energy: int, previous_soreness: int | None) -> Adjustment`:
     - Any value outside 0–10 → `ValueError`.
     - `soreness >= 7` → `load_factor 0.90`, `rpe_cap_delta -1.0`; `flag_repeat_week = previous_soreness is not None and previous_soreness >= 7`.
     - Otherwise → `load_factor 1.0`, `rpe_cap_delta 0.0`, `flag_repeat_week False`.
     - `suggest_smart_rest = sleep <= 3 and energy <= 3` (independent of soreness).
   - `apply_adjustment(p: Prescription, a: Adjustment) -> Prescription`: weight → `round_to_increment(weight * load_factor)` (`None` stays `None`); `rpe_cap + delta` (`None` stays `None`); sets and reps unchanged.

8. **`engine/xp.py`**
   - Constants: `SESSION_AS_PRESCRIBED = 100`, `SET_LOGGED = 5`, `SET_ON_TARGET = 5`, `READINESS_CHECKIN = 10`, `GATED_ADJUSTMENT = 50`, `SMART_REST = 25`, `WEEKLY_CHECKIN = 50`, `E1RM_PR = 150`, `DELOAD_WEEK = 200`, `COMMUTE_MULTIPLIER = 1.5`.
   - `set_xp(rpe: float | None, form_ok: bool, target_rpe: float | None, rpe_cap: float | None) -> int` returns 0 if `rpe is None`, `not form_ok`, or (`rpe_cap is not None and rpe > rpe_cap`). Otherwise it's `SET_LOGGED`, plus `SET_ON_TARGET` if `target_rpe is not None and abs(rpe - target_rpe) <= 0.5`.
   - `session_xp(all_sets_logged: bool, all_within_cap: bool) -> int` returns `SESSION_AS_PRESCRIBED` if both are true, else 0.
   - `ride_xp(miles: float, commute: bool, zone: int) -> int` returns 0 if `zone > 2`, else `math.floor(miles * (COMMUTE_MULTIPLIER if commute else 1))`.
   - `level(total_xp: int) -> int` returns `math.isqrt(total_xp // 100) + 1`, with `ValueError` if negative.
   - `xp_to_next_level(total_xp: int) -> int` returns `100 * level(total_xp) ** 2 - total_xp`.

9. **Tests** in `tests/`, one file per module. Each case below must exist as its own named test:
   - rounding: `202.5 → 205`, `168.75 → 170`, `167.4 → 165`. Plates: `225 → [45, 45]`, `135 → [45]`, `185 → [45, 25]`, `205 → [45, 35]`, `170 → [45, 10, 5, 2.5]`, `45 → []`, `136 → ValueError`, `40 → ValueError`.
   - onramp (the ONRAMP.md example, 4×5 @ 225, target 8): A → `(2, 5, 135.0, 6.0)`, B → `(3, 5, 170.0, 7.0)`, C → `(4, 5, 205.0, 7.0)`. Sets: `sets=10, B → 7`; `sets=3, A → 2`; `sets=5, A → 3`; `sets=1, A → 1`. `target_rpe=None` with C → cap 8.0. `weight None` → `None`. `week "D"` → `ValueError`. Gate: `(5, False, True) → True`, `(6, False, True) → False`, pain → False, sets not ok → False. `next_phase_step`: `C, True → "program"`; `B, False → "B"`.
   - e1rm: `(225, 5, 8) → 277.5` (use `pytest.approx`); `rpe 6.5 → None`; `reps 0 → None`.
   - progression: clean sets at target → ADVANCE; a set at `target + 1` → REPEAT; `rpe None` with a target → REPEAT; first miss → `(REPEAT, 1)`; second consecutive miss (previous 1) → `(RESET, 0)`; form_ok False counts as a miss; empty → ValueError. `next_weight`: RESET 225 → 205; ADVANCE rpe-based deadlift 315 → 325; squat 225 → 230; non-rpe with `program_next 235` → 235; non-rpe without it → ValueError; bad category → ValueError.
   - readiness: soreness 7 → (0.9, −1.0); soreness 7 with previous 8 → `flag_repeat_week True`; previous 6 → False; sleep 3 + energy 3 → smart rest True; sleep 3 + energy 4 → False; value 11 → ValueError. `apply_adjustment` on `(4, 5, 225.0, 8.0)` with soreness 7 → `(4, 5, 205.0, 7.0)` (202.5 rounds up to 205).
   - xp: `set_xp(8, True, 8, 9) → 10`; `(8.5, True, 8, 9) → 10`; `(9, True, 8, 9) → 5`; `(9.5, True, 8, 9) → 0` (over cap); `(8, False, 8, 9) → 0`; `(None, True, 8, 9) → 0`; `(7, True, None, None) → 5`. `ride_xp(17.3, True, 2) → 25`; `(8.2, False, 2) → 8`; `(10, False, 3) → 0`. `level`: 0→1, 99→1, 100→2, 399→2, 400→3, 1600→5, 8100→10, 36100→20; −1 → ValueError. `xp_to_next_level(150) → 250`.

10. `README.md`: rewrite it with a short project description and dev commands (`uv sync`, `uv run pytest`, `uv run ruff check .`). Keep the existing pointers to `CLAUDE.md`, `DEEPSEEK.md`, `docs/`, and `handoffs/`. Under 30 lines.

**Do not:**
- Add any DB, web, CLI, config, or file I/O code (T003/T004).
- Read the clock, randomness, or environment inside `engine/`.
- Modify `docs/`, `program/`, `CLAUDE.md`, `DEEPSEEK.md`, `tools/`, or the handoff files other than your report, `TO_CLAUDE.md`, and your BOARD row.
- Open or read `.env`.
- Run `git commit`, or `git init` (the user handles git).

## Acceptance criteria
All must pass:
1. `uv sync` succeeds.
2. `uv run pytest -q` passes, and every test case listed in Scope §9 is present.
3. `uv run ruff check .` is clean and `uv run ruff format --check .` is clean.
4. `grep -rnE "^\s*(import|from) (os|sys|pathlib|io|sqlite3|sqlalchemy|fastapi|datetime|time|random|httpx|requests)\b" src/gigalegs/engine` prints nothing, and `grep -rn "open(" src/gigalegs/engine` prints nothing.
5. `uv run python -c "from gigalegs.engine import onramp_prescription; print(onramp_prescription('B', 4, 5, 225.0, 8.0))"` prints `Prescription(sets=3, reps=5, weight_lb=170.0, rpe_cap=7.0)`.
6. `uv run python -c "from gigalegs.engine import level, ride_xp; print(level(1600), ride_xp(17.3, True, 2))"` prints `5 25`.

## Report
Follow `DEEPSEEK.md` steps 5–8: report at `handoffs/reports/T001-report.md`, overwrite `handoffs/TO_CLAUDE.md`, set T001 to `review`, send a Discord `done` notification, and tell the user.
