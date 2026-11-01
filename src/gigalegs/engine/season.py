"""Season v2 rules (METHODOLOGY v2, D27–D32): weeks as checklists, today's suggestion,
gym double progression, and the daily streak. Pure: callers pass dates and history in."""

from dataclasses import dataclass, field
from datetime import date, timedelta

PEAK_GYM_WEEKS = range(21, 26)  # half peak + taper: legs -1 set, cap RPE 7
LAG_RUN_UNTIL = 23  # runs repeat a level you didn't finish; from the taper on, the calendar rules
LAG_RIDE_UNTIL = 30
MIN_RUNS_TO_ADVANCE = 2
FREEZE_EVERY_DAYS = 14
PAIN_MSG = (
    "You flagged pain in the last 3 days. Floor only (walk or mobility) until it's gone, "
    "and tell Claude where it hurts."
)
MAX_FREEZES = 2


# ---------- the plan ----------


@dataclass(frozen=True)
class Slot:
    key: str
    kind: str  # gym | run | ride
    title: str
    detail: str = ""
    template: str | None = None  # gym only: A | B | U
    hard: bool = False
    long: bool = False
    tempo: bool = False
    push: bool = False


@dataclass(frozen=True)
class Week:
    week: int
    start: date
    label: str
    phase: str
    tag: str | None  # starter | down | taper | race | recovery | None
    slots: tuple[Slot, ...]
    note: str = ""

    @property
    def end(self) -> date:
        return self.start + timedelta(days=6)

    def slot(self, key: str) -> Slot | None:
        return next((s for s in self.slots if s.key == key), None)


@dataclass(frozen=True)
class Season:
    id: str
    name: str
    weeks: tuple[Week, ...]
    gym_templates: dict
    floor_menu: tuple[dict, ...]
    push: dict
    events: tuple[dict, ...]

    def week(self, n: int) -> Week:
        n = max(0, min(n, self.weeks[-1].week))
        return next(w for w in self.weeks if w.week == n)

    def week_for(self, d: date) -> Week:
        """The calendar week containing d (before the season: the first week; after: the last)."""
        current = self.weeks[0]
        for w in self.weeks:
            if w.start <= d:
                current = w
        return current


def load_season(data: dict) -> Season:
    weeks = tuple(
        Week(
            week=int(w["week"]),
            start=date.fromisoformat(w["start"]),
            label=w["label"],
            phase=w.get("phase", ""),
            tag=w.get("tag"),
            note=w.get("note", ""),
            slots=tuple(
                Slot(
                    key=s["key"],
                    kind=s["kind"],
                    title=s["title"],
                    detail=s.get("detail", ""),
                    template=s.get("template"),
                    hard=bool(s.get("hard")),
                    long=bool(s.get("long")),
                    tempo=bool(s.get("tempo")),
                    push=bool(s.get("push")),
                )
                for s in w["slots"]
            ),
        )
        for w in data["weeks"]
    )
    return Season(
        id=data["id"],
        name=data["name"],
        weeks=tuple(sorted(weeks, key=lambda w: w.week)),
        gym_templates=data["gym_templates"],
        floor_menu=tuple(data["floor_menu"]),
        push=data["push"],
        events=tuple(data.get("events", [])),
    )


def effective_level(calendar_week: int, completed_weeks: set[int], lag_until: int) -> int:
    """Which week's prescription to use for runs or long rides (METHODOLOGY §4, ≤10% growth).

    You only move up a level after a week where you actually did that work, so a missed
    week repeats instead of jumping ahead. Weeks 0–1 always use the calendar; after
    `lag_until`, the calendar rules (taper and race weeks can't move).
    """
    if calendar_week <= 1 or calendar_week > lag_until:
        return calendar_week
    level = 1
    for w in range(1, calendar_week):
        if w in completed_weeks:
            level += 1
    return min(level, calendar_week)


def week_slots(season: Season, calendar_week: int, run_level: int, ride_level: int) -> list[Slot]:
    """The checklist for a calendar week: gym from the calendar, runs/long ride from their levels."""
    cal = season.week(calendar_week)
    ride_src = season.week(ride_level)
    gyms = [s for s in cal.slots if s.kind == "gym"]
    runs = [s for s in season.week(run_level).slots if s.kind == "run"]
    rides = [
        (ride_src.slot(s.key) or s) if s.long and ride_level != calendar_week else s
        for s in cal.slots
        if s.kind == "ride"
    ]
    return gyms + runs + rides


# ---------- today's suggestion (METHODOLOGY §3) ----------


@dataclass(frozen=True)
class DayDone:
    """What was logged on one day (standard or push missions only)."""

    kinds: frozenset[str] = frozenset()  # gym | run | ride
    hard: bool = False
    long_or_tempo_run: bool = False
    long_ride: bool = False


@dataclass(frozen=True)
class Suggestion:
    slot: Slot | None
    reasons: list[str] = field(default_factory=list)
    also_ok: list[Slot] = field(default_factory=list)
    floor_only: bool = False


def suggest(
    remaining: list[Slot],
    today: date,
    week_no: int,
    today_done: DayDone,
    yesterday: DayDone,
    day_before: DayDone,
    pain_recent: bool,
) -> Suggestion:
    if pain_recent:
        return Suggestion(
            None,
            [PAIN_MSG],
            floor_only=True,
        )
    if not remaining:
        return Suggestion(None, ["This week's checklist is done. A floor keeps the streak."])

    weekend = today.weekday() >= 5
    reasons: dict[str, str] = {}

    def allowed(s: Slot) -> bool:
        if s.kind == "run" and week_no <= 12 and "run" in yesterday.kinds:
            reasons[s.key] = "no runs on back-to-back days in Weeks 1–12"
            return False
        if s.kind == "run" and (s.long or s.tempo) and yesterday.long_or_tempo_run:
            reasons[s.key] = "long run and tempo never on back-to-back days"
            return False
        if s.hard and yesterday.hard and day_before.hard:
            reasons[s.key] = "no third hard day in a row"
            return False
        if s.kind == "run" and s.long and today_done.long_ride:
            reasons[s.key] = "not on the same day as the long ride"
            return False
        if s.kind == "ride" and s.long and today_done.long_or_tempo_run:
            reasons[s.key] = "not on the same day as the long run"
            return False
        if s.kind in today_done.kinds:
            reasons[s.key] = f"you already did a {s.kind} session today"
            return False
        friday = today.weekday() == 4
        hard_run_left = any(r.kind == "run" and (r.long or r.tempo) for r in remaining)
        if s.kind == "gym" and s.template == "A" and friday and hard_run_left:
            reasons[s.key] = "Gym A isn't the day before a long or tempo run (likely tomorrow)"
            return False
        return True

    ok = [s for s in remaining if allowed(s)]
    if not ok:
        why = sorted(set(reasons.values()))
        return Suggestion(None, ["Nothing on the checklist fits today: " + "; ".join(why) + "."])

    def rank(s: Slot) -> tuple:
        if weekend:
            order = (s.kind == "run" and s.long, s.kind == "ride" and s.long, s.kind == "gym")
        else:
            order = (
                s.kind == "gym",
                s.kind == "run" and s.tempo,
                s.kind == "run" and not s.long,
                s.kind == "ride" and not s.long,
            )
        return tuple(not x for x in order)

    ok.sort(key=rank)
    best = ok[0]
    why = []
    if today_done.kinds:
        why.append("Already did one today; a second session is fine if you have it in you.")
    if weekend and best.long:
        why.append("Weekend: the best day for the long one.")
    elif best.kind == "gym":
        why.append("Next gym session on the checklist.")
    else:
        why.append("Next on the checklist that fits the spacing rules.")
    return Suggestion(best, why, also_ok=ok[1:3])


# ---------- gym: double progression (METHODOLOGY §5) ----------


@dataclass(frozen=True)
class SetPerf:
    weight: float | None
    reps: int | None
    rpe: float | None
    form_ok: bool = True


@dataclass(frozen=True)
class GymTarget:
    sets: int
    reps: tuple[int, int]
    rpe_cap: float
    weight: float | None  # None = pick by feel
    note: str
    timed: bool = False  # reps are seconds held (planks)


def gym_rpe_cap(week_no: int, lower: bool) -> float:
    if week_no <= 2:
        return 7.0
    if lower and week_no in PEAK_GYM_WEEKS:
        return 7.0
    return 8.0 if lower else 9.0


def gym_sets(base: int, week_no: int, tag: str | None, lower: bool) -> int:
    n = base
    if tag in ("down", "taper", "recovery"):
        n -= 1
    if lower and week_no in PEAK_GYM_WEEKS:
        n -= 1
    return max(1, n)


def _session_result(sets: list[SetPerf], lo: int, hi: int, cap: float) -> str:
    """'top' (all sets at the top of the range, clean), 'fail', or 'mid'."""
    work = [s for s in sets if s.reps is not None]
    if not work:
        return "none"
    w = max((s.weight or 0) for s in work)
    work = [s for s in work if (s.weight or 0) == w]
    if any(not s.form_ok or s.reps < lo or (s.rpe is not None and s.rpe > cap) for s in work):
        return "fail"
    if all(s.reps >= hi and s.rpe is not None for s in work):
        return "top"
    return "mid"


def next_gym_weight(
    history: list[list[SetPerf]],
    reps: tuple[int, int],
    cap: float,
    inc: float,
    timed: bool = False,
) -> tuple[float | None, str]:
    """history = previous sessions of this exercise, newest first.

    timed: reps are seconds held; progression is by time, never by load.
    """
    sessions = [h for h in history if any(s.reps is not None for s in h)]
    lo, hi = reps
    if timed:
        if not sessions:
            return None, f"First time: hold with clean form, stop by RPE {cap:g}"
        if _session_result(sessions[0], lo, hi, cap) == "top":
            return None, f"Held {hi} s every time: make it harder (feet closer, arms farther)"
        return None, f"Add a few seconds until every hold reaches {hi} s"
    if not sessions:
        return None, "First time: pick a weight that feels like RPE " + f"{cap:g}"
    last = sessions[0]
    w = max((s.weight or 0) for s in last if s.reps is not None) or None
    result = _session_result(last, lo, hi, cap)
    if w is None:
        return None, "Bodyweight: add reps, then make it harder"
    if result == "top":
        return w + inc, f"Hit {hi} on every set last time: +{inc:g} lb"
    if result == "fail":
        if len(sessions) > 1 and _session_result(sessions[1], lo, hi, cap) == "fail":
            prev_w = max((s.weight or 0) for s in sessions[1] if s.reps is not None)
            if prev_w == w:
                new = round(w * 0.9 / 5) * 5
                return float(new), "Missed twice at this weight: −10%, build back up"
        return w, "Same weight: aim for clean reps inside the range"
    return w, f"Same weight: add reps until all sets hit {hi}"


# ---------- daily streak (GAMIFICATION v2) ----------


@dataclass(frozen=True)
class DailyStreak:
    days: int
    freezes: int
    done_today: bool


def daily_streak(active: set[date], today: date, excused: set[date] | None = None) -> DailyStreak:
    """Consecutive active days ending today (or yesterday, if today isn't logged yet).

    One freeze is earned per 14 active days in a row (hold at most 2); a missed day
    spends one instead of breaking the streak. Excused days (sick/pain rest) count as
    neither a miss nor an active day.
    """
    excused = excused or set()
    if not active:
        return DailyStreak(0, 0, False)
    d = min(active)
    streak = run = freezes = 0
    while d <= today:
        if d in active:
            streak += 1
            run += 1
            if run % FREEZE_EVERY_DAYS == 0:
                freezes = min(MAX_FREEZES, freezes + 1)
        elif d in excused:
            pass
        elif d == today:
            pass  # the day isn't over
        elif freezes:
            freezes -= 1
            run = 0
        else:
            streak = run = 0
        d += timedelta(days=1)
    return DailyStreak(streak, freezes, today in active)
