from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True)
class Prescription:
    sets: int
    reps: int
    weight_lb: float | None
    rpe_cap: float | None


@dataclass(frozen=True)
class SetResult:
    prescribed_reps: int
    reps: int
    rpe_cap: float | None
    rpe: float | None
    form_ok: bool


@dataclass(frozen=True)
class Adjustment:
    load_factor: float
    rpe_cap_delta: float
    flag_repeat_week: bool
    suggest_smart_rest: bool


class Decision(StrEnum):
    ADVANCE = "advance"
    REPEAT = "repeat"
    RESET = "reset"
