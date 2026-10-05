"""Pure rules engine: no I/O, no DB, no clock. The authority on every number (D2)."""

from .badges import BADGES, BadgeFacts, earned
from .e1rm import e1rm
from .onramp import can_advance_onramp, next_phase_step, onramp_prescription
from .program import (
    DayPlan,
    Position,
    PrescribedExercise,
    Program,
    day_plan,
    load_program,
    next_position,
)
from .progression import adjust_program_weight, decide, next_weight
from .readiness import apply_adjustment, readiness_adjust
from .rounding import plates_per_side, round_to_increment
from .schedule import DayContext, Recommendation, recommend
from .streaks import WeekFacts, freezes_available, week_counts, weekly_streak
from .types import Adjustment, Decision, Prescription, SetResult
from .xp import level, level_title, ride_xp, session_xp, set_xp, xp_to_next_level

__all__ = [
    "BADGES",
    "Adjustment",
    "BadgeFacts",
    "DayContext",
    "DayPlan",
    "Decision",
    "Position",
    "PrescribedExercise",
    "Prescription",
    "Program",
    "Recommendation",
    "SetResult",
    "WeekFacts",
    "adjust_program_weight",
    "apply_adjustment",
    "can_advance_onramp",
    "day_plan",
    "decide",
    "e1rm",
    "earned",
    "freezes_available",
    "level",
    "level_title",
    "load_program",
    "next_phase_step",
    "next_position",
    "next_weight",
    "onramp_prescription",
    "plates_per_side",
    "readiness_adjust",
    "recommend",
    "ride_xp",
    "round_to_increment",
    "session_xp",
    "set_xp",
    "week_counts",
    "weekly_streak",
    "xp_to_next_level",
]
