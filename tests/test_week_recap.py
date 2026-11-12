"""Week recap (D35–D37): what each week earned and what it unlocked."""

from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

WEEK1_MON = date(2026, 10, 26)
WEEK2_MON = date(2026, 11, 2)
WEEK2_THU = date(2026, 11, 5)


@pytest.fixture
def clock(app_env, monkeypatch):
    """Set the app's "today"; returns a setter."""
    from gigalegs import config, services

    monkeypatch.setenv("GIGALEGS_TZ", "America/Los_Angeles")  # the XP test's UTC offsets
    config.get_settings.cache_clear()
    state = {"d": WEEK2_MON}
    monkeypatch.setattr(services, "today", lambda: state["d"])

    def set_today(d: date) -> None:
        state["d"] = d

    return set_today


@pytest.fixture
def c(clock):
    from gigalegs.web.app import app

    return TestClient(app)


def run(c, key: str, d: date) -> None:
    c.post(f"/do/{key}/cardio", data={"minutes": "25", "day": d.isoformat()})


def recap(week_no: int, uid: int = 1):
    from gigalegs import missions
    from gigalegs.db import get_sessionmaker

    with get_sessionmaker()() as db:
        return missions.week_recap(db, uid, week_no)


def test_two_runs_move_runs_up(c):
    run(c, "run1", WEEK1_MON)
    run(c, "run2", WEEK1_MON + timedelta(2))
    r = recap(1)
    assert r.runs_done == 2 and r.status == "past"
    assert r.run_line == "Runs move up to Week 2's level (2 runs, 2 needed)."
    assert "Runs move up to Week 2" in c.get("/week/1").text


def test_one_run_repeats_and_shows_1_of_2(c):
    run(c, "run1", WEEK1_MON)
    r = recap(1)
    assert r.run_line == "Runs repeat Week 1's level (1 run, 2 needed)."
    assert "repeats Week 1's length" in r.ride_line
    html = c.get("/week/1").text
    assert "1 run, 2 needed" in html and "1/8 done" in html


def test_long_ride_moves_up(c):
    c.post("/do/ride_long/cardio", data={"minutes": "60", "day": WEEK1_MON.isoformat()})
    r = recap(1)
    assert r.long_ride_done
    assert r.ride_line == "The long ride moves up to Week 2's length."


def test_calendar_rules_after_lag():
    from gigalegs.engine import recap as RC
    from gigalegs.engine import season as SE

    w = SE.LAG_RUN_UNTIL
    assert "follow the calendar" in RC.run_unlock(w, 10, w + 1, 0)
    assert "follows the calendar" in RC.ride_unlock(SE.LAG_RIDE_UNTIL, 10, 31, False)


def test_forgiven_week_counts_as_done(c):
    from gigalegs import missions, services
    from gigalegs.db import get_sessionmaker

    with get_sessionmaker()() as db:
        services.ensure_user(db, 1)
        missions.forgive_week(db, 1, 1)
        db.commit()
    r = recap(1)
    assert r.forgiven and r.counts_as_done
    assert r.run_line == "Runs move up to Week 2's level (forgiven week)."
    assert "counts as done" in c.get("/week/1").text


def test_recap_xp_is_sum_of_week_xp_events(c):
    from gigalegs import services
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import XpEvent

    def ev(uid: int, ts: datetime, amount: int) -> XpEvent:
        # XpEvent.ts is stored as naive UTC
        ts = ts.replace(tzinfo=None)
        return XpEvent(user_id=uid, ts=ts, source="mission", amount=amount, ref="t")

    with get_sessionmaker()() as db:
        services.ensure_user(db, 1)
        services.ensure_user(db, 2)
        db.add_all(
            [
                ev(1, datetime(2026, 10, 26, 18, tzinfo=UTC), 100),  # Mon week 1 (local morning)
                ev(1, datetime(2026, 11, 2, 5, tzinfo=UTC), 30),  # Sun Nov 1 evening local: week 1
                ev(1, datetime(2026, 11, 3, 18, tzinfo=UTC), 150),  # week 2
                ev(1, datetime(2026, 10, 20, 18, tzinfo=UTC), 40),  # week 0
                ev(2, datetime(2026, 10, 27, 18, tzinfo=UTC), 999),  # another user
            ]
        )
        db.commit()
    assert recap(1).xp == 130
    assert recap(2).xp == 150
    assert "+130 XP" in c.get("/week/1").text


def test_last_week_card_monday_not_thursday(c, clock):
    run(c, "run1", WEEK1_MON)
    html = c.get("/").text
    assert "Last week · Week 1" in html and 'href="/week/1"' in html
    assert "Runs repeat Week 1&#39;s level (1 run, 2 needed)" in html
    clock(WEEK2_THU)
    assert "Last week" not in c.get("/").text


def test_week_out_of_season_is_404(c):
    assert c.get("/week/999").status_code == 404
    assert c.get("/week/-1").status_code == 404


def test_future_week_shows_plan_only(c):
    r = recap(5)
    assert r.status == "future" and r.slots_done == 0 and r.run_line is None
    html = c.get("/week/5").text
    assert "nothing is logged yet" in html and "What it unlocked" not in html


def test_other_users_missions_do_not_appear(c):
    from gigalegs import missions, services
    from gigalegs.db import get_sessionmaker

    with get_sessionmaker()() as db:
        services.ensure_user(db, 2)
        missions._add_mission(
            db, 2, WEEK1_MON, None, "run", "standard", "Someone else's run", "ride-x", None
        )
        db.commit()
    r = recap(1)
    assert r.runs_done == 0 and all(not d.missions for d in r.days)
    assert "Someone else" not in c.get("/week/1").text
    assert recap(1, uid=2).runs_done == 1


def test_season_links_past_and_current_weeks(c):
    html = c.get("/season").text
    assert 'href="/week/1"' in html and 'href="/week/2"' in html
    assert 'href="/week/3"' not in html
