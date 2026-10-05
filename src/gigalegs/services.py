"""Glue between the pure engine and the database. Every number comes from engine/ (D2)."""

import json
from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session as Db

from . import engine as E
from .config import get_settings
from .db import LOCAL_USER_ID, utcnow
from .engine import xp as X
from .engine.program import HEAVY_CATEGORIES
from .engine.shorthand import ParseResult
from .models import DayLog, Metric, PhaseState, Ride, Session, SetLog, User, XpEvent

SQUAT_KEYS = ("high_bar_paused_squat", "back_squat")
DEADLIFT_KEYS = ("deadlift", "deficit_deadlift")


# ---------- basics ----------


def today() -> date:
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


@lru_cache
def _load_program_file(path: str, mtime: float) -> E.Program:
    return E.load_program(json.loads(Path(path).read_text()))


def get_program() -> E.Program | None:
    p = get_settings().program_path
    if not p.exists():
        return None
    return _load_program_file(str(p), p.stat().st_mtime)


def ensure_user(db: Db, uid: int = LOCAL_USER_ID) -> PhaseState:
    if db.get(User, uid) is None:
        db.add(User(id=uid, display_name="Athlete", created_at=utcnow()))
        db.flush()
    st = db.get(PhaseState, uid)
    if st is None:
        st = PhaseState(
            user_id=uid,
            phase="onramp",
            week="A",
            day=1,
            gate_pending=False,
            bike_stage=get_settings().bike_stage,
            updated_at=utcnow(),
        )
        db.add(st)
        db.commit()
    return st


def add_xp(db: Db, uid: int, source: str, amount: int, ref: str = "", detail=None) -> int:
    if amount:
        db.add(
            XpEvent(user_id=uid, ts=utcnow(), source=source, amount=amount, ref=ref, detail=detail)
        )
    return amount


@dataclass
class LevelInfo:
    total: int
    level: int
    title: str
    into_level: int
    level_span: int

    @property
    def pct(self) -> int:
        return round(100 * self.into_level / self.level_span) if self.level_span else 0


def level_info(db: Db, uid: int = LOCAL_USER_ID) -> LevelInfo:
    total = (
        db.scalar(select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.user_id == uid))
        or 0
    )
    lvl = X.level(total)
    floor, ceil = X.level_floor(lvl), X.level_floor(lvl + 1)
    return LevelInfo(total, lvl, X.level_title(lvl), total - floor, ceil - floor)


# ---------- prescriptions ----------


def position(st: PhaseState) -> E.Position:
    return E.Position(st.phase, st.week, st.day)


def _exposure_decisions(
    db: Db, uid: int, key: str, day: int
) -> tuple[float | None, E.Decision | None]:
    """Replay every finished program-phase exposure of (exercise, day) through decide()."""
    rows = db.execute(
        select(Session.id, SetLog)
        .join(SetLog, SetLog.session_id == Session.id)
        .where(
            Session.user_id == uid,
            Session.status == "done",
            Session.phase == "program",
            Session.day == day,
            SetLog.exercise == key,
            SetLog.reps.is_not(None),
        )
        .order_by(Session.started_at, SetLog.id)
    ).all()
    by_session: dict[int, list[SetLog]] = defaultdict(list)
    for sid, s in rows:
        by_session[sid].append(s)
    misses = 0
    last_lb = None
    decision = None
    for sets in by_session.values():
        results = [
            E.SetResult(s.prescribed_reps or s.reps or 0, s.reps or 0, s.rpe_cap, s.rpe, s.form_ok)
            for s in sets
        ]
        decision, misses = E.decide(results, misses)
        last_lb = max((s.weight_lb or 0) for s in sets) or None
    return last_lb, decision


def plan_for(
    db: Db, uid: int, pos: E.Position, readiness: E.Adjustment | None = None
) -> E.DayPlan | None:
    program = get_program()
    if program is None:
        return None
    plan = E.day_plan(program, pos)
    out = []
    for ex in plan.exercises:
        if pos.phase == "program" and ex.kind == "weight" and ex.weight_lb is not None:
            last_lb, decision = _exposure_decisions(db, uid, ex.key, pos.day)
            ex = replace(ex, weight_lb=E.adjust_program_weight(ex.weight_lb, last_lb, decision))
        if readiness is not None and ex.kind in ("weight", "rpe"):
            p = E.apply_adjustment(
                E.Prescription(ex.sets, ex.reps, ex.weight_lb, ex.rpe_cap), readiness
            )
            ex = replace(ex, weight_lb=p.weight_lb, rpe_cap=p.rpe_cap)
        out.append(ex)
    return E.DayPlan(pos, out)


def plates(weight_lb: float | None) -> str:
    if weight_lb is None:
        return ""
    try:
        side = E.plates_per_side(weight_lb)
    except ValueError:
        return ""
    if not side:
        return "empty bar"
    return " + ".join(f"{p:g}" for p in side) + " / side"


# ---------- daily recommendation ----------


def _finished_sessions(db: Db, uid: int, since: datetime) -> list[Session]:
    return list(
        db.scalars(
            select(Session)
            .where(Session.user_id == uid, Session.status == "done", Session.finished_at >= since)
            .order_by(Session.finished_at)
        )
    )


def active_dates(db: Db, uid: int, start: date, end: date) -> dict[date, set[str]]:
    out: dict[date, set[str]] = defaultdict(set)
    for d, heavy in db.execute(
        select(Session.date, Session.heavy).where(
            Session.user_id == uid, Session.status == "done", Session.date.between(start, end)
        )
    ):
        out[d].add("heavy" if heavy else "lift")
    for d, minutes, zone in db.execute(
        select(Ride.date, Ride.minutes, Ride.zone).where(
            Ride.user_id == uid, Ride.date.between(start, end)
        )
    ):
        out[d].add("long_ride" if minutes > 60 or zone >= 3 else "ride")
    for d, kind in db.execute(
        select(DayLog.date, DayLog.kind).where(
            DayLog.user_id == uid, DayLog.date.between(start, end)
        )
    ):
        out[d].add("recovery" if kind == "recovery" else "rest")
    return out


def morning(db: Db, uid: int, d: date) -> dict[str, float]:
    rows = db.execute(
        select(Metric.kind, Metric.value)
        .where(Metric.user_id == uid, Metric.date == d)
        .order_by(Metric.id)
    ).all()
    return {k: v for k, v in rows}


def day_context(db: Db, uid: int, d: date, now: datetime | None = None) -> E.DayContext:
    now = now or utcnow()
    st = ensure_user(db, uid)
    plan = plan_for(db, uid, position(st))
    week_ago = now - timedelta(days=7)
    recent = _finished_sessions(db, uid, now - timedelta(days=14))
    lifts = [s for s in recent if s.finished_at]
    heavy = [s for s in lifts if s.heavy]
    hours = lambda s: (now - s.finished_at).total_seconds() / 3600
    acts = active_dates(db, uid, d - timedelta(days=14), d)
    streak = 0
    probe = d - timedelta(days=1)
    while acts.get(probe):
        streak += 1
        probe -= timedelta(days=1)
    easy = any(
        acts.get(d - timedelta(days=i), set()) & {"recovery", "rest"}
        or (i > 0 and not acts.get(d - timedelta(days=i)))
        for i in range(7)
    )
    yesterday = acts.get(d - timedelta(days=1), set())
    cleared = db.scalar(
        select(func.max(Metric.created_at)).where(
            Metric.user_id == uid, Metric.kind == "pain_clear"
        )
    )
    pain = (
        db.scalar(
            select(func.count(SetLog.id))
            .join(Session)
            .where(
                Session.user_id == uid,
                SetLog.pain.is_not(None),
                Session.date >= d - timedelta(days=3),
                Session.started_at > cleared if cleared else true(),
            )
        )
        or 0
    )
    m = morning(db, uid, d)
    return E.DayContext(
        next_day_heavy=bool(plan and plan.heavy),
        hours_since_heavy=hours(heavy[-1]) if heavy else None,
        hours_since_lift=hours(lifts[-1]) if lifts else None,
        program_sessions_7d=sum(1 for s in lifts if s.finished_at >= week_ago),
        easy_day_in_last_7d=easy,
        active_streak=streak,
        yesterday_hard=bool(yesterday & {"heavy", "long_ride"}),
        open_pain=pain > 0,
        soreness=int(m["soreness"]) if "soreness" in m else None,
        bike_stage=st.bike_stage,
        already_lifted_today=any(s.date == d for s in lifts),
    )


# ---------- sessions ----------


def open_session(db: Db, uid: int) -> Session | None:
    return db.scalar(
        select(Session)
        .where(Session.user_id == uid, Session.status == "open")
        .order_by(Session.id.desc())
    )


def _week_sessions(db: Db, uid: int, st: PhaseState) -> list[Session]:
    return list(
        db.scalars(
            select(Session).where(
                Session.user_id == uid,
                Session.status == "done",
                Session.phase == st.phase,
                Session.week == st.week,
            )
        )
    )


def resolve_gate(db: Db, uid: int, soreness: int) -> str | None:
    """On-ramp gate (ONRAMP.md): evaluated at the first lift after a week's Day 3."""
    st = ensure_user(db, uid)
    if not st.gate_pending:
        return None
    sets = [s for sess in _week_sessions(db, uid, st) for s in sess.sets]
    pain = any(s.pain for s in sets)
    ok = all(
        s.form_ok
        and (s.rpe_cap is None or s.rpe is None or s.rpe <= s.rpe_cap)
        and (s.prescribed_reps is None or s.reps is None or s.reps >= s.prescribed_reps)
        for s in sets
    )
    advance = E.can_advance_onramp(soreness, pain, ok)
    old = st.week
    nxt = E.next_phase_step(st.week, advance)
    if nxt == "program":
        st.phase, st.week = "program", "1"
    else:
        st.week = nxt
    st.day, st.gate_pending, st.updated_at = 1, False, utcnow()
    if advance:
        return f"On-ramp week {old} passed → now {st.phase} week {st.week}."
    add_xp(db, uid, "gated_repeat", X.GATED_ADJUSTMENT, f"onramp-{old}")
    reasons = []
    if soreness > 5:
        reasons.append(f"soreness {soreness}/10")
    if pain:
        reasons.append("pain was flagged")
    if not ok:
        reasons.append("some sets were over the cap, short on reps, or had form flags")
    return f"Repeating on-ramp week {old} ({', '.join(reasons)}). Smart call: +{X.GATED_ADJUSTMENT} XP."


def start_session(
    db: Db, uid: int, d: date, soreness: int, sleep: int, energy: int
) -> tuple[Session, str | None]:
    gate_msg = resolve_gate(db, uid, soreness)
    st = ensure_user(db, uid)
    prev = db.scalar(
        select(Session.soreness)
        .where(Session.user_id == uid, Session.status == "done")
        .order_by(Session.id.desc())
    )
    adj = E.readiness_adjust(soreness, sleep, energy, prev)
    plan = plan_for(db, uid, position(st), adj)
    if plan is None:
        raise RuntimeError("program file missing")
    sess = Session(
        user_id=uid,
        date=d,
        phase=st.phase,
        week=st.week,
        day=st.day,
        heavy=plan.heavy,
        soreness=soreness,
        sleep=sleep,
        energy=energy,
        status="open",
        started_at=utcnow(),
    )
    for ex in plan.exercises:
        if ex.kind == "off":
            continue
        for i in range(ex.sets):
            sess.sets.append(
                SetLog(
                    exercise=ex.key,
                    category=ex.category,
                    set_index=i + 1,
                    prescribed_weight_lb=ex.weight_lb,
                    prescribed_reps=None if ex.kind in ("hold", "test") else ex.reps,
                    rpe_cap=ex.rpe_cap,
                    rpe_min=ex.rpe_range[0] if ex.rpe_range else None,
                    rpe_max=ex.rpe_range[1] if ex.rpe_range else None,
                )
            )
    db.add(sess)
    add_xp(db, uid, "readiness_checkin", X.READINESS_CHECKIN, "session")
    notes = [m for m in (gate_msg,) if m]
    if adj.load_factor < 1:
        notes.append("Soreness ≥ 7: loads are 10% lighter and the RPE cap is 1 lower today.")
    if adj.flag_repeat_week:
        notes.append("Soreness was high last session too. Consider repeating this week.")
    db.commit()
    return sess, " ".join(notes) or None


def log_set(
    db: Db,
    s: SetLog,
    weight: float | None,
    reps: int | None,
    seconds: int | None,
    rpe: float | None,
    form_ok: bool,
    pain: str | None,
) -> int:
    s.weight_lb, s.reps, s.seconds, s.rpe = weight, reps, seconds, rpe
    s.form_ok, s.pain = form_ok, (pain or None)
    s.xp = _set_xp(s)
    db.commit()
    return s.xp


def _set_xp(s: SetLog) -> int:
    if s.seconds is not None and s.rpe is None:
        return X.SET_LOGGED if s.form_ok else 0
    rng = (s.rpe_min, s.rpe_max) if s.rpe_min is not None and s.rpe_max is not None else None
    return X.set_xp(s.rpe, s.form_ok, s.rpe_cap, rng)


@dataclass
class ExerciseSummary:
    key: str
    sets: list[SetLog]
    decision: E.Decision | None = None


@dataclass
class SessionSummary:
    session: Session
    exercises: list[ExerciseSummary] = field(default_factory=list)
    xp: int = 0
    messages: list[str] = field(default_factory=list)


def summarize(sess: Session) -> list[ExerciseSummary]:
    groups: dict[str, list[SetLog]] = {}
    for s in sess.sets:
        groups.setdefault(s.exercise, []).append(s)
    out = []
    for key, sets in groups.items():
        done = [s for s in sets if s.reps is not None]
        decision = None
        if done and any(s.prescribed_reps for s in done):
            decision, _ = E.decide(
                [
                    E.SetResult(
                        s.prescribed_reps or s.reps or 0, s.reps or 0, s.rpe_cap, s.rpe, s.form_ok
                    )
                    for s in done
                ],
                0,
            )
        out.append(ExerciseSummary(key, sets, decision))
    return out


def finish_session(db: Db, uid: int, sess: Session) -> SessionSummary:
    st = ensure_user(db, uid)
    logged = [s for s in sess.sets if s.reps is not None or s.seconds is not None]
    plan = plan_for(db, uid, E.Position(sess.phase, sess.week, sess.day))
    counts: dict[str, int] = defaultdict(int)
    for s in logged:
        counts[s.exercise] += 1
    # "As prescribed" = every planned exercise has its planned number of sets logged.
    all_logged = bool(logged) and (
        all(counts[e.key] >= e.sets for e in plan.exercises if e.kind != "off")
        if plan and plan.exercises
        else len(logged) == len(sess.sets)
    )
    within = all(s.rpe_cap is None or s.rpe is None or s.rpe <= s.rpe_cap for s in logged)
    xp = sum(s.xp for s in logged)
    for s in logged:
        add_xp(db, uid, "set", s.xp, f"set-{s.id}")
    xp += add_xp(db, uid, "session", X.session_xp(all_logged, within), f"session-{sess.id}")
    msgs = []
    # e1RM PRs on the main lifts
    for keys, label in ((SQUAT_KEYS, "squat"), (DEADLIFT_KEYS, "deadlift")):
        best_now = max(
            (
                v
                for s in logged
                if s.exercise in keys
                and s.weight_lb
                and s.reps
                and s.rpe
                and s.form_ok
                and (v := E.e1rm(s.weight_lb, s.reps, s.rpe))
            ),
            default=None,
        )
        if best_now:
            prev = best_e1rm(db, uid, keys, exclude_session=sess.id)
            if prev is not None and best_now > prev:
                xp += add_xp(db, uid, "e1rm_pr", X.E1RM_PR, f"session-{sess.id}")
                msgs.append(
                    f"New {label} e1RM: {best_now:.0f} lb (was {prev:.0f}). +{X.E1RM_PR} XP"
                )
    sess.status, sess.finished_at = "done", utcnow()
    if (sess.phase, sess.week, sess.day) == (st.phase, st.week, st.day):
        program = get_program()
        if program and sess.day >= program.days_per_week:
            if st.phase == "onramp":
                st.gate_pending, st.day = True, 1
                msgs.append(
                    "On-ramp week done. Your next lift checks the gate: soreness ≤ 5, "
                    "no pain, all sets clean → next week."
                )
            else:
                nxt = E.next_position(program, position(st))
                st.phase, st.week, st.day = nxt.phase, nxt.week, nxt.day
                msgs.append(f"Week complete → {st.phase} week {st.week}.")
        elif program:
            st.day += 1
        st.updated_at = utcnow()
    if not all_logged:
        msgs.append(
            "Some sets weren't logged, so no session bonus. That's fine if you cut it short on purpose."
        )
    db.commit()
    return SessionSummary(sess, summarize(sess), xp, msgs)


def best_e1rm(
    db: Db, uid: int, keys: tuple[str, ...], exclude_session: int | None = None
) -> float | None:
    q = (
        select(SetLog)
        .join(Session)
        .where(
            Session.user_id == uid,
            SetLog.exercise.in_(keys),
            SetLog.weight_lb.is_not(None),
            SetLog.reps.is_not(None),
            SetLog.rpe.is_not(None),
            SetLog.form_ok.is_(True),
        )
    )
    if exclude_session is not None:
        q = q.where(Session.id != exclude_session)
    vals = [v for s in db.scalars(q) if (v := E.e1rm(s.weight_lb, s.reps, s.rpe))]
    return max(vals) if vals else None


# ---------- rides, recovery, metrics ----------


def log_ride(
    db: Db,
    uid: int,
    d: date,
    miles: float,
    minutes: int,
    zone: int,
    commute: str | None,
    elevation_ft: int | None,
    note: str,
) -> int:
    r = Ride(
        user_id=uid,
        date=d,
        miles=miles,
        minutes=minutes,
        zone=zone,
        commute=commute,
        elevation_ft=elevation_ft,
        note=note,
        created_at=utcnow(),
    )
    db.add(r)
    db.flush()
    xp = add_xp(db, uid, "ride", E.ride_xp(miles, commute is not None, zone), f"ride-{r.id}")
    db.commit()
    return xp


def log_day(db: Db, uid: int, d: date, kind: str, minutes: int | None, note: str) -> int:
    db.add(DayLog(user_id=uid, date=d, kind=kind, minutes=minutes, note=note, created_at=utcnow()))
    amount = {"recovery": X.RECOVERY_DAY, "smart_rest": X.SMART_REST}.get(kind, 0)
    xp = add_xp(db, uid, kind, amount, d.isoformat())
    db.commit()
    return xp


def log_metric(db: Db, uid: int, d: date, kind: str, value: float) -> int:
    first = (
        db.scalar(
            select(func.count(Metric.id)).where(
                Metric.user_id == uid, Metric.date == d, Metric.kind == kind
            )
        )
        == 0
    )
    db.add(Metric(user_id=uid, date=d, kind=kind, value=value, created_at=utcnow()))
    xp = add_xp(
        db,
        uid,
        "morning_checkin",
        X.MORNING_CHECKIN if first and kind == "soreness" else 0,
        d.isoformat(),
    )
    db.commit()
    return xp


# ---------- quick log (shorthand) ----------


def save_parsed(db: Db, uid: int, parsed: ParseResult) -> list[str]:
    """Persist a parsed shorthand log. Lift blocks become finished sessions."""
    out: list[str] = []
    for m in parsed.metrics:
        xp = log_metric(db, uid, m.date, m.kind, m.value)
        out.append(f"{m.date:%a %b %-d}: {m.kind} {m.value:g}" + (f" (+{xp} XP)" if xp else ""))
    for r in parsed.rides:
        xp = log_ride(
            db, uid, r.date, r.miles, r.minutes, r.zone or 2, r.commute, r.elevation_ft, r.note
        )
        out.append(f"{r.date:%a %b %-d}: ride {r.miles:g} mi / {r.minutes} min (+{xp} XP)")
    for lift in parsed.lifts:
        st = ensure_user(db, uid)
        pos = E.Position(lift.phase or st.phase, lift.week or st.week, lift.day or st.day)
        sor, slp, eng = lift.readiness or (None, None, None)
        if st.gate_pending and sor is not None:
            msg = resolve_gate(db, uid, sor)
            if msg:
                out.append(msg)
            st = ensure_user(db, uid)
            if not lift.phase:
                pos = E.Position(st.phase, st.week, lift.day or st.day)
        plan = plan_for(db, uid, pos)
        presc = {e.key: e for e in plan.exercises} if plan else {}
        sess = Session(
            user_id=uid,
            date=lift.date,
            phase=pos.phase,
            week=pos.week,
            day=pos.day,
            heavy=any(
                s.exercise in SQUAT_KEYS + DEADLIFT_KEYS
                or (presc.get(s.exercise) and presc[s.exercise].category in HEAVY_CATEGORIES)
                for s in lift.sets
            ),
            soreness=sor,
            sleep=slp,
            energy=eng,
            status="open",
            note="\n".join(lift.notes),
            started_at=utcnow(),
        )
        counters: dict[str, int] = defaultdict(int)
        for ps in lift.sets:
            p = presc.get(ps.exercise)
            counters[ps.exercise] += 1
            s = SetLog(
                exercise=ps.exercise,
                category=p.category if p else "accessory",
                set_index=counters[ps.exercise],
                prescribed_weight_lb=p.weight_lb if p else None,
                prescribed_reps=p.reps if p and p.kind not in ("hold", "test") else None,
                rpe_cap=p.rpe_cap if p else None,
                rpe_min=p.rpe_range[0] if p and p.rpe_range else None,
                rpe_max=p.rpe_range[1] if p and p.rpe_range else None,
                weight_lb=ps.weight_lb,
                reps=ps.reps,
                seconds=ps.seconds,
                rpe=ps.rpe,
                form_ok=ps.form_ok,
                pain=ps.pain,
            )
            s.xp = _set_xp(s)
            sess.sets.append(s)
        db.add(sess)
        db.flush()
        if lift.readiness:
            add_xp(db, uid, "readiness_checkin", X.READINESS_CHECKIN, f"session-{sess.id}")
        summary = finish_session(db, uid, sess)
        out.append(
            f"{lift.date:%a %b %-d}: {pos.phase} {pos.week} day {pos.day}: "
            f"{len(lift.sets)} sets (+{summary.xp} XP)"
        )
        out.extend(summary.messages)
    db.commit()
    return out


# ---------- insights ----------


def insights(db: Db, uid: int, d: date) -> dict:
    start = d - timedelta(days=83)
    e1: dict[str, dict[str, float]] = {"Squat": {}, "Deadlift": {}}
    for sdate, s in db.execute(
        select(Session.date, SetLog)
        .join(SetLog)
        .where(
            Session.user_id == uid,
            Session.date >= start,
            SetLog.weight_lb.is_not(None),
            SetLog.reps.is_not(None),
            SetLog.rpe.is_not(None),
            SetLog.form_ok.is_(True),
        )
    ):
        label = (
            "Squat"
            if s.exercise in SQUAT_KEYS
            else "Deadlift"
            if s.exercise in DEADLIFT_KEYS
            else None
        )
        v = E.e1rm(s.weight_lb, s.reps, s.rpe) if label else None
        if v:
            k = sdate.isoformat()
            e1[label][k] = max(e1[label].get(k, 0), round(v, 1))
    week0 = d - timedelta(days=d.weekday())
    weeks = [week0 - timedelta(weeks=i) for i in range(11, -1, -1)]
    miles = {w.isoformat(): 0.0 for w in weeks}
    for rdate, m in db.execute(
        select(Ride.date, Ride.miles).where(Ride.user_id == uid, Ride.date >= weeks[0])
    ):
        wk = rdate - timedelta(days=rdate.weekday())
        miles[wk.isoformat()] = round(miles.get(wk.isoformat(), 0) + m, 1)
    metrics = defaultdict(dict)
    for mdate, kind, v in db.execute(
        select(Metric.date, Metric.kind, Metric.value)
        .where(Metric.user_id == uid, Metric.date >= start)
        .order_by(Metric.id)
    ):
        metrics[kind][mdate.isoformat()] = v
    bw = sorted(metrics.get("bodyweight", {}).items())
    bw_avg = []
    for i, (k, _) in enumerate(bw):
        kd = date.fromisoformat(k)
        window = [v for kk, v in bw[: i + 1] if (kd - date.fromisoformat(kk)).days < 7]
        bw_avg.append((k, round(sum(window) / len(window), 1)))
    acts = active_dates(db, uid, d - timedelta(days=27), d)
    calendar = []
    for i in range(27, -1, -1):
        day = d - timedelta(days=i)
        kinds = acts.get(day, set())
        main = next(
            (k for k in ("heavy", "lift", "long_ride", "ride", "recovery", "rest") if k in kinds),
            "none",
        )
        calendar.append({"date": day.isoformat(), "kind": main, "dow": day.strftime("%a")[0]})
    totals = {
        "sessions": db.scalar(
            select(func.count(Session.id)).where(Session.user_id == uid, Session.status == "done")
        )
        or 0,
        "ride_miles": round(
            db.scalar(select(func.coalesce(func.sum(Ride.miles), 0)).where(Ride.user_id == uid))
            or 0,
            1,
        ),
        "active_days_28": sum(1 for c in calendar if c["kind"] not in ("none", "rest")),
    }
    return {
        "e1rm": {k: sorted(v.items()) for k, v in e1.items()},
        "weekly_miles": sorted(miles.items()),
        "soreness": sorted(metrics.get("soreness", {}).items()),
        "bodyweight": bw,
        "bodyweight_avg": bw_avg,
        "calendar": calendar,
        "totals": totals,
        "best": {
            "Squat": best_e1rm(db, uid, SQUAT_KEYS),
            "Deadlift": best_e1rm(db, uid, DEADLIFT_KEYS),
        },
    }


def history(db: Db, uid: int, days: int = 30) -> list[dict]:
    d0 = today() - timedelta(days=days)
    items: dict[date, list[str]] = defaultdict(list)
    for s in db.scalars(
        select(Session).where(Session.user_id == uid, Session.status == "done", Session.date >= d0)
    ):
        tops = summarize(s)
        parts = []
        for ex in tops:
            done = [x for x in ex.sets if x.reps is not None or x.seconds is not None]
            if not done:
                continue
            x = done[-1]
            amt = (
                f"{x.weight_lb:g}×{x.reps}"
                if x.weight_lb
                else (f"{x.seconds}s" if x.seconds else f"×{x.reps}")
            )
            parts.append(
                f"{ex.key.replace('_', ' ')} {amt}"
                + (f" @{x.rpe:g}" if x.rpe else "")
                + (f" ({len(done)} sets)" if len(done) > 1 else "")
            )
        label = f"Lift ({s.phase} {s.week}, day {s.day})"
        items[s.date].append(label + ": " + "; ".join(parts))
    for r in db.scalars(select(Ride).where(Ride.user_id == uid, Ride.date >= d0)):
        c = {"in": " commute in", "out": " commute home", "round": " round-trip commute"}.get(
            r.commute or "", ""
        )
        items[r.date].append(
            f"Ride{c}: {r.miles:g} mi, {r.minutes} min, Z{r.zone}"
            + (f", {r.note}" if r.note else "")
        )
    for x in db.scalars(select(DayLog).where(DayLog.user_id == uid, DayLog.date >= d0)):
        items[x.date].append(
            x.kind.replace("_", " ").title()
            + (f" {x.minutes} min" if x.minutes else "")
            + (f": {x.note}" if x.note else "")
        )
    for m in db.scalars(select(Metric).where(Metric.user_id == uid, Metric.date >= d0)):
        items[m.date].append(
            ("Soreness " if m.kind == "soreness" else "Bodyweight ")
            + f"{m.value:g}"
            + (" lb" if m.kind == "bodyweight" else "/10")
        )
    return [{"date": k, "items": v} for k, v in sorted(items.items(), reverse=True)]


# ---------- path ----------


def total_ride_miles(db: Db, uid: int) -> float:
    return round(
        db.scalar(select(func.coalesce(func.sum(Ride.miles), 0)).where(Ride.user_id == uid)) or 0, 1
    )


def commute_checkpoints(db: Db, uid: int, st: PhaseState) -> list[tuple[str, bool, str]]:
    """The commute map from docs/GAMIFICATION.md."""
    rides = list(db.scalars(select(Ride).where(Ride.user_id == uid)))
    return [
        ("Leave the Ridge", bool(rides), "first ride logged"),
        ("Marina Laps", st.bike_stage >= 2, "bike stage 1 complete"),
        ("Sparks Blvd", any(r.miles >= 10 for r in rides), "first ride of 10+ mi"),
        ("Veterans Pkwy", any(r.commute in ("in", "out") for r in rides), "first one-way commute"),
        ("South Meadows", any(r.commute == "round" for r in rides), "first round-trip commute"),
        ("Commuter", st.bike_stage >= 5, "reach stage 5 and hold it"),
    ]


# ---------- export for Claude (data/logs/*.jsonl) ----------


def export_jsonl(db: Db, uid: int, out_dir: Path) -> dict[str, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}

    def dump(name: str, rows: list[dict]):
        with open(out_dir / name, "w") as f:
            f.writelines(json.dumps(r, default=str) + "\n" for r in rows)
        counts[name] = len(rows)

    lifts = []
    for s in db.scalars(
        select(Session)
        .where(Session.user_id == uid, Session.status == "done")
        .order_by(Session.started_at)
    ):
        for x in s.sets:
            if x.reps is None and x.seconds is None:
                continue
            lifts.append(
                {
                    "id": f"s{s.id}-{x.id}",
                    "date": s.date,
                    "phase": s.phase,
                    "week": s.week,
                    "day": s.day,
                    "exercise": x.exercise,
                    "set": x.set_index,
                    "weight_lb": x.weight_lb,
                    "reps": x.reps,
                    "seconds": x.seconds,
                    "rpe": x.rpe,
                    "rpe_cap": x.rpe_cap,
                    "prescribed_weight_lb": x.prescribed_weight_lb,
                    "prescribed_reps": x.prescribed_reps,
                    "form_ok": x.form_ok,
                    "pain": bool(x.pain),
                    "pain_where": x.pain,
                    "note": s.note,
                }
            )
    dump("lifts.jsonl", lifts)
    dump(
        "readiness.jsonl",
        [
            {
                "date": s.date,
                "session": s.id,
                "soreness": s.soreness,
                "sleep": s.sleep,
                "energy": s.energy,
            }
            for s in db.scalars(
                select(Session).where(Session.user_id == uid, Session.soreness.is_not(None))
            )
        ],
    )
    dump(
        "rides.jsonl",
        [
            {
                "date": r.date,
                "miles": r.miles,
                "minutes": r.minutes,
                "elevation_ft": r.elevation_ft,
                "commute": r.commute,
                "zone": r.zone,
                "note": r.note,
            }
            for r in db.scalars(select(Ride).where(Ride.user_id == uid).order_by(Ride.date))
        ],
    )
    dump(
        "soreness.jsonl",
        [
            {"date": m.date, "soreness": m.value}
            for m in db.scalars(
                select(Metric).where(Metric.user_id == uid, Metric.kind == "soreness")
            )
        ],
    )
    dump(
        "bodyweight.jsonl",
        [
            {"date": m.date, "lb": m.value}
            for m in db.scalars(
                select(Metric).where(Metric.user_id == uid, Metric.kind == "bodyweight")
            )
        ],
    )
    dump(
        "days.jsonl",
        [
            {"date": x.date, "kind": x.kind, "minutes": x.minutes, "note": x.note}
            for x in db.scalars(select(DayLog).where(DayLog.user_id == uid))
        ],
    )
    return counts
