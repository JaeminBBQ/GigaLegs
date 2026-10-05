"""One named test per rule for streaks and badges (docs/GAMIFICATION.md)."""

import re
from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from gigalegs.engine import badges as B
from gigalegs.engine import streaks as ST
from gigalegs.engine.badges import BadgeFacts
from gigalegs.engine.streaks import WeekFacts


def wk(lifts=0, active=0, protected=False):
    return WeekFacts(lifts, active, protected)


# --- engine: week counts


def test_week_counts_needs_two_lifts_and_four_active_days():
    assert ST.week_counts(wk(lifts=2, active=4))
    assert not ST.week_counts(wk(lifts=2, active=3))
    assert not ST.week_counts(wk(lifts=1, active=6))


def test_week_counts_protected_week_counts_without_lifts():
    assert ST.week_counts(wk(lifts=0, active=0, protected=True))


# --- engine: weekly streak


def test_weekly_streak_counts_finished_weeks():
    weeks = [wk(2, 4), wk(2, 4), wk(2, 4)]
    assert ST.weekly_streak(weeks, 0) == (3, 0)


def test_weekly_streak_freezes_newest_miss_first():
    # Newest week missed: the freeze is spent there; the older miss stops the streak.
    weeks = [wk(), wk(2, 4), wk()]
    assert ST.weekly_streak(weeks, 1) == (1, 1)


def test_weekly_streak_frozen_week_does_not_add_to_count():
    weeks = [wk(2, 4), wk(), wk(2, 4)]
    assert ST.weekly_streak(weeks, 1) == (2, 1)


def test_weekly_streak_stops_at_unfrozen_miss():
    weeks = [wk(), wk(2, 4), wk(2, 4)]
    assert ST.weekly_streak(weeks, 0) == (2, 0)


def test_weekly_streak_no_weeks():
    assert ST.weekly_streak([], 3) == (0, 0)


def test_freezes_available_one_per_six_started_weeks_never_negative():
    assert ST.freezes_available(5, 0) == 0
    assert ST.freezes_available(6, 0) == 1
    assert ST.freezes_available(12, 0) == 2
    assert ST.freezes_available(12, 1) == 1
    assert ST.freezes_available(2, 1) == 0


# --- engine: badges


def test_badges_all_keys_with_qualifying_facts():
    facts = BadgeFacts(
        finished_onramp=True,
        finished_sessions=1,
        commute_miles=100.0,
        gated_repeats=2,
        smart_rests=1,
        best_squat_e1rm=405.0,
        bike_stage=5,
    )
    assert B.earned(facts) == set(B.BADGES)


def test_plate_badges_boundaries():
    def plates(e1rm):
        got = B.earned(BadgeFacts(False, 0, 0.0, 0, 0, e1rm, 1))
        return {k for k in got if k.startswith("plate")}

    assert plates(224.9) == set()
    assert plates(225.0) == {"plate_225"}
    assert plates(404.9) == {"plate_225", "plate_275", "plate_315", "plate_365"}
    assert plates(405.0) == {f"plate_{p}" for p in B.PLATE_MILESTONES}
    assert plates(None) == set()


def test_smart_rest_badge_combines_gated_repeats_and_smart_rests():
    def smart(gated, rests):
        return B.earned(BadgeFacts(False, 0, 0.0, gated, rests, None, 1))

    assert "smart_rest" not in smart(2, 0)
    assert "smart_rest" in smart(2, 1)
    assert "smart_rest" in smart(3, 0)
    assert "smart_rest" in smart(0, 3)


def test_patience_pays_iron_lungs_and_commuter_thresholds():
    assert "patience_pays" not in B.earned(BadgeFacts(False, 1, 0.0, 0, 0, None, 1))
    assert "patience_pays" in B.earned(BadgeFacts(True, 0, 0.0, 0, 0, None, 1))
    assert "first_session" not in B.earned(BadgeFacts(False, 0, 0.0, 0, 0, None, 1))
    assert "first_session" in B.earned(BadgeFacts(False, 1, 0.0, 0, 0, None, 1))
    assert "iron_lungs" not in B.earned(BadgeFacts(False, 0, 99.9, 0, 0, None, 1))
    assert "iron_lungs" in B.earned(BadgeFacts(False, 0, 100.0, 0, 0, None, 1))
    assert "commuter" not in B.earned(BadgeFacts(False, 0, 0.0, 0, 0, None, 4))
    assert "commuter" in B.earned(BadgeFacts(False, 0, 0.0, 0, 0, None, 5))


# --- services: week facts and streaks

MON = date(2026, 10, 5)  # a Monday (2026-10-15 is a Thursday)
THU = date(2026, 10, 15)


def _db():
    from gigalegs.db import get_sessionmaker

    return get_sessionmaker()()


def _mk_session(uid, d):
    from gigalegs.db import utcnow
    from gigalegs.models import Session

    return Session(
        user_id=uid,
        date=d,
        phase="onramp",
        week="A",
        day=1,
        heavy=True,
        status="done",
        started_at=utcnow(),
        finished_at=utcnow(),
    )


def _mk_daylog(d, kind):
    from gigalegs.db import utcnow
    from gigalegs.models import DayLog

    return DayLog(user_id=1, date=d, kind=kind, minutes=20, note="", created_at=utcnow())


def test_week_facts_recovery_counts_as_active_rest_does_not(app_env):
    from gigalegs import services as S

    with _db() as db:
        S.ensure_user(db, 1)
        db.add(_mk_session(1, MON))
        db.add(_mk_session(1, date(2026, 10, 7)))
        db.add(_mk_daylog(date(2026, 10, 6), "recovery"))
        db.add(_mk_daylog(date(2026, 10, 8), "rest"))
        db.commit()
        f = S.week_facts(db, 1, MON, date(2026, 10, 11))[0]
        assert (f.lift_sessions, f.active_days, f.protected) == (2, 3, False)
        assert not ST.week_counts(f)
        db.add(_mk_daylog(date(2026, 10, 9), "recovery"))
        db.commit()
        assert ST.week_counts(S.week_facts(db, 1, MON, date(2026, 10, 11))[0])


def test_week_facts_smart_rest_protects_week(app_env):
    from gigalegs import services as S

    with _db() as db:
        S.ensure_user(db, 1)
        db.add(_mk_daylog(date(2026, 10, 6), "smart_rest"))
        db.commit()
        facts = S.week_facts(db, 1, MON, date(2026, 10, 11))
        assert facts[0].protected
        assert ST.week_counts(facts[0])


def test_week_facts_gated_repeat_protects_week(app_env):
    from gigalegs import services as S
    from gigalegs.models import XpEvent

    with _db() as db:
        S.ensure_user(db, 1)
        # 19:00 UTC on Oct 6 is still Oct 6 in America/Los_Angeles. ts is naive
        # UTC by convention (see utcnow()).
        db.add(
            XpEvent(
                user_id=1,
                ts=datetime(2026, 10, 6, 19, 0, tzinfo=UTC).replace(tzinfo=None),
                source="gated_repeat",
                amount=50,
                ref="onramp-A",
            )
        )
        db.commit()
        facts = S.week_facts(db, 1, MON, date(2026, 10, 11))
        assert facts[0].protected
        # The following week is not protected by the same event.
        assert not S.week_facts(db, 1, date(2026, 10, 12), date(2026, 10, 18))[0].protected


def _add_counting_week(db, monday):
    db.add(_mk_session(1, monday))
    db.add(_mk_session(1, monday + timedelta(days=2)))
    db.add(_mk_daylog(monday + timedelta(days=1), "recovery"))
    db.add(_mk_daylog(monday + timedelta(days=3), "recovery"))


def test_streak_excludes_current_week(app_env, monkeypatch):
    from gigalegs import services as S

    monkeypatch.setattr("gigalegs.services.today", lambda: THU)
    with _db() as db:
        S.ensure_user(db, 1)
        _add_counting_week(db, MON)  # Oct 5–11: counts
        # Current week (Oct 12+) also counts if included — it must be excluded.
        _add_counting_week(db, date(2026, 10, 12))
        db.commit()
        st = S.streak(db, 1)
        assert (st.weeks, st.freezes_used, st.freezes_left, st.total_weeks) == (1, 0, 0, 2)


def test_streak_freezes_old_miss_end_to_end(app_env, monkeypatch):
    from gigalegs import services as S

    monkeypatch.setattr("gigalegs.services.today", lambda: date(2026, 11, 12))
    with _db() as db:
        S.ensure_user(db, 1)
        for monday in (
            date(2026, 9, 28),
            date(2026, 10, 5),
            date(2026, 10, 12),
            date(2026, 10, 19),
            date(2026, 11, 2),
        ):
            _add_counting_week(db, monday)
        db.add(_mk_session(1, date(2026, 10, 27)))  # Oct 26 week missed
        db.commit()
        # 7 started weeks → 1 freeze; the Oct 26 miss burns it, streak survives.
        st = S.streak(db, 1)
        assert (st.weeks, st.freezes_used, st.freezes_left, st.total_weeks) == (5, 1, 0, 7)


def test_award_badges_only_once(app_env):
    from gigalegs import services as S

    with _db() as db:
        S.ensure_user(db, 1)
        st = S.ensure_user(db, 1)
        st.phase = "program"  # on-ramp finished through the gate: week C's 3 days done
        for day in (1, 2, 3):
            sess = _mk_session(1, date(2026, 10, 18 + day))
            sess.week, sess.day = "C", day
            db.add(sess)
        db.commit()
        first = S.award_badges(db, 1)
        assert "patience_pays" in first and "first_session" in first
        assert S.award_badges(db, 1) == []
    with _db() as db:
        assert S.award_badges(db, 1) == []  # persisted across sessions


# --- web


def client():
    from gigalegs.web.app import app

    return TestClient(app)


def test_iron_lungs_badge_after_ten_commutes_shows_on_path(app_env):
    c = client()
    for _ in range(10):
        c.post("/ride", data={"miles": "10", "minutes": "50", "zone": "2", "commute": "in"})
    html = c.get("/path").text
    assert "★ Iron Lungs" in html and "Earned" in html
    assert "Plate Collector 225" in html  # unearned badge shows how to earn it


def test_first_session_badge_shown_on_summary(app_env):
    c = client()
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
    done = c.post(f"/session/{sid}/finish", data={"note": ""})
    assert "Badge earned: First Session" in done.text


def test_patience_pays_needs_the_gate_not_a_skip(app_env):
    from fastapi.testclient import TestClient

    from gigalegs.web.app import app

    c = TestClient(app)
    c.post("/path/position", data={"phase": "program", "week": "1", "day": "1"})
    c.post("/ride", data={"miles": "5", "minutes": "25", "zone": "2"})  # triggers award_badges
    html = c.get("/path").text
    assert "Badges · 0 of" in html


def test_bike_stage_change_awards_commuter(app_env):
    from fastapi.testclient import TestClient

    from gigalegs.web.app import app

    c = TestClient(app)
    c.post("/path/bike-stage", data={"stage": "5"})
    assert "Badges · 1 of" in c.get("/path").text
