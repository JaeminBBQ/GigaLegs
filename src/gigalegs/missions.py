"""Season v2 glue (D27–D32): missions, the week's checklist, gym targets, daily streak.

Every rule and number comes from engine/season.py and engine/xp.py; this module only
reads and writes the database.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session as Db

from . import services as S
from .config import get_settings
from .db import utcnow
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


def _levels(db: Db, uid: int, season: SE.Season, cal: int) -> tuple[int, int]:
    """Run and long-ride levels from what was actually done in earlier weeks."""
    ms = [m for m in _missions(db, uid, season.week(1).start, date.max) if m.plan_week < cal]
    run_weeks: dict[int, int] = {}
    ride_weeks: set[int] = set()
    for m in ms:
        if m.kind == "run":
            run_weeks[m.plan_week] = run_weeks.get(m.plan_week, 0) + 1
        if m.kind == "ride" and m.long:
            ride_weeks.add(m.plan_week)
    done_runs = {w for w, n in run_weeks.items() if n >= SE.MIN_RUNS_TO_ADVANCE}
    return (
        SE.effective_level(cal, done_runs, SE.LAG_RUN_UNTIL),
        SE.effective_level(cal, ride_weeks, SE.LAG_RIDE_UNTIL),
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
    run_level, ride_level = _levels(db, uid, season, wk.week)
    slots = SE.week_slots(season, wk.week, run_level, ride_level)
    ms = [m for m in _missions(db, uid, wk.start, wk.end) if m.plan_week == wk.week]
    done = {m.slot_key: m for m in ms if m.slot_key}
    pushes = sum(1 for m in ms if m.level == "push")
    return WeekState(wk, run_level, ride_level, slots, done, ms, pushes)


def _day_done(ms: list[Mission]) -> SE.DayDone:
    ms = [m for m in ms if m.kind != "floor"]
    return SE.DayDone(
        kinds=frozenset(m.kind for m in ms),
        hard=any(m.hard for m in ms),
        long_or_tempo_run=any(m.kind == "run" and (m.long or m.tempo) for m in ms),
        long_ride=any(m.kind == "ride" and m.long for m in ms),
    )


def pain_recent(db: Db, uid: int, d: date) -> bool:
    cleared = db.scalar(
        select(Metric.date)
        .where(Metric.user_id == uid, Metric.kind == "pain_clear")
        .order_by(Metric.date.desc())
    )
    recent = _missions(db, uid, d - timedelta(days=3), d)
    return any(m.pain and (cleared is None or m.date > cleared) for m in recent)


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


def _exercise_history(db: Db, uid: int, exercise: str, limit: int = 3) -> list[list[SE.SetPerf]]:
    rows = db.execute(
        select(SetLog, Session.id)
        .join(Session, SetLog.session_id == Session.id)
        .where(Session.user_id == uid, Session.phase == "season", SetLog.exercise == exercise)
        .order_by(Session.date.desc(), Session.id.desc(), SetLog.set_index)
    ).all()
    out: dict[int, list[SE.SetPerf]] = {}
    for s, sid in rows:
        out.setdefault(sid, []).append(SE.SetPerf(s.weight_lb, s.reps, s.rpe, s.form_ok))
    return list(out.values())[:limit]


def _last_option(db: Db, uid: int, slot_key: str) -> str | None:
    return db.scalar(
        select(SetLog.exercise)
        .join(Session, SetLog.session_id == Session.id)
        .where(Session.user_id == uid, Session.phase == "season", SetLog.category == slot_key)
        .order_by(Session.date.desc(), Session.id.desc())
    )


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
        reps = (int(t["reps"][0]), int(t["reps"][1]))
        weight, note = SE.next_gym_weight(
            _exercise_history(db, uid, slug(option)), reps, cap, float(t["inc"])
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
    xp += _sync_week_bonus(db, uid, m.plan_week, d)
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
    db.commit()
    return xp


@dataclass
class LoggedExercise:
    slot_key: str
    option: str
    rpe_cap: float
    sets: list[tuple[float | None, int | None, float | None]]  # weight, reps, rpe
    form_ok: bool = True


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
                weight_lb=w,
                reps=reps,
                rpe=rpe,
                form_ok=ex.form_ok,
                pain=pain,
            )
            s.xp = X.set_xp(rpe, ex.form_ok, ex.rpe_cap)
            db.add(s)
            db.flush()
            xp += S.add_xp(db, uid, "set", s.xp, f"set-{s.id}")
    if slot is not None:
        level = "push" if push and slot.push else "standard"
        m = _add_mission(db, uid, d, slot, "gym", level, slot.title, f"session-{sess.id}", pain)
        xp += _award(db, uid, d, m, slot, pushes)
    db.commit()
    return xp


def drop_missions_for(db: Db, uid: int, ref: str) -> int:
    """Called when a session, ride, or day log is deleted: remove its mission and XP."""
    xp = 0
    for m in list(db.scalars(select(Mission).where(Mission.user_id == uid, Mission.ref == ref))):
        xp += S._remove_xp_events(db, uid, [f"mission-{m.id}", f"mission-{m.id}-push"])
        week_no, d = m.plan_week, m.date
        db.delete(m)
        db.flush()
        if get_season() is not None:
            _sync_week_bonus(db, uid, week_no, d)
    return xp


def history_label(db: Db, uid: int, ref: str) -> str | None:
    m = db.scalar(select(Mission).where(Mission.user_id == uid, Mission.ref == ref))
    if m is None:
        return None
    lvl = {"push": " · push", "floor": " · floor"}.get(m.level, "")
    return f"{m.title}{lvl}" + (f" (pain: {m.pain})" if m.pain else "")
