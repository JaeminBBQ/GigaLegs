"""Load progression (METHODOLOGY §3, D6)."""

from .rounding import round_to_increment
from .types import Decision, SetResult

CATEGORIES = ("squat", "deadlift", "accessory")
RESET_FACTOR = 0.90


def decide(sets: list[SetResult], previous_misses: int) -> tuple[Decision, int]:
    """Returns (decision, new consecutive-miss count)."""
    if not sets:
        raise ValueError("no sets to judge")
    missed = any(s.reps < s.prescribed_reps or not s.form_ok for s in sets)
    if missed:
        misses = previous_misses + 1
        return (Decision.RESET, 0) if misses >= 2 else (Decision.REPEAT, misses)
    over_cap = any(s.rpe_cap is not None and (s.rpe is None or s.rpe > s.rpe_cap) for s in sets)
    if over_cap:
        return Decision.REPEAT, 0
    return Decision.ADVANCE, 0


def next_weight(
    current_lb: float,
    decision: Decision,
    category: str,
    rpe_based: bool,
    program_next_lb: float | None = None,
) -> float:
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category!r}")
    if decision is Decision.RESET:
        return round_to_increment(current_lb * RESET_FACTOR)
    if decision is Decision.REPEAT:
        return current_lb
    if rpe_based:
        return current_lb + (10 if category == "deadlift" else 5)
    if program_next_lb is None:
        raise ValueError("program_next_lb is required for program-weight lifts")
    return program_next_lb


def adjust_program_weight(
    program_lb: float, last_lb: float | None, last_decision: Decision | None
) -> float:
    """The written program weight, held back if the last exposure didn't earn an increase."""
    if last_lb is None or last_decision is None or last_decision is Decision.ADVANCE:
        return program_lb
    if last_decision is Decision.REPEAT:
        return min(program_lb, last_lb)
    return min(program_lb, round_to_increment(last_lb * RESET_FACTOR))
