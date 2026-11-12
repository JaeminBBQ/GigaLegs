"""Week recap wording: what a week unlocked for run and long-ride levels (D35–D37).

Pure: callers pass in the levels the engine already computed (`effective_level`) for the
week and the one after. No new rules live here; it only describes the level lag.
"""

from .season import LAG_RIDE_UNTIL, LAG_RUN_UNTIL, MIN_RUNS_TO_ADVANCE

RECAP_DAYS = (0, 1, 2)  # Monday–Wednesday: Today shows the "Last week" card


def calendar_rules(next_week: int, lag_until: int) -> bool:
    """True when the week after uses the calendar, not the level lag (effective_level)."""
    return next_week <= 1 or next_week > lag_until


def _runs(done: int) -> str:
    """'3 runs, 2 needed' rather than '3 of 2 runs'."""
    return f"{done} run{'' if done == 1 else 's'}, {MIN_RUNS_TO_ADVANCE} needed"


def run_unlock(
    week_no: int, level: int, next_level: int, runs_done: int, forgiven: bool = False
) -> str:
    nxt = week_no + 1
    if calendar_rules(nxt, LAG_RUN_UNTIL):
        return f"Runs follow the calendar: Week {nxt} uses Week {nxt}'s runs."
    if next_level > level:
        why = "forgiven week" if forgiven and runs_done < MIN_RUNS_TO_ADVANCE else ""
        tail = f" ({why})" if why else f" ({_runs(runs_done)})"
        return f"Runs move up to Week {next_level}'s level{tail}."
    return f"Runs repeat Week {level}'s level ({_runs(runs_done)})."


def ride_unlock(
    week_no: int, level: int, next_level: int, long_done: bool, forgiven: bool = False
) -> str:
    nxt = week_no + 1
    if calendar_rules(nxt, LAG_RIDE_UNTIL):
        return f"The long ride follows the calendar: Week {nxt} uses Week {nxt}'s length."
    if next_level > level:
        tail = " (forgiven week)" if forgiven and not long_done else ""
        return f"The long ride moves up to Week {next_level}'s length{tail}."
    return f"The long ride repeats Week {level}'s length (not done this week)."
