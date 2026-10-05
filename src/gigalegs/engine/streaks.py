"""Weekly streaks (docs/GAMIFICATION.md). The unit is the week, not the day."""

from dataclasses import dataclass

FREEZE_EVERY_WEEKS = 6


@dataclass(frozen=True)
class WeekFacts:
    lift_sessions: int
    active_days: int
    protected: bool


def week_counts(f: WeekFacts) -> bool:
    """True if the week's plan was done (2+ lifts on 4+ active days) or properly gated."""
    return f.protected or (f.lift_sessions >= 2 and f.active_days >= 4)


def weekly_streak(weeks: list[WeekFacts], freezes_available: int) -> tuple[int, int]:
    """Count back from the newest week; a non-counting week burns a freeze
    (newest miss first) or stops the streak. Returns (streak_weeks, freezes_used)."""
    streak = 0
    used = 0
    for f in reversed(weeks):
        if week_counts(f):
            streak += 1
        elif used < freezes_available:
            used += 1
        else:
            break
    return streak, used


def freezes_available(total_weeks_since_start: int, used: int) -> int:
    """One freeze per 6 started weeks, minus those already used, never negative."""
    return max(0, total_weeks_since_start // FREEZE_EVERY_WEEKS - used)
