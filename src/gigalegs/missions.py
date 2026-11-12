"""Season v2 glue (D27–D32): missions, the week's checklist, gym targets, daily streak.

Every rule and number comes from engine/season.py and engine/xp.py; this module only
reads and writes the database.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session as Db

from . import services as S
from .config import get_settings
from .db import utcnow
from .engine import recap as RC
from .engine import season as SE
from .engine import xp as X
from .models import DayLog, Metric, Mission, Ride, Session, SetLog, XpEvent

EASY_TAGS = ("down", "taper", "recovery", "race")


# ---------- plan ----------


@lru_cache
def _load(path: str, mtime: float) -> SE.Season:
    return SE.load_season(json.loads(Path(path).read_text()))


def get_season() -> SE.Season | None:
    p = get_settings().season_path
    if not p.exists():
        return None
    return _load(str(p), p.stat().st_mtime)


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _missions(db: Db, uid: int, start: date, end: date) -> list[Mission]:
    return list(
        db.scalars(
            select(Mission)
            .where(Mission.user_id == uid, Mission.date >= start, Mission.date <= end)
            .order_by(Mission.date, Mission.id)
        )
    )


LEVEL_FORGIVE = "level_forgive"  # Metric kind: value = a plan week counted as done for levels


def forgiven_weeks(db: Db, uid: int) -> set[int]:
    """Weeks the coach chose to count as done for run/ride levels (D37), e.g. an on-ramp miss."""
    vals = db.scalars(
        select(Metric.value).where(Metric.user_id == uid, Metric.kind == LEVEL_FORGIVE)
    )
    return {int(v) for v in vals}


def forgive_week(db: Db, uid: int, week_no: int) -> bool:
    """Count `week_no` as done for run and long-ride levels. Returns False if it already was."""
    if week_no in forgiven_weeks(db, uid):
        return False
    db.add(
        Metric(
            user_id=uid,
            date=S.today(),
            kind=LEVEL_FORGIVE,
            value=float(week_no),
            created_at=utcnow(),
        )
    )
    db.flush()
    if get_season() is not None:
        _sync_weeks_from(db, uid, week_no)
    return True


@dataclass
class Levels:
    run: int
    ride: int
    run_missed: list[int]
    ride_missed: list[int]
    taper_risk: int = 0


def _levels(
    db: Db,
    uid: int,
    season: SE.Season,
    cal: int,
    run_asof: datetime | None = None,
    ride_asof: datetime | None = None,
) -> Levels:
    """Run and long-ride levels from what was actually done in earlier weeks.

    `run_asof` / `ride_asof` freeze a level as it stood when that week's first run / long
    ride was logged, so a later backdate or forgive can't swap the week's slots under
    sessions already done (D39).
    """
    ms = [m for m in _missions(db, uid, season.week(1).start, date.max) if m.plan_week < cal]
    run_weeks: dict[int, int] = {}
    ride_weeks: set[int] = set()
    for m in ms:
        if m.kind == "run" and (run_asof is None or m.created_at <= run_asof):
            run_weeks[m.plan_week] = run_weeks.get(m.plan_week, 0) + 1
        if m.kind == "ride" and m.long and (ride_asof is None or m.created_at <= ride_asof):
            ride_weeks.add(m.plan_week)
    forgives = list(
        db.execute(
            select(Metric.value, Metric.created_at).where(
                Metric.user_id == uid, Metric.kind == LEVEL_FORGIVE
            )
        )
    )

    def forgiven(asof: datetime | None) -> set[int]:
        return {int(v) for v, t in forgives if asof is None or t <= asof}

    done_runs = {w for w, n in run_weeks.items() if n >= SE.MIN_RUNS_TO_ADVANCE}
    done_runs |= forgiven(run_asof)
    ride_weeks |= forgiven(ride_asof)
    return Levels(
        SE.effective_level(cal, done_runs, SE.LAG_RUN_UNTIL),
        SE.effective_level(cal, ride_weeks, SE.LAG_RIDE_UNTIL),
        SE.missed_weeks(cal, done_runs, SE.LAG_RUN_UNTIL),
        SE.missed_weeks(cal, ride_weeks, SE.LAG_RIDE_UNTIL),
        SE.taper_jump_risk(cal, done_runs, SE.LAG_RUN_UNTIL),
    )


@dataclass
class WeekState:
    week: SE.Week
    run_level: int
    ride_level: int
    slots: list[SE.Slot]
    done: dict[str, Mission]
    missions: list[Mission]
    pushes_used: int
    run_missed: list[int] = field(default_factory=list)
    ride_missed: list[int] = field(default_factory=list)
    taper_risk: int = 0

    @property
    def remaining(self) -> list[SE.Slot]:
        return [s for s in self.slots if s.key not in self.done]

    @property
    def complete(self) -> bool:
        return bool(self.slots) and not self.remaining


def week_state(db: Db, uid: int, d: date) -> WeekState | None:
    season = get_season()
    if season is None:
        return None
    wk = season.week_for(d)
    ms = [m for m in _missions(db, uid, wk.start, wk.end) if m.plan_week == wk.week]
    first_run = min((m.created_at for m in ms if m.kind == "run"), default=None)
    first_long = min((m.created_at for m in ms if m.kind == "ride" and m.long), default=None)
    lv = _levels(db, uid, season, wk.week, first_run, first_long)
    slots = SE.week_slots(season, wk.week, lv.run, lv.ride)
    done = {m.slot_key: m for m in ms if m.slot_key}
    pushes = sum(1 for m in ms if m.level == "push")
    return WeekState(
        wk, lv.run, lv.ride, slots, done, ms, pushes, lv.run_missed, lv.ride_missed, lv.taper_risk
    )


def _day_done(ms: list[Mission]) -> SE.DayDone:
    ms = [m for m in ms if m.kind != "floor"]
    return SE.DayDone(
        kinds=frozenset(m.kind for m in ms),
        hard=any(m.hard for m in ms),
        long_or_tempo_run=any(m.kind == "run" and (m.long or m.tempo) for m in ms),
        long_ride=any(m.kind == "ride" and m.long for m in ms),
    )


PAIN_FLAG = "pain"  # Metric kind: pain reported on a log that wrote no Mission (unplanned)


def pain_recent(db: Db, uid: int, d: date) -> bool:
    """Pain reported in the last 3 days and after the latest "pain cleared" tap.

    Ordered by when things were recorded (created_at), not by the activity date, so pain
    reported after a same-day clear still counts.
    """
    cleared = db.scalar(
        select(Metric.created_at)
        .where(Metric.user_id == uid, Metric.kind == "pain_clear")
        .order_by(Metric.created_at.desc())
    )
    after = lambda ts: cleared is None or ts > cleared
    recent = _missions(db, uid, d - timedelta(days=3), d)
    if any(m.pain and after(m.created_at) for m in recent):
        return True
    flags = db.scalars(
        select(Metric.created_at).where(
            Metric.user_id == uid,
            Metric.kind == PAIN_FLAG,
            Metric.date >= d - timedelta(days=3),
            Metric.date <= d,
        )
    )
    return any(after(ts) for ts in flags)


def _flag_pain(db: Db, uid: int, d: date, pain: str | None) -> None:
    """Pain on a log that wrote no Mission still has to reach pain_recent (safety first)."""
    if pain:
        db.add(Metric(user_id=uid, date=d, kind=PAIN_FLAG, value=1.0, created_at=utcnow()))
        db.flush()


@dataclass
class TodayView:
    state: WeekState
    suggestion: SE.Suggestion
    today_missions: list[Mission]
    streak: SE.DailyStreak
    floor_menu: tuple[dict, ...]
    push: dict
    events: list[dict] = field(default_factory=list)


def today_view(db: Db, uid: int, d: date) -> TodayView | None:
    season = get_season()
    st = week_state(db, uid, d)
    if season is None or st is None:
        return None
    recent = _missions(db, uid, d - timedelta(days=2), d)
    by_day = {
        k: [m for m in recent if m.date == k] for k in (d, d - timedelta(1), d - timedelta(2))
    }
    sug = SE.suggest(
        st.remaining,
        d,
        st.week.week,
        _day_done(by_day[d]),
        _day_done(by_day[d - timedelta(1)]),
        _day_done(by_day[d - timedelta(2)]),
        pain_recent(db, uid, d),
    )
    events = [
        {**e, "days": (date.fromisoformat(e["date"]) - d).days}
        for e in season.events
        if date.fromisoformat(e["date"]) >= d
    ]
    return TodayView(st, sug, by_day[d], streak(db, uid, d), season.floor_menu, season.push, events)


def streak(db: Db, uid: int, d: date) -> SE.DailyStreak:
    ms = _missions(db, uid, date.min, d)
    excused = {
        x.date
        for x in db.scalars(
            select(DayLog).where(DayLog.user_id == uid, DayLog.kind == "smart_rest")
        )
    }
    return SE.daily_streak({m.date for m in ms}, d, excused)


# ---------- gym targets ----------


@dataclass
class ExerciseTarget:
    slot_key: str
    slot_name: str
    options: list[str]
    option: str
    lower: bool
    target: SE.GymTarget


def _exercise_history(
    db: Db, uid: int, exercise: str, limit: int = 3, before: Session | None = None
) -> list[list[SE.SetPerf]]:
    """Newest-first sessions of one exercise; with `before`, only sessions logged before it."""
    rows = db.execute(
        select(SetLog, Session.id, Session.date)
        .join(Session, SetLog.session_id == Session.id)
        .where(Session.user_id == uid, Session.phase == "season", SetLog.exercise == exercise)
        .order_by(Session.date.desc(), Session.id.desc(), SetLog.set_index)
    ).all()
    out: dict[int, list[SE.SetPerf]] = {}
    for s, sid, sdate in rows:
        if before is not None and (sdate, sid) >= (before.date, before.id):
            continue
        done = s.reps if s.reps is not None else s.seconds
        out.setdefault(sid, []).append(
            SE.SetPerf(s.weight_lb, done, s.rpe, s.form_ok, bool(s.pain))
        )
    return list(out.values())[:limit]


def _last_option(db: Db, uid: int, slot_key: str) -> str | None:
    return db.scalar(
        select(SetLog.exercise)
        .join(Session, SetLog.session_id == Session.id)
        .where(Session.user_id == uid, Session.phase == "season", SetLog.category == slot_key)
        .order_by(Session.date.desc(), Session.id.desc())
    )


def hold_range(slot: dict, option: str) -> tuple[int, int] | None:
    """Seconds range if this option is a timed hold (e.g. plank), else None."""
    r = slot.get("holds", {}).get(option)
    return (int(r[0]), int(r[1])) if r else None


def gym_targets(
    db: Db, uid: int, week: SE.Week, template: str, overrides: dict[str, str] | None = None
) -> list[ExerciseTarget]:
    season = get_season()
    assert season is not None
    out = []
    for t in season.gym_templates[template]["slots"]:
        names = {slug(o): o for o in t["options"]}
        picked = (overrides or {}).get(t["key"])
        last = _last_option(db, uid, t["key"])
        option = picked if picked in t["options"] else names.get(last or "", t["options"][0])
        cap = SE.gym_rpe_cap(week.week, t["lower"])
        hold = hold_range(t, option)
        reps = hold or (int(t["reps"][0]), int(t["reps"][1]))
        weight, note = SE.next_gym_weight(
            _exercise_history(db, uid, slug(option)), reps, cap, float(t["inc"]), timed=bool(hold)
        )
        out.append(
            ExerciseTarget(
                slot_key=t["key"],
                slot_name=t["name"],
                options=t["options"],
                option=option,
                lower=t["lower"],
                target=SE.GymTarget(
                    SE.gym_sets(int(t["sets"]), week.week, week.tag, t["lower"]),
                    reps,
                    cap,
                    weight,
                    note,
                    timed=bool(hold),
                ),
            )
        )
    return out


# ---------- logging ----------


def _mission_xp(slot: SE.Slot) -> int:
    return X.KEY_MISSION if (slot.long or slot.tempo) else X.MISSION


def _add_mission(
    db: Db,
    uid: int,
    d: date,
    slot: SE.Slot | None,
    kind: str,
    level: str,
    title: str,
    ref: str,
    pain: str | None,
) -> Mission:
    season = get_season()
    assert season is not None
    week = season.week_for(d)
    m = Mission(
        user_id=uid,
        date=d,
        plan_week=week.week,
        slot_key=slot.key if slot else None,
        kind=kind,
        level=level,
        title=title,
        hard=bool(slot and slot.hard),
        long=bool(slot and slot.long),
        tempo=bool(slot and slot.tempo),
        ref=ref,
        pain=pain or None,
        created_at=utcnow(),
    )
    db.add(m)
    db.flush()
    return m


def _award(db: Db, uid: int, d: date, m: Mission, slot: SE.Slot | None, pushes_before: int) -> int:
    if slot is None:
        others = [x for x in _missions(db, uid, d, d) if x.id != m.id]
        xp = S.add_xp(db, uid, "floor", 0 if others else X.FLOOR, f"mission-{m.id}")
    else:
        xp = S.add_xp(db, uid, "mission", _mission_xp(slot), f"mission-{m.id}")
        if m.level == "push" and pushes_before < X.PUSHES_PER_WEEK:
            xp += S.add_xp(db, uid, "push", X.PUSH, f"mission-{m.id}-push")
    db.flush()
    xp += _sync_weeks_from(db, uid, m.plan_week)  # a backdated log can change later levels
    return xp


def _sync_week_bonus(db: Db, uid: int, week_no: int, d: date) -> int:
    season = get_season()
    assert season is not None
    st = week_state(db, uid, season.week(week_no).start)
    ref = f"week-{week_no}"
    ev = db.scalar(select(XpEvent).where(XpEvent.user_id == uid, XpEvent.ref == ref))
    if st and st.complete and ev is None:
        amount = X.EASY_WEEK_DONE if st.week.tag in EASY_TAGS else X.WEEK_DONE
        return S.add_xp(db, uid, "week_done", amount, ref)
    if st and not st.complete and ev is not None:
        db.delete(ev)
    return 0


def _sync_weeks_from(db: Db, uid: int, week_no: int) -> int:
    """Re-sync week bonuses from `week_no` through the current calendar week.

    Levels for a week come from earlier weeks, so a change in one week can complete or
    un-complete any later week.
    """
    season = get_season()
    assert season is not None
    last = max(week_no, season.week_for(S.today()).week)
    return sum(_sync_week_bonus(db, uid, w, S.today()) for w in range(week_no, last + 1))


def _resync_floor(db: Db, uid: int, d: date) -> None:
    """A floor earns XP only if nothing was logged before it that day (same rule as _award)."""
    ms = sorted(_missions(db, uid, d, d), key=lambda m: m.id)
    for i, m in enumerate(ms):
        if m.kind == "floor":
            S._sync_xp_event(db, uid, "floor", f"mission-{m.id}", 0 if i else X.FLOOR)


def _resync_pushes(db: Db, uid: int, week_no: int) -> None:
    """The first PUSHES_PER_WEEK push missions of a week earn the push bonus, in log order."""
    pushes = db.scalars(
        select(Mission)
        .where(Mission.user_id == uid, Mission.plan_week == week_no, Mission.level == "push")
        .order_by(Mission.id)
    )
    for i, m in enumerate(pushes):
        amount = X.PUSH if i < X.PUSHES_PER_WEEK else 0
        S._sync_xp_event(db, uid, "push", f"mission-{m.id}-push", amount)


def _resync(db: Db, uid: int, days: set[date], weeks: set[int]) -> None:
    """Recompute day- and week-level XP after a mission was removed or moved."""
    db.flush()
    for d in days:
        _resync_floor(db, uid, d)
    for w in weeks:
        _resync_pushes(db, uid, w)
    db.flush()
    _sync_weeks_from(db, uid, min(weeks))


def _slot(db: Db, uid: int, d: date, slot_key: str | None) -> tuple[SE.Slot | None, int]:
    st = week_state(db, uid, d)
    if st is None or slot_key is None:
        return None, st.pushes_used if st else 0
    slot = next((s for s in st.slots if s.key == slot_key), None)
    if slot is None or slot_key in st.done:
        return None, st.pushes_used
    return slot, st.pushes_used


def log_floor(db: Db, uid: int, d: date, option: str) -> int:
    season = get_season()
    assert season is not None
    item = next((f for f in season.floor_menu if f["key"] == option), None)
    if item is None:
        raise ValueError(f"unknown floor option {option!r}")
    x = DayLog(user_id=uid, date=d, kind="floor", note=item["name"], created_at=utcnow())
    db.add(x)
    db.flush()
    m = _add_mission(db, uid, d, None, "floor", "floor", item["name"], f"day-{x.id}", None)
    xp = _award(db, uid, d, m, None, 0)
    db.commit()
    return xp


def log_cardio(
    db: Db,
    uid: int,
    d: date,
    sport: str,
    slot_key: str | None,
    minutes: int,
    miles: float | None,
    zone: int,
    push: bool,
    pain: str | None,
    note: str,
) -> int:
    """A run or ride. Tied to a plan slot it earns mission XP; unplanned, it's just logged."""
    slot, pushes = _slot(db, uid, d, slot_key)
    if slot is not None and slot.kind != sport:
        slot = None
    r = Ride(
        user_id=uid,
        date=d,
        sport=sport,
        miles=miles or 0.0,
        minutes=minutes,
        zone=zone,
        commute=None,
        note=note,
        created_at=utcnow(),
    )
    db.add(r)
    db.flush()
    xp = 0
    if slot is not None:
        level = "push" if push and slot.push else "standard"
        m = _add_mission(db, uid, d, slot, sport, level, slot.title, f"ride-{r.id}", pain)
        xp = _award(db, uid, d, m, slot, pushes)
    else:
        _flag_pain(db, uid, d, pain)
    db.commit()
    return xp


@dataclass
class LoggedExercise:
    slot_key: str
    option: str
    rpe_cap: float
    sets: list[tuple[float | None, int | None, float | None]]  # weight, reps (or seconds), rpe
    form_ok: bool = True
    timed: bool = False  # the reps column holds seconds


def _rep_range(m: Mission, exercise_slot: str) -> tuple[int, int] | None:
    """The engine's rep range for one exercise slot of the gym template a mission used."""
    season = get_season()
    plan_slot = season.week(m.plan_week).slot(m.slot_key or "") if season else None
    if plan_slot is None or plan_slot.template is None:
        return None
    tpl = season.gym_templates.get(plan_slot.template, {})
    t = next((t for t in tpl.get("slots", []) if t["key"] == exercise_slot), None)
    return (int(t["reps"][0]), int(t["reps"][1])) if t else None


def _plan_entry(m: Mission, exercise_slot: str) -> tuple[SE.Week, dict] | None:
    """The plan week and gym-template slot entry a mission's exercise came from."""
    season = get_season()
    plan_slot = season.week(m.plan_week).slot(m.slot_key or "") if season else None
    if plan_slot is None or plan_slot.template is None:
        return None
    tpl = season.gym_templates.get(plan_slot.template, {})
    t = next((t for t in tpl.get("slots", []) if t["key"] == exercise_slot), None)
    return (season.week(m.plan_week), t) if t else None


def _did_the_prescription(
    db: Db, uid: int, sess: Session, m: Mission, exercise: str, sets: list[SetLog], cap: float
) -> bool:
    """XP guard only (the load rule is untouched): the increase counts when the athlete
    did the planned number of sets at or above the engine's target weight. Lifting under
    the target or dropping sets must not farm the reward."""
    entry = _plan_entry(m, sets[0].category or "")
    if entry is None:
        return False
    week, t = entry
    planned = SE.gym_sets(int(t["sets"]), week.week, week.tag, t["lower"])
    if sum(1 for s in sets if s.reps is not None) < planned:
        return False
    reps = (int(t["reps"][0]), int(t["reps"][1]))
    prior = _exercise_history(db, uid, exercise, before=sess)
    target, _ = SE.next_gym_weight(prior, reps, cap, float(t["inc"]))
    if target is None:  # first time or bodyweight: nothing to compare against
        return True
    done = max((s.weight_lb for s in sets if s.reps is not None and s.weight_lb), default=None)
    return done is not None and done >= target


def sync_weight_increases(db: Db, uid: int, sess: Session) -> list[str]:
    """Award or remove `weight_increase` XP for each exercise of a season session.

    One award per session per exercise (ref `inc-{session}-{exercise}`), and only for a
    planned session (one with a mission). The test is the engine's own double-progression
    rule, so the XP appears exactly when the next target weight goes up. Re-run after any
    edit; returns the exercises that earned it.
    """
    m = mission_for(db, uid, f"session-{sess.id}")
    by_ex: dict[str, list[SetLog]] = {}
    for s in sorted(sess.sets, key=lambda s: s.set_index):
        by_ex.setdefault(s.exercise, []).append(s)
    earned = []
    for exercise, sets in by_ex.items():
        reps = _rep_range(m, sets[0].category or "") if m is not None else None
        caps = [s.rpe_cap for s in sets if s.rpe_cap is not None]
        ok = (
            reps is not None
            and bool(caps)  # unknown cap: never reward
            and SE.earned_increase(
                [SE.SetPerf(s.weight_lb, s.reps, s.rpe, s.form_ok) for s in sets],
                reps,
                min(caps),
                pain=bool(m.pain or any(s.pain for s in sets)),
            )
            and _did_the_prescription(db, uid, sess, m, exercise, sets, min(caps))
        )
        ref = f"inc-{sess.id}-{exercise}"
        S._sync_xp_event(db, uid, S.WEIGHT_INCREASE_SOURCE, ref, X.WEIGHT_INCREASE if ok else 0)
        if ok:
            earned.append(exercise)
    return earned


def latest_session_id(db: Db, uid: int) -> int | None:
    return db.scalar(select(func.max(Session.id)).where(Session.user_id == uid))


def weight_increases(db: Db, uid: int, session_id: int) -> list[str]:
    """Exercises (slugs) of a session that earned weight-increase XP."""
    prefix = f"inc-{session_id}-"
    refs = db.scalars(
        select(XpEvent.ref).where(
            XpEvent.user_id == uid,
            XpEvent.source == S.WEIGHT_INCREASE_SOURCE,
            XpEvent.ref.startswith(prefix, autoescape=True),
        )
    )
    return [r.removeprefix(prefix) for r in refs]


def log_gym(
    db: Db,
    uid: int,
    d: date,
    slot_key: str,
    exercises: list[LoggedExercise],
    push: bool,
    pain: str | None,
    note: str,
) -> int:
    slot, pushes = _slot(db, uid, d, slot_key)
    season = get_season()
    assert season is not None
    week = season.week_for(d)
    sess = Session(
        user_id=uid,
        date=d,
        phase="season",
        week=str(week.week),
        day=0,
        heavy=bool(slot and slot.template == "A"),
        status="done",
        note=note,
        started_at=utcnow(),
        finished_at=utcnow(),
    )
    db.add(sess)
    db.flush()
    xp = 0
    for ex in exercises:
        for i, (w, reps, rpe) in enumerate(ex.sets, 1):
            if reps is None:
                continue
            s = SetLog(
                session_id=sess.id,
                exercise=slug(ex.option),
                category=ex.slot_key,
                set_index=i,
                rpe_cap=ex.rpe_cap,
                weight_lb=None if ex.timed else w,
                reps=None if ex.timed else reps,
                seconds=reps if ex.timed else None,
                rpe=rpe,
                form_ok=ex.form_ok,
                pain=pain,
            )
            # Unplanned (repeated or unknown slot) volume is logged but earns nothing.
            s.xp = X.set_xp(rpe, ex.form_ok, ex.rpe_cap) if slot is not None else 0
            db.add(s)
            db.flush()
            xp += S.add_xp(db, uid, "set", s.xp, f"set-{s.id}")
    if slot is not None:
        level = "push" if push and slot.push else "standard"
        m = _add_mission(db, uid, d, slot, "gym", level, slot.title, f"session-{sess.id}", pain)
        xp += _award(db, uid, d, m, slot, pushes)
        db.flush()
        db.refresh(sess)
        xp += X.WEIGHT_INCREASE * len(sync_weight_increases(db, uid, sess))
    else:
        _flag_pain(db, uid, d, pain)
    db.commit()
    S.award_badges(db, uid)
    return xp


def drop_missions_for(db: Db, uid: int, ref: str) -> int:
    """Called when a session, ride, or day log is deleted: remove its mission and XP."""
    xp = 0
    days: set[date] = set()
    weeks: set[int] = set()
    for m in list(db.scalars(select(Mission).where(Mission.user_id == uid, Mission.ref == ref))):
        xp += S._remove_xp_events(db, uid, [f"mission-{m.id}", f"mission-{m.id}-push"])
        days.add(m.date)
        weeks.add(m.plan_week)
        db.delete(m)
    if weeks and get_season() is not None:
        _resync(db, uid, days, weeks)
    return xp


def mission_for(db: Db, uid: int, ref: str) -> Mission | None:
    return db.scalar(select(Mission).where(Mission.user_id == uid, Mission.ref == ref))


def move_mission(db: Db, uid: int, ref: str, d: date) -> bool:
    """An edited activity date moves its mission (and plan week). False if there is none."""
    m = mission_for(db, uid, ref)
    if m is None:
        return False
    season = get_season()
    if m.date == d or season is None:
        return True
    days, weeks = {m.date, d}, {m.plan_week}
    m.date, m.plan_week = d, season.week_for(d).week
    weeks.add(m.plan_week)
    _resync(db, uid, days, weeks)
    return True


def history_label(db: Db, uid: int, ref: str) -> str | None:
    m = mission_for(db, uid, ref)
    if m is None:
        return None
    lvl = {"push": " · push", "floor": " · floor"}.get(m.level, "")
    return f"{m.title}{lvl}" + (f" (pain: {m.pain})" if m.pain else "")


# ---------- week recap ----------


@dataclass
class RecapDay:
    date: date
    missions: list[Mission]


@dataclass
class WeekRecap:
    """What one plan week earned and what it unlocked (D35–D37)."""

    state: WeekState
    status: str  # past | current | future
    slots_done: int
    slots_total: int
    runs_done: int
    runs_needed: int
    long_ride_done: bool
    floors: int
    pushes_used: int
    forgiven: bool
    xp: int
    days: list[RecapDay]
    run_line: str | None  # None for future weeks: nothing unlocked yet
    ride_line: str | None
    has_prev: bool
    has_next: bool

    @property
    def week(self) -> SE.Week:
        return self.state.week

    @property
    def counts_as_done(self) -> bool:
        return self.forgiven or self.state.complete


def _week_xp(db: Db, uid: int, wk: SE.Week) -> int:
    """XP recorded during the week's local calendar days (XpEvent.ts is naive UTC)."""
    tz = ZoneInfo(get_settings().timezone)

    def utc(d: date) -> datetime:
        return datetime.combine(d, time.min, tz).astimezone(UTC).replace(tzinfo=None)

    total = db.scalar(
        select(func.coalesce(func.sum(XpEvent.amount), 0)).where(
            XpEvent.user_id == uid,
            XpEvent.ts >= utc(wk.start),
            XpEvent.ts < utc(wk.end + timedelta(days=1)),
        )
    )
    return int(total or 0)


def week_recap(db: Db, uid: int, week_no: int) -> WeekRecap | None:
    """None when there is no season or `week_no` is outside it."""
    season = get_season()
    if season is None or all(w.week != week_no for w in season.weeks):
        return None
    wk = season.week(week_no)
    st = week_state(db, uid, wk.start)
    assert st is not None
    today = S.today()
    status = "future" if wk.start > today else "past" if wk.end < today else "current"
    ms = st.missions
    runs = sum(1 for m in ms if m.kind == "run")
    long_ride = any(m.kind == "ride" and m.long for m in ms)
    forgiven = week_no in forgiven_weeks(db, uid)
    run_line = ride_line = None
    if status != "future":
        nxt = _levels(db, uid, season, week_no + 1)
        run_line = RC.run_unlock(week_no, st.run_level, nxt.run, runs, forgiven)
        ride_line = RC.ride_unlock(week_no, st.ride_level, nxt.ride, long_ride, forgiven)
    days = [
        RecapDay(d, [m for m in ms if m.date == d])
        for d in (wk.start + timedelta(days=i) for i in range(7))
    ]
    numbers = [w.week for w in season.weeks]
    return WeekRecap(
        state=st,
        status=status,
        slots_done=sum(1 for s in st.slots if s.key in st.done),
        slots_total=len(st.slots),
        runs_done=runs,
        runs_needed=SE.MIN_RUNS_TO_ADVANCE,
        long_ride_done=long_ride,
        floors=sum(1 for m in ms if m.kind == "floor"),
        pushes_used=st.pushes_used,
        forgiven=forgiven,
        xp=_week_xp(db, uid, wk),
        days=days,
        run_line=run_line,
        ride_line=ride_line,
        has_prev=week_no - 1 in numbers,
        has_next=week_no + 1 in numbers,
    )


def last_week_recap(db: Db, uid: int, d: date) -> WeekRecap | None:
    """The previous week's recap for Today's card, shown Monday–Wednesday only."""
    season = get_season()
    if season is None or d.weekday() not in RC.RECAP_DAYS:
        return None
    return week_recap(db, uid, season.week_for(d).week - 1)
