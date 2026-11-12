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

# Season v2 missions (GAMIFICATION v2, D29)
FLOOR = 30
MISSION = 100
KEY_MISSION = 150  # long run, tempo, long ride, race
PUSH = 20
PUSHES_PER_WEEK = 2
WEEK_DONE = 100
EASY_WEEK_DONE = 200  # down, taper, recovery, and race weeks are worth more
WEIGHT_INCREASE = 25  # per exercise per planned session, when double progression adds weight


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


# GAMIFICATION v2: full-body/endurance theme. Same curve as v1; one title per 2 levels.
LEVEL_TITLES = (
    "Rookie",
    "Regular",
    "Grinder",
    "Hybrid",
    "Engine",
    "Machine",
    "Giga",
)


def level_title(lvl: int) -> str:
    return LEVEL_TITLES[min(len(LEVEL_TITLES) - 1, (lvl - 1) // 2)]
