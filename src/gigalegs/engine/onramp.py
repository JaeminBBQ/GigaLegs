"""3-week on-ramp scaling (docs/training/ONRAMP.md, D4)."""

from .rounding import round_to_increment
from .types import Prescription

# week: (load %, sets %, RPE cap, hold % of best)
ONRAMP_WEEKS: dict[str, tuple[int, int, float, int]] = {
    "A": (60, 50, 6.0, 50),
    "B": (75, 70, 7.0, 70),
    "C": (90, 100, 8.0, 90),
}
ONRAMP_ORDER = ("A", "B", "C")


def _week(week: str) -> tuple[int, int, float, int]:
    try:
        return ONRAMP_WEEKS[week]
    except KeyError:
        raise ValueError(f"unknown on-ramp week {week!r}") from None


def scale_sets(sets: int, week: str) -> int:
    _, sets_pct, _, _ = _week(week)
    if sets <= 1:
        return sets
    scaled = -(-sets * sets_pct // 100)  # integer ceil, no float error
    return min(sets, max(2, scaled))


def onramp_rpe_cap(week: str, program_max_rpe: float | None) -> float:
    _, _, week_cap, _ = _week(week)
    if program_max_rpe is None:
        return week_cap
    return min(week_cap, program_max_rpe - 1)


def hold_percent(week: str) -> int:
    return _week(week)[3]


def onramp_prescription(
    week: str, sets: int, reps: int, weight_lb: float | None, target_rpe: float | None
) -> Prescription:
    load_pct, _, _, _ = _week(week)
    weight = round_to_increment(weight_lb * load_pct / 100) if weight_lb is not None else None
    return Prescription(
        sets=scale_sets(sets, week),
        reps=reps,
        weight_lb=weight,
        rpe_cap=onramp_rpe_cap(week, target_rpe),
    )


def can_advance_onramp(soreness: int, pain: bool, all_sets_ok: bool) -> bool:
    return soreness <= 5 and not pain and all_sets_ok


def next_phase_step(week: str, advance: bool) -> str:
    _week(week)
    if not advance:
        return week
    i = ONRAMP_ORDER.index(week)
    return ONRAMP_ORDER[i + 1] if i + 1 < len(ONRAMP_ORDER) else "program"
