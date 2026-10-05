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
        "/healthz",
        "/manifest.webmanifest",
    ):
        assert c.get(url).status_code == 200, url


def test_today_shows_onramp_plan(app_env):
    html = client().get("/").text
    assert "On-ramp A" in html and "135 lb" in html  # 60% of 225
    assert "45 / side" in html


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


def test_pain_flag_then_clear(app_env):
    c = client()
    c.post("/log/save", data={"text": "lift onramp A day 2\nrow 95x10 @6 !pain left elbow"})
    assert "You flagged pain" in c.get("/").text
    c.post("/pain/clear")
    assert "You flagged pain" not in c.get("/").text


def test_timed_hold_earns_logged_xp(app_env):
    saved = client().post("/log/save", data={"text": "lift\nplank 60s x2"})
    assert "(+10 XP)" in saved.text  # 2 holds x 5, no RPE needed
