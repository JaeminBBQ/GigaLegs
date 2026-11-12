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
    assert all("6 × (3 min run" in s.detail for s in runs)
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
    # 5 logged + 5 on target per set, +25: all sets at the top of the range under the cap
    assert xp() == 100 + 3 * 10 + 25
    nxt = c.get("/do/gym3").text
    assert "210 lb" in nxt and "+10 lb" in nxt


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
    assert "Runs are at Week 1's level, 2 weeks behind" in html and "10 × (1 min run" in html
    assert "Weeks 1, 2 were short" in html
    assert "The long ride is at Week 1's length" in html


def test_forgiven_week_counts_for_levels(c, monkeypatch):
    from gigalegs import missions, services
    from gigalegs.db import get_sessionmaker

    week3 = date(2026, 11, 11)
    monkeypatch.setattr(services, "today", lambda: week3)
    with get_sessionmaker()() as db:
        services.ensure_user(db, 1)
        assert missions.forgive_week(db, 1, 1) is True
        assert missions.forgive_week(db, 1, 1) is False  # idempotent
        db.commit()
        st = missions.week_state(db, 1, week3)
        assert (st.run_level, st.ride_level) == (2, 2)
        assert st.run_missed == [2] and st.ride_missed == [2]
    html = c.get("/").text
    assert "Week 2 was short" in html and "1 week behind" in html
    assert xp() == 0  # forgiving a week is not an XP event


def test_missed_weeks():
    assert SE.missed_weeks(4, {1, 3}, 23) == [2]
    assert SE.missed_weeks(1, set(), 23) == []
    assert SE.missed_weeks(24, set(), 23) == []


# ---------- regressions: pain, edits, deletes ----------


def _events():
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import XpEvent

    with get_sessionmaker()() as db:
        return [(e.source, e.amount, e.ref) for e in db.query(XpEvent)]


def _gym_form():
    form = {"squat_pattern_option": "Leg press"}
    for i in (1, 2, 3):
        form.update(
            {
                f"squat_pattern_w{i}": "200",
                f"squat_pattern_r{i}": "12",
                f"squat_pattern_rpe{i}": "7",
            }
        )
    return form


def _one(model):
    from gigalegs.db import get_sessionmaker

    with get_sessionmaker()() as db:
        return db.query(model).one().id


def test_pain_after_same_day_clear_still_counts(c):
    c.post("/do/run1/cardio", data={"minutes": "20", "pain": "left shin"})
    c.post("/pain/clear")
    assert "You flagged pain" not in c.get("/").text
    c.post("/do/ride_easy/cardio", data={"minutes": "30", "pain": "right knee sharp"})
    assert "You flagged pain" in c.get("/").text


@pytest.mark.parametrize("kind", ["cardio", "gym"])
def test_pain_on_unplanned_log_counts(c, kind):
    if kind == "cardio":
        c.post("/do/run1/cardio", data={"minutes": "25"})
        c.post("/do/run1/cardio", data={"minutes": "25", "pain": "sharp knee"})  # unplanned
    else:
        c.post("/do/gym1/gym", data=_gym_form())
        c.post("/do/gym1/gym", data={**_gym_form(), "pain": "sharp knee"})  # unplanned
    assert "You flagged pain" in c.get("/").text
    html = c.get("/history").text
    assert "Pain flagged" in html and "Bodyweight" not in html
    c.post("/pain/clear")
    assert "You flagged pain" not in c.get("/").text


def test_edit_season_run_earns_no_v1_ride_xp(c):
    from gigalegs.models import Ride

    c.post("/do/run1/cardio", data={"minutes": "25", "miles": "3"})
    rid = _one(Ride)
    day = WED_WEEK1.isoformat()
    c.post(f"/ride/{rid}/update", data={"miles": "3", "minutes": "25", "zone": "2", "day": day})
    assert xp() == 100
    assert not any(e[0] == "ride" for e in _events())


def test_edit_run_date_moves_mission_and_week_bonus(c):
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import Mission, Ride

    d = WED_WEEK1
    for key in ("run1", "run2", "run3", "ride_easy", "ride_long"):
        c.post(f"/do/{key}/cardio", data={"minutes": "45", "day": d.isoformat()})
    for key in ("gym1", "gym2", "gym3"):
        c.post(f"/do/{key}/gym", data={"day": d.isoformat()})
    assert any(e[2] == "week-1" for e in _events())
    with get_sessionmaker()() as db:
        rid = db.query(Ride).order_by(Ride.id).first().id
    newd = d + timedelta(days=7)
    c.post(
        f"/ride/{rid}/update",
        data={"miles": "0", "minutes": "45", "zone": "2", "day": newd.isoformat()},
    )
    with get_sessionmaker()() as db:
        m = db.query(Mission).filter(Mission.ref == f"ride-{rid}").one()
        assert (m.date, m.plan_week) == (newd, 2)
    assert not any(e[2] == "week-1" for e in _events())  # week 1 is no longer complete


def test_edit_season_set_adds_no_session_bonus(c):
    from gigalegs.models import SetLog

    c.post("/do/gym1/gym", data=_gym_form())
    before = xp()
    from gigalegs.db import get_sessionmaker

    with get_sessionmaker()() as db:
        s = db.query(SetLog).first()
        sid, setid = s.session_id, s.id
    c.post(f"/session/{sid}/edit-set/{setid}", data={"weight": "200", "reps": "12", "rpe": "7"})
    assert xp() == before
    assert not any(e[0] == "session" for e in _events())


def test_repeated_gym_slot_earns_no_set_xp(c):
    c.post("/do/gym1/gym", data=_gym_form())
    first = xp()
    c.post("/do/gym1/gym", data=_gym_form())  # same slot again: extra, unprescribed volume
    assert xp() == first


def test_week_bonus_revoked_for_later_weeks(c, monkeypatch):
    """Deleting a week-7 run drops week 8's run level, so week 8 is no longer complete."""
    from gigalegs import missions, services
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import Ride

    with get_sessionmaker()() as db:
        services.ensure_user(db, 1)
        for w in range(1, 7):
            missions.forgive_week(db, 1, w)
        db.commit()
    wk7, wk8 = date(2026, 12, 9), date(2026, 12, 16)
    for k in ("run1", "run2"):
        c.post(f"/do/{k}/cardio", data={"minutes": "25", "day": wk7.isoformat()})
    monkeypatch.setattr(services, "today", lambda: wk8)
    with get_sessionmaker()() as db:
        keys = [s.key for s in missions.week_state(db, 1, wk8).slots]
    for k in keys:
        kind = "gym" if k.startswith("gym") else "cardio"
        c.post(f"/do/{k}/{kind}", data={"minutes": "25", "day": wk8.isoformat()})
    assert any(e[2] == "week-8" for e in _events())
    with get_sessionmaker()() as db:
        rid = db.query(Ride).filter(Ride.date == wk7).first().id
    c.post(f"/ride/{rid}/delete")
    with get_sessionmaker()() as db:
        assert not missions.week_state(db, 1, wk8).complete
    assert not any(e[2] == "week-8" for e in _events())


def test_history_labels_internal_metrics(c):
    from gigalegs import missions, services
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import Metric

    c.post("/pain/clear")
    with get_sessionmaker()() as db:
        services.ensure_user(db, 1)
        missions.forgive_week(db, 1, 2)
        db.commit()
        fid = db.query(Metric).filter(Metric.kind == "level_forgive").one().id
    html = c.get("/history").text
    assert "Bodyweight" not in html
    assert "Pain cleared" in html and "Week 2 counted as done for levels" in html
    assert f"/metric/{fid}/delete" not in html
    c.post(f"/metric/{fid}/delete")
    with get_sessionmaker()() as db:
        assert missions.forgiven_weeks(db, 1) == {2}


def test_floor_regains_xp_when_other_mission_deleted(c):
    from gigalegs.models import Ride

    c.post("/do/run1/cardio", data={"minutes": "25"})
    c.post("/floor", data={"option": "walk"})
    assert xp() == 100
    c.post(f"/ride/{_one(Ride)}/delete")
    assert xp() == 30  # a floor-only day earns the floor


def test_push_bonus_reawarded_after_delete(c):
    from gigalegs.models import Ride

    c.post("/do/ride_easy/cardio", data={"minutes": "40", "push": "1"})
    c.post("/do/gym1/gym", data={"push": "1"})
    c.post("/do/gym2/gym", data={"push": "1"})  # 3rd push: no bonus
    c.post(f"/ride/{_one(Ride)}/delete")
    assert sum(1 for e in _events() if e[0] == "push") == 2


# ---------- D38 ----------


def test_week_run_slots_lock_once_a_run_is_logged(c, monkeypatch):
    """A backdated earlier week can't swap this week's run slots under done runs."""
    from gigalegs import missions, services
    from gigalegs.db import get_sessionmaker

    with get_sessionmaker()() as db:
        services.ensure_user(db, 1)
        for w in range(1, 7):
            missions.forgive_week(db, 1, w)
        db.commit()
    wk7, wk8 = date(2026, 12, 9), date(2026, 12, 16)
    monkeypatch.setattr(services, "today", lambda: wk8)
    c.post("/do/run1/cardio", data={"minutes": "25", "day": wk8.isoformat()})
    c.post("/do/run2/cardio", data={"minutes": "25", "day": (wk8 + timedelta(2)).isoformat()})
    for k, dd in (("run1", wk7), ("run2", wk7 + timedelta(2))):
        c.post(f"/do/{k}/cardio", data={"minutes": "25", "day": dd.isoformat()})
    with get_sessionmaker()() as db:
        st = missions.week_state(db, 1, wk8)
        keys = {s.key for s in st.slots}
        assert st.run_level == 7  # frozen at the first run's level
        assert sum(1 for k in st.done if k in keys) == 2


def test_pain_holds_the_next_gym_weight():
    hi = SE.SetPerf(200, 12, 7, True)
    hurt = SE.SetPerf(200, 12, 7, True, pain=True)
    assert SE.next_gym_weight([[hi, hi, hi]], (8, 12), 8, 10)[0] == 210
    w, note = SE.next_gym_weight([[hi, hi, hurt]], (8, 12), 8, 10)
    assert w == 200 and "Pain" in note
    assert not SE.earned_increase([hi, hi, hurt], (8, 12), 8)


def test_taper_jump_risk():
    all_done = set(range(1, 30))
    assert SE.taper_jump_risk(20, all_done, 23) == 0
    assert SE.taper_jump_risk(20, all_done - {3, 9}, 23) == 0  # 2 behind: taper is below that
    assert SE.taper_jump_risk(20, all_done - {3, 9, 15}, 23) == 3
    assert SE.taper_jump_risk(25, all_done - {3, 9, 15}, 23) == 3  # still flagged in the taper
    assert SE.taper_jump_risk(17, all_done - {3, 9, 15}, 23) == 0  # too early to call
    assert SE.taper_jump_risk(27, all_done - {3, 9, 15}, 23) == 0  # after the race


def test_taper_warning_on_today(c, monkeypatch):
    from gigalegs import services

    monkeypatch.setattr(services, "today", lambda: date(2027, 3, 10))  # week 20, no runs ever
    assert "weeks behind on runs with the half coming up" in c.get("/").text
