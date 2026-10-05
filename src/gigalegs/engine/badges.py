"""Badges (docs/GAMIFICATION.md). Earned once, never revoked, no XP attached."""

from dataclasses import dataclass

PLATE_MILESTONES = (225, 275, 315, 365, 405)

BADGES: dict[str, tuple[str, str]] = {
    "patience_pays": ("Patience Pays", "Finish the 3-week on-ramp without skipping ahead"),
    "first_session": ("First Session", "Finish your first lifting session"),
    "iron_lungs": ("Iron Lungs", "Ride 100 commute miles"),
    "smart_rest": (
        "Smart Rest",
        "Take 3 smart calls: repeating an on-ramp week or a smart rest day",
    ),
    "plate_225": ("Plate Collector 225", "Squat e1RM of 225 lb"),
    "plate_275": ("Plate Collector 275", "Squat e1RM of 275 lb"),
    "plate_315": ("Plate Collector 315", "Squat e1RM of 315 lb"),
    "plate_365": ("Plate Collector 365", "Squat e1RM of 365 lb"),
    "plate_405": ("Plate Collector 405", "Squat e1RM of 405 lb"),
    "commuter": ("Commuter", "Reach bike stage 5"),
}


@dataclass(frozen=True)
class BadgeFacts:
    finished_onramp: bool
    finished_sessions: int
    commute_miles: float
    gated_repeats: int
    smart_rests: int
    best_squat_e1rm: float | None
    bike_stage: int


def earned(facts: BadgeFacts) -> set[str]:
    out: set[str] = set()
    if facts.finished_onramp:
        out.add("patience_pays")
    if facts.finished_sessions >= 1:
        out.add("first_session")
    if facts.commute_miles >= 100:
        out.add("iron_lungs")
    if facts.gated_repeats + facts.smart_rests >= 3:
        out.add("smart_rest")
    if facts.best_squat_e1rm is not None:
        out.update(f"plate_{m}" for m in PLATE_MILESTONES if facts.best_squat_e1rm >= m)
    if facts.bike_stage >= 5:
        out.add("commuter")
    return out
