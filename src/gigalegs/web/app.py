import json
from datetime import date, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session as Db

from .. import engine as E
from .. import services as S
from ..config import get_settings
from ..db import LOCAL_USER_ID, get_sessionmaker
from ..engine.onramp import ONRAMP_ORDER
from ..engine.shorthand import parse
from ..models import Session, SetLog

HERE = Path(__file__).parent
templates = Jinja2Templates(directory=HERE / "templates")
templates.env.globals["plates"] = S.plates
templates.env.filters["pretty"] = lambda k: k.replace("_", " ").capitalize()
templates.env.filters["num"] = lambda v: (
    "" if v is None else (f"{int(v)}" if float(v).is_integer() else f"{float(v):.1f}")
)
templates.env.globals["is_hold"] = lambda key: key in ("plank", "side_plank")


def route_miles() -> float | None:
    p = get_settings().route_path
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())["features"][0]["properties"].get("miles")
    except (ValueError, KeyError, IndexError):
        return None


app = FastAPI(title="GigaLegs")
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")


def get_db():
    db = get_sessionmaker()()
    try:
        yield db
    finally:
        db.close()


def current_user(db: Db = Depends(get_db)) -> int:
    # Local mode: always the single local athlete (D8). Hosted mode adds auth here only.
    S.ensure_user(db, LOCAL_USER_ID)
    return LOCAL_USER_ID


def render(request: Request, name: str, db: Db, uid: int, **ctx) -> HTMLResponse:
    S.ensure_user(db, uid)
    return templates.TemplateResponse(
        request, name, {"lvl": S.level_info(db, uid), "today": S.today(), **ctx}
    )


def to_int(v: str | None) -> int | None:
    return int(v) if v not in (None, "") else None


def to_float(v: str | None) -> float | None:
    return float(v) if v not in (None, "") else None


def _date(v: str | None) -> date:
    return date.fromisoformat(v) if v else S.today()


# ---------- Today ----------


@app.get("/", response_class=HTMLResponse)
def today_page(request: Request, db: Db = Depends(get_db), uid: int = Depends(current_user)):
    st = S.ensure_user(db, uid)
    open_sess = S.open_session(db, uid)
    if open_sess:
        return RedirectResponse(f"/session/{open_sess.id}", status_code=303)
    d = S.today()
    ctx = S.day_context(db, uid, d)
    rec = E.recommend(ctx)
    plan = S.plan_for(db, uid, S.position(st))
    return render(
        request,
        "today.html",
        db,
        uid,
        st=st,
        rec=rec,
        plan=plan,
        ctx=ctx,
        morning=S.morning(db, uid, d),
        program_missing=S.get_program() is None,
        recent=S.history(db, uid, days=3),
    )


@app.post("/morning")
def morning(
    soreness: str = Form(""),
    bodyweight: str = Form(""),
    day: str = Form(""),
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    d = _date(day)
    if (v := to_int(soreness)) is not None:
        S.log_metric(db, uid, d, "soreness", max(0, min(10, v)))
    if (w := to_float(bodyweight)) is not None:
        S.log_metric(db, uid, d, "bodyweight", w)
    return RedirectResponse("/", status_code=303)


@app.post("/pain/clear")
def pain_clear(db: Db = Depends(get_db), uid: int = Depends(current_user)):
    S.log_metric(db, uid, S.today(), "pain_clear", 1)
    return RedirectResponse("/", status_code=303)


@app.post("/day")
def day_log(
    kind: str = Form(...),
    minutes: str = Form(""),
    note: str = Form(""),
    day: str = Form(""),
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    if kind not in ("recovery", "rest", "smart_rest"):
        raise HTTPException(400, "bad kind")
    S.log_day(db, uid, _date(day), kind, to_int(minutes), note.strip())
    return RedirectResponse("/", status_code=303)


# ---------- Lifting sessions ----------


@app.post("/session/start")
def session_start(
    soreness: int = Form(...),
    sleep: int = Form(7),
    energy: int = Form(7),
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    sess, note = S.start_session(db, uid, S.today(), soreness, sleep, energy)
    url = f"/session/{sess.id}"
    if note:
        from urllib.parse import quote

        url += "?note=" + quote(note)
    return RedirectResponse(url, status_code=303)


def _owned(db: Db, uid: int, sid: int) -> Session:
    sess = db.get(Session, sid)
    if sess is None or sess.user_id != uid:
        raise HTTPException(404)
    return sess


@app.get("/session/{sid}", response_class=HTMLResponse)
def session_page(
    request: Request,
    sid: int,
    note: str = "",
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    sess = _owned(db, uid, sid)
    if sess.status == "done":
        return render(
            request,
            "summary.html",
            db,
            uid,
            summary=S.SessionSummary(sess, S.summarize(sess)),
            done_view=True,
        )
    groups: dict[str, list[SetLog]] = {}
    for s in sess.sets:
        groups.setdefault(s.exercise, []).append(s)
    program = S.get_program()
    notes = {}
    if program:
        for ex in S.plan_for(db, uid, E.Position(sess.phase, sess.week, sess.day)).exercises:
            notes[ex.key] = ex
    return render(
        request, "session.html", db, uid, sess=sess, groups=groups, notes=notes, note=note
    )


@app.post("/session/{sid}/set/{set_id}", response_class=HTMLResponse)
def session_set(
    request: Request,
    sid: int,
    set_id: int,
    weight: str = Form(""),
    reps: str = Form(""),
    seconds: str = Form(""),
    rpe: str = Form(""),
    form_bad: str = Form(""),
    pain: str = Form(""),
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    sess = _owned(db, uid, sid)
    s = db.get(SetLog, set_id)
    if s is None or s.session_id != sess.id:
        raise HTTPException(404)
    S.log_set(
        db,
        s,
        to_float(weight),
        to_int(reps),
        to_int(seconds),
        to_float(rpe),
        form_ok=not form_bad,
        pain=pain.strip() or None,
    )
    return templates.TemplateResponse(
        request, "_set_row.html", {"s": s, "sess": sess, "just_logged": True}
    )


@app.post("/session/{sid}/finish", response_class=HTMLResponse)
def session_finish(
    request: Request,
    sid: int,
    note: str = Form(""),
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    sess = _owned(db, uid, sid)
    if sess.status == "done":
        return RedirectResponse(f"/session/{sid}", status_code=303)
    sess.note = note.strip()
    summary = S.finish_session(db, uid, sess)
    return render(request, "summary.html", db, uid, summary=summary, done_view=False)


@app.post("/session/{sid}/discard")
def session_discard(sid: int, db: Db = Depends(get_db), uid: int = Depends(current_user)):
    sess = _owned(db, uid, sid)
    if sess.status == "open":
        db.delete(sess)
        db.commit()
    return RedirectResponse("/", status_code=303)


# ---------- Quick log, rides ----------


@app.get("/log", response_class=HTMLResponse)
def log_page(request: Request, db: Db = Depends(get_db), uid: int = Depends(current_user)):
    return render(request, "log.html", db, uid)


@app.post("/log/preview", response_class=HTMLResponse)
def log_preview(request: Request, text: str = Form("")):
    return templates.TemplateResponse(
        request, "_preview.html", {"r": parse(text, S.today()), "text": text}
    )


@app.post("/log/save", response_class=HTMLResponse)
def log_save(
    request: Request,
    text: str = Form(""),
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    r = parse(text, S.today())
    if r.errors or r.empty:
        return templates.TemplateResponse(request, "_preview.html", {"r": r, "text": text})
    lines = S.save_parsed(db, uid, r)
    return templates.TemplateResponse(request, "_saved.html", {"lines": lines})


@app.get("/ride", response_class=HTMLResponse)
def ride_page(request: Request, db: Db = Depends(get_db), uid: int = Depends(current_user)):
    return render(request, "ride.html", db, uid, route_miles=route_miles())


@app.post("/ride")
def ride_save(
    miles: float = Form(...),
    minutes: int = Form(...),
    zone: int = Form(2),
    commute: str = Form(""),
    elevation_ft: str = Form(""),
    note: str = Form(""),
    day: str = Form(""),
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    S.log_ride(
        db,
        uid,
        _date(day),
        miles,
        minutes,
        zone,
        commute or None,
        to_int(elevation_ft),
        note.strip(),
    )
    return RedirectResponse("/history", status_code=303)


# ---------- History, insights, path ----------


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, db: Db = Depends(get_db), uid: int = Depends(current_user)):
    return render(request, "history.html", db, uid, days=S.history(db, uid, days=60))


@app.get("/insights", response_class=HTMLResponse)
def insights_page(request: Request, db: Db = Depends(get_db), uid: int = Depends(current_user)):
    data = S.insights(db, uid, S.today())
    return render(request, "insights.html", db, uid, data=data, data_json=json.dumps(data))


PHASES = [
    ("onramp", "On-ramp", 3),
    ("program", "Deadlift program", 10),
    ("deload", "Deload", 1),
    ("squat_block", "Squat block", 6),
]
BIKE_STAGES = [
    (1, "Base", "2-3 easy rides/wk, 60-120 min total, longest 45 min"),
    (2, "Build", "3 rides/wk, 2-3 h total, longest 60-75 min"),
    (3, "Recon + one-way", "1 one-way commute in + 2 easy rides"),
    (4, "First round trips", "1 round trip + 1 one-way"),
    (5, "Regular commuter", "2-3 round trips/wk"),
]


@app.get("/path", response_class=HTMLResponse)
def path_page(request: Request, db: Db = Depends(get_db), uid: int = Depends(current_user)):
    st = S.ensure_user(db, uid)
    start = date.fromisoformat(get_settings().onramp_start)
    program = S.get_program()
    n_weeks = program.n_weeks if program else 10
    steps = [("onramp", w, f"On-ramp {w}") for w in ONRAMP_ORDER]
    steps += [("program", str(i), f"Week {i}") for i in range(1, n_weeks + 1)]
    steps += [("deload", "1", "Deload"), ("squat_block", "1", "Squat block")]
    cur = next((i for i, (p, w, _) in enumerate(steps) if (p, w) == (st.phase, st.week)), 0)
    timeline = []
    for i, (p, w, label) in enumerate(steps):
        eta = max(S.today(), start) + timedelta(weeks=i - cur) if i >= cur else None
        timeline.append(
            {
                "label": label,
                "phase": p,
                "state": "done" if i < cur else "current" if i == cur else "next",
                "eta": eta,
            }
        )
    return render(
        request,
        "path.html",
        db,
        uid,
        st=st,
        timeline=timeline,
        start=start,
        stages=BIKE_STAGES,
        has_route=get_settings().route_path.exists(),
        route_miles=route_miles(),
        checkpoints=S.commute_checkpoints(db, uid, st),
        ride_miles=S.total_ride_miles(db, uid),
        n_weeks=n_weeks,
    )


@app.post("/path/position")
def set_position(
    phase: str = Form(...),
    week: str = Form(...),
    day: int = Form(...),
    db: Db = Depends(get_db),
    uid: int = Depends(current_user),
):
    st = S.ensure_user(db, uid)
    st.phase, st.week, st.day, st.gate_pending = phase, week, day, False
    db.commit()
    return RedirectResponse("/path", status_code=303)


@app.post("/path/bike-stage")
def set_bike_stage(
    stage: int = Form(...), db: Db = Depends(get_db), uid: int = Depends(current_user)
):
    st = S.ensure_user(db, uid)
    st.bike_stage = max(1, min(5, stage))
    db.commit()
    return RedirectResponse("/path", status_code=303)


@app.get("/route.geojson")
def route_geojson():
    p = get_settings().route_path
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="application/geo+json")


@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse(
        {
            "name": "GigaLegs",
            "short_name": "GigaLegs",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#111110",
            "theme_color": "#111110",
            "icons": [{"src": "/static/icon.svg", "sizes": "any", "type": "image/svg+xml"}],
        },
        media_type="application/manifest+json",
    )


@app.get("/healthz")
def healthz():
    return {"ok": True}
