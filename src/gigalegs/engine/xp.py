"""XP and levels (docs/GAMIFICATION.md, D5). The game rewards compliance, not volume."""

import math

SESSION_AS_PRESCRIBED = 100
SET_LOGGED = 5
SET_ON_TARGET = 5
READINESS_CHECKIN = 10
GATED_ADJUSTMENT = 50
SMART_REST = 25
RECOVERY_DAY = 15
MORNING_CHECKIN = 5
WEEKLY_CHECKIN = 50
E1RM_PR = 150
DELOAD_WEEK = 200
COMMUTE_MULTIPLIER = 1.5


def set_xp(
    rpe: float | None,
    form_ok: bool,
    rpe_cap: float | None,
    rpe_range: tuple[float, float] | None = None,
) -> int:
    """No XP for unrated sets, broken form, or going over the cap.

    "On target" = inside the program's RPE range when it has one, otherwise
    within 2 RPE under the cap (on-ramp: working, but not too hard).
    """
    if rpe is None or not form_ok:
        return 0
    if rpe_cap is not None and rpe > rpe_cap:
        return 0
    xp = SET_LOGGED
    if rpe_range is not None:
        lo, hi = rpe_range
        if lo <= rpe <= hi:
            xp += SET_ON_TARGET
    elif rpe_cap is not None and rpe_cap - 2 <= rpe <= rpe_cap:
        xp += SET_ON_TARGET
    return xp


def session_xp(all_sets_logged: bool, all_within_cap: bool) -> int:
    return SESSION_AS_PRESCRIBED if all_sets_logged and all_within_cap else 0


def ride_xp(miles: float, commute: bool, zone: int) -> int:
    if zone > 2:
        return 0
    return math.floor(miles * (COMMUTE_MULTIPLIER if commute else 1))


def level(total_xp: int) -> int:
    if total_xp < 0:
        raise ValueError("XP can't be negative")
    return math.isqrt(total_xp // 100) + 1


def xp_to_next_level(total_xp: int) -> int:
    return 100 * level(total_xp) ** 2 - total_xp


def level_floor(lvl: int) -> int:
    return 100 * (lvl - 1) ** 2


LEVEL_TITLES = (
    "Quad Squire",
    "Calf Cadet",
    "Hamstring Knight",
    "Glute Baron",
    "Posterior Chain Count",
    "Squat Duke",
    "Pull Prince",
    "Iron Monarch",
    "Giga Legs",
)


def level_title(lvl: int) -> str:
    return LEVEL_TITLES[min(len(LEVEL_TITLES) - 1, (lvl - 1) // 2)]
