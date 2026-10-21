import re

from fastapi.testclient import TestClient


def client():
    from gigalegs.web.app import app

    return TestClient(app)


def test_pages_render(app_env):
    c = client()
    for url in (
        "/",
        "/log",
        "/ride",
        "/history",
        "/insights",
        "/path",
        "/season",
        "/healthz",
        "/manifest.webmanifest",
    ):
        assert c.get(url).status_code == 200, url


def test_today_has_no_soreness_prompt(app_env):
    html = client().get("/").text
    assert "Today's mission" in html and "How sore" not in html


def test_full_onramp_week_and_gate(app_env):
    c = client()
    for day in (1, 2, 3):
        r = c.post(
            "/session/start", data={"soreness": 2, "sleep": 7, "energy": 7}, follow_redirects=False
        )
        assert r.status_code == 303
        sid = int(re.search(r"/session/(\d+)", r.headers["location"])[1])
        page = c.get(f"/session/{sid}").text
        for set_id, form in re.findall(rf'/session/{sid}/set/(\d+)"(.*?)</form>', page, re.DOTALL):
            reps = re.search(r'name="reps"[^>]*value="(\d*)"', form)
            row = c.post(
                f"/session/{sid}/set/{set_id}",
                data={"reps": reps[1] if reps else "", "seconds": "30", "rpe": "5"},
            )
            assert row.status_code == 200 and "Log</button>" not in row.text
        done = c.post(f"/session/{sid}/finish", data={"note": f"day {day}"})
        assert "+" in done.text and "XP" in done.text
    # gate is checked at the next start: soreness 2, clean sets -> week B
    r = c.post(
        "/session/start", data={"soreness": 2, "sleep": 7, "energy": 7}, follow_redirects=True
    )
    assert "On-ramp B" in r.text and "passed" in r.text


def test_gate_repeats_week_when_sore(app_env):
    from gigalegs import services as S
    from gigalegs.db import get_sessionmaker

    with get_sessionmaker()() as db:
        st = S.ensure_user(db, 1)
        st.gate_pending = True
        db.commit()
        msg = S.resolve_gate(db, 1, soreness=6)
        assert "Repeating on-ramp week A" in msg
        assert (S.ensure_user(db, 1).week, S.level_info(db, 1).total) == ("A", 50)


def test_quick_log_preview_and_save(app_env):
    c = client()
    text = "lift\nready 2 7 7\nsq 135x5x2 @6\nplank 45s x2\nride 6mi 30min z2\nsore 3\nbw 180"
    prev = c.post("/log/preview", data={"text": text})
    assert "looks good" in prev.text
    saved = c.post("/log/save", data={"text": text})
    assert "Saved" in saved.text and "ride 6 mi" in saved.text
    hist = c.get("/history").text
    assert "Ride: 6 mi" in hist and "Soreness 3/10" in hist


def test_quick_log_errors_are_shown_not_saved(app_env):
    r = client().post("/log/save", data={"text": "lift\nsq banana"})
    assert "Line 2" in r.text and "Saved" not in r.text


def test_ride_form_and_xp(app_env):
    c = client()
    c.post("/ride", data={"miles": "10", "minutes": "50", "zone": "2", "commute": "in"})
    assert "15 XP" in c.get("/").text  # 10 mi x 1.5 commute


def test_recovery_and_rest(app_env):
    c = client()
    c.post("/day", data={"kind": "recovery", "minutes": "25"})
    assert "Recovery 25 min" in c.get("/history").text


def test_export_jsonl(app_env, tmp_path):
    from gigalegs import services as S
    from gigalegs.db import get_sessionmaker

    client().post("/ride", data={"miles": "5", "minutes": "25", "zone": "2"})
    with get_sessionmaker()() as db:
        counts = S.export_jsonl(db, 1, tmp_path / "logs")
    assert counts["rides.jsonl"] == 1


def test_timed_hold_earns_logged_xp(app_env):
    saved = client().post("/log/save", data={"text": "lift\nplank 60s x2"})
    assert "(+10 XP)" in saved.text  # 2 holds x 5, no RPE needed


def test_gate_ignores_accessories(app_env):
    # D25: a hard accessory set doesn't hold back the week; clean main lifts pass
    from gigalegs import services as S
    from gigalegs.db import get_sessionmaker
    from gigalegs.engine.shorthand import parse

    text = (
        "lift onramp A day 1\nsq 135x5x2 @6\nplank 30s x2\n"
        "lift onramp A day 2\nrow 135x10x5 @9\n"
        "lift onramp A day 3\ndl 190x5x2 @6\n"
    )
    with get_sessionmaker()() as db:
        S.ensure_user(db, 1)
        S.save_parsed(db, 1, parse(text, S.today()))
        st = S.ensure_user(db, 1)
        assert st.gate_pending
        msg = S.resolve_gate(db, 1, soreness=2)
        assert "passed" in msg and S.ensure_user(db, 1).week == "B"


def test_gate_still_blocks_on_accessory_pain(app_env):
    from gigalegs import services as S
    from gigalegs.db import get_sessionmaker
    from gigalegs.engine.shorthand import parse

    text = (
        "lift onramp A day 1\nsq 135x5x2 @6\n"
        "lift onramp A day 2\nrow 135x10 @6 !pain low back\n"
        "lift onramp A day 3\ndl 190x5x2 @6\n"
    )
    with get_sessionmaker()() as db:
        S.ensure_user(db, 1)
        S.save_parsed(db, 1, parse(text, S.today()))
        msg = S.resolve_gate(db, 1, soreness=2)
        assert "Repeating" in msg and "pain" in msg


def test_by_feel_accessory_sets_earn_logged_xp_unrated(app_env):
    from gigalegs import services as S
    from gigalegs.db import get_sessionmaker
    from gigalegs.engine import xp as X
    from gigalegs.engine.shorthand import parse

    with get_sessionmaker()() as db:
        S.ensure_user(db, 1)
        S.save_parsed(db, 1, parse("lift onramp A day 2\nrow 135x10x5\ncurl 30x10", S.today()))
        sets = db.query(S.SetLog).all()
        rows = [s for s in sets if s.exercise == "barbell_row"]
        assert len(rows) == 5 and all(s.rpe_cap is None and s.xp == X.SET_LOGGED for s in rows)
        assert all(s.xp == 0 for s in sets if s.exercise != "barbell_row")  # unprescribed
