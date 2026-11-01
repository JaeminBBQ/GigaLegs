"""Season v2 (D27–D32): engine rules and the mission flows, on fixed dates."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from gigalegs.engine import season as SE

WED_WEEK1 = date(2026, 10, 28)


# ---------- engine ----------


@pytest.fixture(scope="module")
def season():
    import json

    from conftest import SEASON

    return SE.load_season(json.loads(SEASON.read_text()))


def test_weeks_and_dates(season):
    assert season.week_for(date(2026, 10, 21)).week == 0
    assert season.week_for(WED_WEEK1).week == 1
    assert season.week_for(date(2027, 4, 24)).week == 26  # half marathon Saturday
    assert season.week_for(date(2027, 6, 6)).week == 32  # Tahoe Sunday
    assert season.week_for(date(2030, 1, 1)).week == season.weeks[-1].week


def test_effective_level_repeats_missed_weeks():
    assert SE.effective_level(1, set(), 23) == 1
    assert SE.effective_level(4, {1, 2, 3}, 23) == 4
    assert SE.effective_level(4, {1}, 23) == 2  # missed weeks 2 and 3
    assert SE.effective_level(24, set(), 23) == 24  # taper and race weeks follow the calendar


def test_week_slots_use_level_for_runs_only(season):
    slots = SE.week_slots(season, 5, run_level=3, ride_level=5)
    runs = [s for s in slots if s.kind == "run"]
    assert all("Easy jog, 18 min" in s.title for s in runs)
    assert sum(s.kind == "gym" for s in slots) == 3
    assert any(s.long and "70 min" in s.title for s in slots if s.kind == "ride")


def _slots(season, w):
    return list(season.week(w).slots)


NONE = SE.DayDone()


def test_suggest_weekday_gym_weekend_long(season):
    s = SE.suggest(_slots(season, 1), WED_WEEK1, 1, NONE, NONE, NONE, False)
    assert s.slot.kind == "gym"
    sat = date(2026, 10, 31)
    s = SE.suggest(_slots(season, 9), sat, 9, NONE, NONE, NONE, False)
    assert s.slot.key == "run_long"


def test_no_back_to_back_runs_early(season):
    runs = [x for x in _slots(season, 2) if x.kind == "run"]
    ran = SE.DayDone(kinds=frozenset({"run"}))
    s = SE.suggest(runs, date(2026, 11, 4), 2, NONE, ran, NONE, False)
    assert s.slot is None and "back-to-back" in s.reasons[0]


def test_one_session_per_kind_per_day(season):
    gyms = [x for x in _slots(season, 1) if x.kind == "gym"]
    s = SE.suggest(gyms, WED_WEEK1, 1, SE.DayDone(kinds=frozenset({"gym"})), NONE, NONE, False)
    assert s.slot is None


def test_pain_means_floor_only(season):
    s = SE.suggest(_slots(season, 1), WED_WEEK1, 1, NONE, NONE, NONE, True)
    assert s.slot is None and s.floor_only


def test_gym_double_progression():
    top = [SE.SetPerf(100, 12, 8), SE.SetPerf(100, 12, 8.5)]
    mid = [SE.SetPerf(100, 10, 8), SE.SetPerf(100, 9, 8)]
    miss = [SE.SetPerf(100, 6, 9), SE.SetPerf(100, 7, 9)]
    assert SE.next_gym_weight([], (8, 12), 8, 10)[0] is None
    assert SE.next_gym_weight([top], (8, 12), 9, 5)[0] == 105
    assert SE.next_gym_weight([mid], (8, 12), 9, 5)[0] == 100
    assert SE.next_gym_weight([miss], (8, 12), 9, 5)[0] == 100
    assert SE.next_gym_weight([miss, miss], (8, 12), 9, 5)[0] == 90
    over_cap = [SE.SetPerf(100, 12, 9.5)]
    assert SE.next_gym_weight([over_cap], (8, 12), 9, 5)[0] == 100


def test_timed_hold_progresses_by_time_not_load():
    short = [SE.SetPerf(None, 40, 7), SE.SetPerf(None, 35, 7)]
    full = [SE.SetPerf(None, 60, 7), SE.SetPerf(None, 60, 7)]
    w, note = SE.next_gym_weight([], (30, 60), 7, 5, timed=True)
    assert w is None and "hold" in note
    w, note = SE.next_gym_weight([short], (30, 60), 7, 5, timed=True)
    assert w is None and "60 s" in note
    w, note = SE.next_gym_weight([full], (30, 60), 7, 5, timed=True)
    assert w is None and "harder" in note


def test_early_runs_are_steady_jogs(season):
    for n in range(9):
        for s in season.week(n).slots:
            if s.kind == "run":
                assert "×" not in s.detail and "walk" not in s.detail.lower()


def test_gym_caps_and_sets():
    assert SE.gym_rpe_cap(1, lower=False) == 7
    assert SE.gym_rpe_cap(5, lower=True) == 8 and SE.gym_rpe_cap(5, lower=False) == 9
    assert SE.gym_rpe_cap(22, lower=True) == 7
    assert SE.gym_sets(3, 4, "down", lower=False) == 2
    assert SE.gym_sets(3, 22, None, lower=True) == 2


def test_daily_streak_and_freezes():
    d0 = date(2026, 11, 1)
    days = {d0 + timedelta(i) for i in range(3)}
    assert SE.daily_streak(days, d0 + timedelta(2)).days == 3
    assert SE.daily_streak(days, d0 + timedelta(3)).days == 3  # today not logged yet
    assert SE.daily_streak(days, d0 + timedelta(4)).days == 0  # missed a day, no freeze
    long = {d0 + timedelta(i) for i in range(14)} | {d0 + timedelta(15)}
    s = SE.daily_streak(long, d0 + timedelta(15))
    assert s.days == 15 and s.freezes == 0  # day 14 missed, freeze spent
    excused = {d0 + timedelta(3)}
    assert SE.daily_streak(days | {d0 + timedelta(4)}, d0 + timedelta(4), excused).days == 4


# ---------- web flows ----------


@pytest.fixture
def c(app_env, monkeypatch):
    from gigalegs import services
    from gigalegs.web.app import app

    monkeypatch.setattr(services, "today", lambda: WED_WEEK1)
    return TestClient(app)


def xp():
    from gigalegs import services
    from gigalegs.db import get_sessionmaker

    with get_sessionmaker()() as db:
        return services.level_info(db, 1).total


def test_today_page(c):
    html = c.get("/").text
    assert "Week 1" in html and "Today's mission" in html and "Gym A" in html
    assert "How sore" not in html


def test_floor_counts_once_per_day(c):
    c.post("/floor", data={"option": "walk"})
    assert xp() == 30
    c.post("/floor", data={"option": "circuit"})
    assert xp() == 30
    assert "1-day streak" in c.get("/").text
    assert c.post("/floor", data={"option": "nap"}).status_code == 400


def test_run_mission_and_checklist(c):
    c.post("/do/run1/cardio", data={"minutes": "25", "day": WED_WEEK1.isoformat()})
    assert xp() == 100
    html = c.get("/").text
    assert "1/8 done" in html
    # logging the same slot again: activity saved, no more mission XP
    c.post("/do/run1/cardio", data={"minutes": "25"})
    assert xp() == 100


def test_push_bonus_capped_at_two_per_week(c):
    c.post("/do/ride_easy/cardio", data={"minutes": "40", "push": "1"})
    assert xp() == 120
    for i, key in enumerate(("gym1", "gym2")):
        c.post(
            f"/do/{key}/gym", data={"push": "1", "day": (WED_WEEK1 + timedelta(i + 1)).isoformat()}
        )
    # gym1 push: +20 (2nd push); gym2 push: no bonus (3rd)
    assert xp() == 120 + 120 + 100


def test_gym_logging_and_progression(c):
    page = c.get("/do/gym1").text
    assert "Leg press" in page and "RPE ≤ 7" in page  # week 1 cap
    form = {"squat_pattern_option": "Leg press"}
    for i in (1, 2, 3):
        form.update(
            {
                f"squat_pattern_w{i}": "200",
                f"squat_pattern_r{i}": "12",
                f"squat_pattern_rpe{i}": "7",
            }
        )
    c.post("/do/gym1/gym", data=form)
    assert xp() == 100 + 3 * 10  # 5 logged + 5 on target (within 2 of the cap)
    nxt = c.get("/do/gym3").text
    assert "210 lb" in nxt and "+10 lb" in nxt


def test_plank_logs_seconds(c):
    from sqlalchemy import select

    from gigalegs.db import get_sessionmaker
    from gigalegs.models import SetLog

    page = c.get("/do/gym2?opt_core=Plank").text
    assert "30–60 s hold" in page and 'name="core_w1"' not in page
    c.post(
        "/do/gym2/gym",
        data={"core_option": "Plank", "core_r1": "45", "core_rpe1": "7", "core_r2": "40"},
    )
    with get_sessionmaker()() as db:
        rows = db.scalars(select(SetLog).where(SetLog.exercise == "plank")).all()
    assert [(r.seconds, r.reps, r.weight_lb) for r in rows] == [(45, None, None), (40, None, None)]
    assert "every hold reaches 60 s" in c.get("/do/gym2?opt_core=Plank").text


def test_gym_option_switch_starts_fresh(c):
    page = c.get("/do/gym1?opt_squat_pattern=Hack%20squat").text
    assert "<option selected>Hack squat</option>" in page
    assert c.post("/do/gym1/gym", data={"squat_pattern_option": "Nope"}).status_code == 400


def test_delete_ride_removes_mission_and_xp(c):
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import Mission, Ride

    c.post("/do/run1/cardio", data={"minutes": "25"})
    with get_sessionmaker()() as db:
        rid = db.query(Ride).one().id
    c.post(f"/ride/{rid}/delete")
    assert xp() == 0
    with get_sessionmaker()() as db:
        assert db.query(Mission).count() == 0


def test_pain_flag_then_clear(c):
    c.post("/do/run1/cardio", data={"minutes": "20", "pain": "left shin"})
    assert "You flagged pain" in c.get("/").text
    c.post("/pain/clear")
    assert "You flagged pain" not in c.get("/").text


def test_week_bonus_when_checklist_done(c):
    d = WED_WEEK1
    for key in ("run1", "run2", "run3"):
        c.post(f"/do/{key}/cardio", data={"minutes": "25", "day": d.isoformat()})
    for key in ("ride_easy", "ride_long"):
        c.post(f"/do/{key}/cardio", data={"minutes": "45", "day": d.isoformat()})
    for key in ("gym1", "gym2", "gym3"):
        c.post(f"/do/{key}/gym", data={"day": d.isoformat()})
    assert xp() == 3 * 100 + 100 + 150 + 3 * 100 + 100  # long ride is a key session; week bonus


def test_missed_runs_repeat_the_level(c, monkeypatch):
    from gigalegs import services

    week3 = date(2026, 11, 11)
    monkeypatch.setattr(services, "today", lambda: week3)
    html = c.get("/").text
    assert "Runs repeat Week 1" in html and "Easy jog, 10 min" in html
