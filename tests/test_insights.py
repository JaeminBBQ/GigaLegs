"""/insights for season v2: lift progress, cardio split by sport, floor days as active."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

TODAY = date(2026, 11, 4)  # Week 2 of the public season plan; all numbers below are made up


@pytest.fixture
def c(app_env, monkeypatch):
    from gigalegs import services
    from gigalegs.web.app import app

    monkeypatch.setattr(services, "today", lambda: TODAY)
    client = TestClient(app)
    with _db() as db:
        services.ensure_user(db, 1)
        db.commit()
    return client


def _db():
    from gigalegs.db import get_sessionmaker

    return get_sessionmaker()()


def _leg_press(d: date, weight: float, reps: int = 12) -> None:
    from gigalegs import missions as M

    with _db() as db:
        M.log_gym(
            db,
            1,
            d,
            None,
            [M.LoggedExercise("squat_pattern", "Leg press", 7.0, [(weight, reps, 7.0)] * 3)],
            push=False,
            pain=None,
            note="",
        )


def _lift(name: str) -> dict:
    from gigalegs import services as S

    with _db() as db:
        return next(x for x in S.insights(db, 1, TODAY)["lifts"] if x["name"] == name)


def test_lift_series_change_and_engine_target(c):
    from gigalegs import missions as M

    for d, w in ((date(2026, 10, 28), 180), (date(2026, 10, 30), 190), (date(2026, 11, 2), 200)):
        _leg_press(d, w)
    lp = _lift("Leg press")
    assert lp["points"] == [("2026-10-28", 180), ("2026-10-30", 190), ("2026-11-02", 200)]
    assert lp["start"] == 180 and lp["current"] == 200
    assert lp["change"] == "+20 lb since Oct 28"

    with _db() as db:
        week = M.get_season().week_for(TODAY)
        engine = next(t for t in M.gym_targets(db, 1, week, "A") if t.option == "Leg press")
    assert lp["target"]["weight"] == engine.target.weight
    assert lp["target"]["note"] == engine.target.note
    assert lp["target"]["sets"] == engine.target.sets

    html = c.get("/insights").text
    assert "Leg press" in html and "+20 lb since Oct 28" in html
    assert f"{engine.target.weight:g} lb" in html


def test_floor_day_counts_as_active(c):
    from gigalegs import missions as M
    from gigalegs import services as S

    with _db() as db:
        M.log_floor(db, 1, date(2026, 11, 3), "walk")
        S.log_day(db, 1, date(2026, 11, 2), "rest", None, "")
        acts = S.active_dates(db, 1, date(2026, 11, 1), TODAY)
        data = S.insights(db, 1, TODAY)
    assert acts[date(2026, 11, 3)] == {"floor"}
    assert data["totals"]["active_days_28"] == 1  # the floor day counts, the rest day doesn't
    assert next(x for x in data["calendar"] if x["date"] == "2026-11-03")["kind"] == "floor"
    assert 'class="k-floor"' in c.get("/insights").text


def test_runs_and_rides_reported_separately(c):
    from gigalegs import missions as M
    from gigalegs import services as S

    with _db() as db:
        M.log_cardio(db, 1, date(2026, 11, 2), "run", None, 30, 3.0, 2, False, None, "")
        M.log_cardio(db, 1, date(2026, 11, 3), "ride", None, 45, 12.0, 2, False, None, "")
        cardio = S.insights(db, 1, TODAY)["cardio"]
    week = "2026-11-02"
    assert dict(cardio["run_minutes"])[week] == 30
    assert dict(cardio["run_miles"])[week] == 3.0
    assert dict(cardio["ride_minutes"])[week] == 45
    assert dict(cardio["ride_miles"])[week] == 12.0
    assert cardio["totals"] == {
        "run": {"minutes": 30, "miles": 3.0},
        "ride": {"minutes": 45, "miles": 12.0},
    }


def test_insights_renders_with_no_data(c):
    r = c.get("/insights")
    assert r.status_code == 200
    html = r.text
    assert "Lifts" in html and "Weekly run minutes" in html and "Weekly ride minutes" in html
    assert "e1RM" not in html and "soreness" not in html.lower()
    assert "Bodyweight</h2>" not in html  # no bodyweight data, no section
