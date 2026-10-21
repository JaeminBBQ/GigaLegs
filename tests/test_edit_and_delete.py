"""One named test per rule for T018: edit and delete keep XP consistent."""

import re

from fastapi.testclient import TestClient
from sqlalchemy import select

from gigalegs.engine import xp as X


def client():
    from gigalegs.web.app import app

    return TestClient(app)


def _db():
    from gigalegs.db import get_sessionmaker

    return get_sessionmaker()()


def _level(db):
    from gigalegs import services as S

    return S.level_info(db, 1).total


def _finish_full_session(c):
    """Start a session, log every set at RPE 5, finish. Returns (sid, total_xp)."""
    from gigalegs import services as S

    r = c.post(
        "/session/start", data={"soreness": 2, "sleep": 7, "energy": 7}, follow_redirects=False
    )
    sid = int(re.search(r"/session/(\d+)", r.headers["location"])[1])
    page = c.get(f"/session/{sid}").text
    for set_id, form in re.findall(rf'/session/{sid}/set/(\d+)"(.*?)</form>', page, re.DOTALL):
        reps = re.search(r'name="reps"[^>]*value="(\d*)"', form)
        c.post(
            f"/session/{sid}/set/{set_id}",
            data={"reps": reps[1] if reps else "", "seconds": "30", "rpe": "5"},
        )
    c.post(f"/session/{sid}/finish", data={"note": ""})
    with _db() as db:
        return sid, S.level_info(db, 1).total


def _weight_set(db, sid):
    from gigalegs.models import SetLog

    return db.scalar(
        select(SetLog).where(SetLog.session_id == sid, SetLog.reps.is_not(None)).order_by(SetLog.id)
    )


def test_edit_set_over_cap_drops_set_and_session_bonus_xp(app_env):
    from gigalegs.models import XpEvent

    c = client()
    sid, t1 = _finish_full_session(c)
    with _db() as db:
        s = _weight_set(db, sid)
        set_xp_before, set_id = s.xp, s.id
        weight, reps = s.weight_lb, s.reps
        wform = str(weight) if weight is not None else ""
    # Over the cap (6): the set earns 0 and the session bonus collapses too.
    row = c.post(
        f"/session/{sid}/edit-set/{set_id}",
        data={"weight": wform, "reps": str(reps), "rpe": "9"},
    )
    assert row.status_code == 200 and "over cap" in row.text
    with _db() as db:
        assert _level(db) == t1 - (set_xp_before + X.SESSION_AS_PRESCRIBED)
        assert db.scalar(select(XpEvent).where(XpEvent.ref == f"set-{set_id}")) is None
    # Edit it back: set XP and the session bonus return.
    row = c.post(
        f"/session/{sid}/edit-set/{set_id}",
        data={"weight": wform, "reps": str(reps), "rpe": "5"},
    )
    assert row.status_code == 200 and "XP" in row.text
    with _db() as db:
        assert _level(db) == t1
        ev = db.scalar(select(XpEvent).where(XpEvent.ref == f"set-{set_id}"))
        assert ev is not None and ev.amount == set_xp_before
        bonus = db.scalar(
            select(XpEvent).where(XpEvent.ref == f"session-{sid}", XpEvent.source == "session")
        )
        assert bonus is not None and bonus.amount == X.SESSION_AS_PRESCRIBED


def test_delete_ride_removes_exactly_its_xp(app_env):
    from gigalegs import services as S
    from gigalegs.models import Ride

    c = client()
    c.post("/ride", data={"miles": "10", "minutes": "50", "zone": "2", "commute": "in"})
    with _db() as db:
        t1 = _level(db)
        ride = db.scalar(select(Ride).where(Ride.user_id == 1))
        assert S.delete_ride(db, 1, ride.id) == 15  # 10 mi x 1.5 commute
        assert _level(db) == t1 - 15
    assert "commute in" not in c.get("/history").text


def test_update_ride_recomputes_xp(app_env):
    from gigalegs import services as S
    from gigalegs.models import Ride

    c = client()
    c.post("/ride", data={"miles": "10", "minutes": "50", "zone": "2", "commute": "in"})
    with _db() as db:
        t1 = _level(db)
        ride = db.scalar(select(Ride).where(Ride.user_id == 1))
        # Zone 3 earns nothing: the event is removed.
        assert S.update_ride(db, 1, ride.id, ride.date, 10.0, 50, 3, "in", None, "") == 0
        assert _level(db) == t1 - 15
        # Back to zone 2, no commute: 10 XP.
        assert S.update_ride(db, 1, ride.id, ride.date, 10.0, 50, 2, None, None, "") == 10
        assert _level(db) == t1 - 5


def test_delete_session_removes_all_its_xp_and_keeps_phase_state(app_env):
    from gigalegs import services as S
    from gigalegs.models import PhaseState, XpEvent

    c = client()
    sid, t1 = _finish_full_session(c)
    assert t1 > 0
    with _db() as db:
        st = S.ensure_user(db, 1)
        before = (st.phase, st.week, st.day, st.gate_pending)
    assert c.post(f"/session/{sid}/delete", follow_redirects=False).status_code == 303
    with _db() as db:
        assert _level(db) == 0
        st = db.get(PhaseState, 1)
        assert (st.phase, st.week, st.day, st.gate_pending) == before
        n_events = db.scalar(
            select(XpEvent).where(XpEvent.user_id == 1).with_only_columns(XpEvent.id)
        )
        assert n_events is None  # every session/set/readiness event went with it


def test_delete_someone_elses_row_returns_404(app_env):
    from datetime import date

    from gigalegs import services as S
    from gigalegs.models import Ride

    with _db() as db:
        S.ensure_user(db, 2)
        S.log_ride(db, 2, date(2026, 10, 4), 5.0, 25, 2, None, None, "")
        ride = db.scalar(select(Ride).where(Ride.user_id == 2))
    c = client()
    assert c.post(f"/ride/{ride.id}/delete").status_code == 404
    assert c.get(f"/ride/{ride.id}/edit").status_code == 404
    with _db() as db:
        assert S.delete_ride(db, 1, ride.id) is None


def test_level_total_matches_recomputed_xp_after_mix(app_env):
    from gigalegs import engine as E
    from gigalegs import services as S
    from gigalegs.models import Ride, Session

    c = client()
    c.post("/log/save", data={"text": "lift\nready 2 7 7\nsq 135x5x2 @6\nplank 45s x2"})
    c.post("/ride", data={"miles": "5", "minutes": "25", "zone": "2"})
    with _db() as db:
        sess = db.scalar(select(Session).where(Session.user_id == 1))
        s = _weight_set(db, sess.id)
        # Over the cap, then back: the event is deleted, then recreated.
        S.update_set(db, 1, s.id, s.weight_lb, s.reps, None, 9.0, True, None)
    c.post("/ride", data={"miles": "10", "minutes": "50", "zone": "2", "commute": "in"})
    with _db() as db:
        ride = db.scalar(select(Ride).where(Ride.user_id == 1).order_by(Ride.id.desc()))
        assert ride.miles == 10
        assert c.post(f"/ride/{ride.id}/delete", follow_redirects=False).status_code == 303
        sess = db.scalar(select(Session).where(Session.user_id == 1))
        s = _weight_set(db, sess.id)
        S.update_set(db, 1, s.id, s.weight_lb, s.reps, None, 5.0, True, None)
    with _db() as db:
        expected = 0
        for sess in db.scalars(select(Session).where(Session.user_id == 1)):
            expected += sum(x.xp for x in sess.sets)
            expected += S._session_bonus(db, 1, sess)[1]
            if sess.soreness is not None:
                expected += X.READINESS_CHECKIN
        for r in db.scalars(select(Ride).where(Ride.user_id == 1)):
            expected += E.ride_xp(r.miles, r.commute is not None, r.zone)
        assert _level(db) == expected
