"""Daily recommendation for a flexible schedule (METHODOLOGY §3b, D20)."""

from dataclasses import dataclass, field

MIN_HOURS_BETWEEN_HEAVY = 48
PREFERRED_HOURS_BETWEEN_HEAVY = 72
MIN_HOURS_BETWEEN_LIFTS = 20
MAX_PROGRAM_SESSIONS_7D = 3
MAX_ACTIVE_STREAK_WITHOUT_EASY = 6

BIKE_STAGE_RIDE = {
    1: "Easy ride, 20-45 min, flat (Marina / river path)",
    2: "Easy ride, 45-75 min; include part of the commute route",
    3: "One-way commute in (or an easy 60-75 min ride)",
    4: "Commute (round trip or one way) at conversation pace",
    5: "Commute, easy pace",
}


@dataclass(frozen=True)
class DayContext:
    next_day_heavy: bool
    hours_since_heavy: float | None  # None = never
    hours_since_lift: float | None
    program_sessions_7d: int
    easy_day_in_last_7d: bool  # a rest or recovery day in the rolling 7 days
    active_streak: int  # consecutive days with any activity, ending yesterday
    yesterday_hard: bool  # heavy leg session or a ride over 60 min
    open_pain: bool  # pain flagged in the last 3 days
    soreness: int | None = None  # today's morning soreness, 0-10
    sleep: int | None = None
    energy: int | None = None
    bike_stage: int = 1
    already_lifted_today: bool = False


@dataclass(frozen=True)
class Recommendation:
    kind: str  # lift | ride | recovery | rest
    title: str
    reasons: list[str] = field(default_factory=list)
    also_ok: list[str] = field(default_factory=list)


def lift_blockers(ctx: DayContext) -> list[str]:
    """Why the next queued lift can't happen today (empty = good to go)."""
    out: list[str] = []
    if ctx.already_lifted_today:
        out.append("you already lifted today")
    if ctx.hours_since_lift is not None and ctx.hours_since_lift < MIN_HOURS_BETWEEN_LIFTS:
        out.append(
            f"last lift was {ctx.hours_since_lift:.0f} h ago (need {MIN_HOURS_BETWEEN_LIFTS})"
        )
    if ctx.program_sessions_7d >= MAX_PROGRAM_SESSIONS_7D:
        out.append(f"already {ctx.program_sessions_7d} program sessions in the last 7 days")
    if ctx.next_day_heavy:
        h = ctx.hours_since_heavy
        if h is not None and h < MIN_HOURS_BETWEEN_HEAVY:
            out.append(f"last heavy leg day was {h:.0f} h ago (need {MIN_HOURS_BETWEEN_HEAVY})")
        if ctx.yesterday_hard:
            out.append("yesterday was a hard day")
        if ctx.soreness is not None and ctx.soreness >= 7:
            out.append(f"leg soreness is {ctx.soreness}/10")
    return out


def recommend(ctx: DayContext) -> Recommendation:
    ride = BIKE_STAGE_RIDE.get(ctx.bike_stage, BIKE_STAGE_RIDE[1])
    if ctx.open_pain:
        return Recommendation(
            "recovery",
            "Recovery: walk or mobility, 20-30 min",
            ["You flagged pain in the last 3 days. Let it settle, and tell Claude where it hurts."],
            ["Rest"],
        )
    if ctx.sleep is not None and ctx.energy is not None and ctx.sleep <= 3 and ctx.energy <= 3:
        return Recommendation(
            "rest",
            "Smart rest",
            ["Sleep and energy are both very low. A rest day keeps your streak (+25 XP)."],
            ["Recovery walk"],
        )
    if ctx.active_streak >= MAX_ACTIVE_STREAK_WITHOUT_EASY and not ctx.easy_day_in_last_7d:
        return Recommendation(
            "recovery",
            "Recovery day: walk, mobility, or a spin under 30 min",
            [f"{ctx.active_streak} active days in a row with no easy day this week."],
            ["Rest"],
        )
    blockers = lift_blockers(ctx)
    if not blockers:
        reasons = ["Next up in your program queue, and the spacing rules are met."]
        if (
            ctx.next_day_heavy
            and ctx.hours_since_heavy is not None
            and ctx.hours_since_heavy < PREFERRED_HOURS_BETWEEN_HEAVY
        ):
            reasons.append("It's been under 72 h since the last heavy day; fine, but warm up well.")
        if ctx.soreness is not None and ctx.soreness >= 7:
            reasons.append("Soreness is high: loads drop 10% and the RPE cap drops by 1.")
        return Recommendation("lift", "Lift", reasons, [ride])
    if ctx.yesterday_hard or (ctx.soreness is not None and ctx.soreness >= 7):
        return Recommendation(
            "recovery",
            "Recovery: walk, mobility, or an easy spin under 30 min",
            ["Not lifting today: " + "; ".join(blockers) + "."],
            ["Rest"],
        )
    reasons = ["Not lifting today: " + "; ".join(blockers) + "."]
    if ctx.next_day_heavy:
        reasons.append("Heavy legs are next, so keep it easy: Zone 1-2, conversational.")
    return Recommendation("ride", ride, reasons, ["Recovery walk", "Rest"])
