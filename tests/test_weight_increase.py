"""Weight-increase XP (GAMIFICATION v2, T024): rewards the double-progression win only."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from gigalegs.engine import badges as B
from gigalegs.engine import season as SE
from gigalegs.engine import xp as X

WED_WEEK1 = date(2026, 10, 28)  # week 1: cap RPE 7, leg press 3 × 8–12
REPS = (8, 12)
CAP = 7.0


# ---------- engine ----------


def _agree(sets: list[SE.SetPerf], pain: bool = False) -> bool:
    """earned_increase and next_gym_weight on the same input; they must agree."""
    earned = SE.earned_increase(sets, REPS, CAP, pain=pain)
    nxt, _ = SE.next_gym_weight([sets], REPS, CAP, 10)
    w = max(((s.weight or 0) for s in sets if s.reps is not None), default=0) or None
    if not pain:
        assert earned == (nxt is not None and w is not None and nxt > w)
    return earned


CASES = {
    "top_at_cap": ([SE.SetPerf(200, 12, 7)] * 3, True),
    "top_under_cap": ([SE.SetPerf(200, 12, 6), SE.SetPerf(200, 13, 6.5)], True),
    "one_over_cap": ([SE.SetPerf(200, 12, 7), SE.SetPerf(200, 12, 7.5)], False),
    "one_mid_range": ([SE.SetPerf(200, 12, 7), SE.SetPerf(200, 11, 7)], False),
    "below_range": ([SE.SetPerf(200, 12, 7), SE.SetPerf(200, 6, 7)], False),
    "missing_rpe": ([SE.SetPerf(200, 12, 7), SE.SetPerf(200, 12, None)], False),
    "form_flagged": ([SE.SetPerf(200, 12, 7), SE.SetPerf(200, 12, 7, form_ok=False)], False),
    "bodyweight": ([SE.SetPerf(None, 12, 7)] * 3, False),
    "no_sets": ([], False),
}


@pytest.mark.parametrize("name", CASES)
def test_earned_increase_matches_next_weight(name):
    sets, want = CASES[name]
    assert _agree(sets) is want


def test_pain_blocks_increase_xp():
    assert not SE.earned_increase([SE.SetPerf(200, 12, 7)] * 3, REPS, CAP, pain=True)


def test_session_result_is_public():
    assert SE.session_result([SE.SetPerf(200, 12, 7)], 8, 12, 7) == "top"
    assert X.WEIGHT_INCREASE == 25


def test_progress_machine_badge_at_25():
    facts = B.BadgeFacts(False, 0, 0.0, 0, 0, None, 1, weight_increases=24)
    assert "progress_machine" not in B.earned(facts)
    facts = B.BadgeFacts(False, 0, 0.0, 0, 0, None, 1, weight_increases=25)
    assert "progress_machine" in B.earned(facts)


def test_v2_level_titles():
    assert X.level_title(1) == "Rookie"
    assert X.level_title(100) == "Giga"


# ---------- flows ----------


@pytest.fixture
def c(app_env, monkeypatch):
    from gigalegs import services
    from gigalegs.web.app import app

    monkeypatch.setattr(services, "today", lambda: WED_WEEK1)
    return TestClient(app)


def _form(reps=("12", "12", "12"), rpe=("7", "7", "7"), w="200", **extra):
    form = {"squat_pattern_option": "Leg press", "day": WED_WEEK1.isoformat(), **extra}
    for i, (r, e) in enumerate(zip(reps, rpe, strict=True), 1):
        form.update(
            {f"squat_pattern_w{i}": w, f"squat_pattern_r{i}": r, f"squat_pattern_rpe{i}": e}
        )
    return form


def _inc_events():
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import XpEvent

    with get_sessionmaker()() as db:
        q = db.query(XpEvent).filter(XpEvent.source == "weight_increase")
        return [(e.amount, e.ref) for e in q]


def _session_and_set():
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import SetLog

    with get_sessionmaker()() as db:
        s = db.query(SetLog).order_by(SetLog.id).first()
        return s.session_id, s.id


def test_top_reps_under_cap_awards_25_and_shows_it(c):
    r = c.post("/do/gym1/gym", data=_form())
    assert "+25 · weight increase earned" in r.text and "Leg press" in r.text
    sid, _ = _session_and_set()
    assert _inc_events() == [(25, f"inc-{sid}-leg_press")]


@pytest.mark.parametrize(
    "form",
    [
        _form(rpe=("7", "7", "8")),  # over the week-1 cap
        _form(reps=("12", "12", "7")),  # below the range
        _form(rpe=("7", "7", "")),  # missing RPE
        _form(squat_pattern_formbad="1"),  # form flagged
        _form(pain="knee"),  # pain
    ],
    ids=["over_cap", "below_range", "missing_rpe", "form_flagged", "pain"],
)
def test_non_qualifying_sessions_award_nothing(c, form):
    r = c.post("/do/gym1/gym", data=form)
    assert _inc_events() == []
    assert "weight increase earned" not in r.text


def test_repeat_logging_and_push_do_not_double_award(c):
    c.post("/do/gym1/gym", data=_form())
    c.post("/do/gym1/gym", data=_form())  # same slot again: unplanned, no award
    assert len(_inc_events()) == 1
    # push: +1 set on an upper-body exercise; still one award per exercise per session
    push = {"horizontal_press_option": "DB bench", "push": "1"}
    push["day"] = (WED_WEEK1 + timedelta(days=1)).isoformat()
    for i in range(1, 5):
        push.update(
            {f"horizontal_press_w{i}": "50", f"horizontal_press_r{i}": "12"}
            | {f"horizontal_press_rpe{i}": "7"}
        )
    c.post("/do/gym3/gym", data=push)
    refs = [ref for _, ref in _inc_events()]
    assert len(refs) == len(set(refs)) == 2
    assert sum(r.endswith("-db_bench") for r in refs) == 1


def test_delete_session_removes_increase_xp(c):
    c.post("/do/gym1/gym", data=_form())
    sid, _ = _session_and_set()
    c.post(f"/session/{sid}/delete")
    assert _inc_events() == []


def test_edit_set_reevaluates_increase(c):
    c.post("/do/gym1/gym", data=_form())
    sid, setid = _session_and_set()
    url = f"/session/{sid}/edit-set/{setid}"
    c.post(url, data={"weight": "200", "reps": "12", "rpe": "8"})  # now over the cap
    assert _inc_events() == []
    c.post(url, data={"weight": "200", "reps": "12", "rpe": "7"})  # back under: earned again
    assert _inc_events() == [(25, f"inc-{sid}-leg_press")]


def test_progress_machine_granted_once(c):
    from gigalegs import missions as M
    from gigalegs import services as S
    from gigalegs.db import get_sessionmaker
    from gigalegs.models import Badge

    with get_sessionmaker()() as db:
        S.ensure_user(db, 1)
        for i in range(24):
            S.add_xp(db, 1, S.WEIGHT_INCREASE_SOURCE, X.WEIGHT_INCREASE, f"inc-fake{i}-x")
        db.commit()
        assert "progress_machine" not in S.award_badges(db, 1)
    c.post("/do/gym1/gym", data=_form())  # the 25th
    c.post("/do/gym3/gym", data=_form(w="210", day="2026-10-29"))  # 26th: no second badge
    with get_sessionmaker()() as db:
        assert db.query(Badge).filter(Badge.key == "progress_machine").count() == 1
        assert len(M.weight_increases(db, 1, M.latest_session_id(db, 1))) == 1


def test_no_increase_xp_below_engine_target(c):
    """Sandbagging guard: after earning +10 lb, repeating the old weight earns nothing."""
    c.post("/do/gym1/gym", data=_form())
    assert len(_inc_events()) == 1
    c.post("/do/gym3/gym", data=_form(day="2026-10-29"))  # target is now 210, did 200
    assert len(_inc_events()) == 1


def test_no_increase_xp_with_fewer_sets_than_planned(c):
    c.post("/do/gym1/gym", data=_form(reps=("12",), rpe=("7",)))
    assert _inc_events() == []
