"""Pre-session readiness gates (METHODOLOGY §4)."""

from dataclasses import replace

from .rounding import round_to_increment
from .types import Adjustment, Prescription


def readiness_adjust(
    soreness: int, sleep: int, energy: int, previous_soreness: int | None
) -> Adjustment:
    for name, v in (("soreness", soreness), ("sleep", sleep), ("energy", energy)):
        if not 0 <= v <= 10:
            raise ValueError(f"{name} must be 0-10, got {v}")
    smart_rest = sleep <= 3 and energy <= 3
    if soreness >= 7:
        return Adjustment(
            load_factor=0.90,
            rpe_cap_delta=-1.0,
            flag_repeat_week=previous_soreness is not None and previous_soreness >= 7,
            suggest_smart_rest=smart_rest,
        )
    return Adjustment(1.0, 0.0, False, smart_rest)


def apply_adjustment(p: Prescription, a: Adjustment) -> Prescription:
    return replace(
        p,
        weight_lb=round_to_increment(p.weight_lb * a.load_factor)
        if p.weight_lb is not None
        else None,
        rpe_cap=p.rpe_cap + a.rpe_cap_delta if p.rpe_cap is not None else None,
    )
