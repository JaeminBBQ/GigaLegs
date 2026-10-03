# Architecture

## Stack (D3)
Python 3.12 via `uv` · FastAPI + Jinja2 server-rendered pages + HTMX for quick set logging · SQLite + SQLAlchemy 2 + Alembic · pytest · ruff. No JS build step. A PWA manifest so the app installs on the phone. Same shape as LeagueApp, which DeepSeek has already shipped successfully.

## Layout
```
src/gigalegs/
  engine/          PURE rules: no I/O, no DB, no clock. Implements METHODOLOGY + GAMIFICATION.
    rounding.py    round_to_increment, plate math
    onramp.py      A/B/C scaling + advance gate
    e1rm.py        RPE-adjusted Epley
    progression.py advance / repeat / reset decisions
    readiness.py   pre-session adjustments
    xp.py          XP per set/session/ride, levels
  models.py, db.py, config.py     (T003)
  web/             FastAPI app, templates, static  (T004)
  cli.py           import/export logs, serve
program/           templates/ (original, public) · private/ (normalized purchased program, gitignored)
athlete/           PROFILE.md: the owner's personal data (gitignored)
data/              SQLite DB, JSONL logs, check-ins (gitignored except READMEs)
tools/notify.py    Discord notifications
```

## Core principle: the engine is the authority on numbers
Every prescribed weight, decision, and XP value comes from `engine/`. The web layer only displays and stores. The coach (Claude now, the in-app LLM later) calls engine functions and explains the results. It never computes loads itself.

## Program as data
`program/private/deadlift-program.json` has weeks → days → exercises → sets, and each set has `{reps, weight_lb | percent_1rm | rpe}` plus `category` (`squat` / `deadlift` / `accessory`). The engine resolves it into pounds from the athlete's 1RMs. Phases wrap it: `onramp` (A/B/C) → `program` (weeks 1..N) → `deload` → `squat_block`.

## Multi-user readiness (D8)
Runs local-only for one person today, but every choice keeps a public hosted version possible:
- **Every user-owned table has `user_id`.** In `GIGALEGS_MODE=local` (the default), requests auto-resolve to user 1 with no login. `hosted` mode will add real auth (sessions + passwords or OAuth) inside one `auth.py` module; nothing else should care which mode it's in.
- **Programs are data owned by a user or marked public.** The purchased program is imported as a private program for user 1 only. A hosted build ships only original templates from `program/templates/` (D10).
- **SQLite now**; SQLAlchemy and Alembic keep a move to Postgres a config change. No SQLite-only SQL.
- **Personal data never goes into code, tests, or fixtures.** Tests use made-up athletes.
- Hosting-only concerns are deferred: email, password reset, rate limits, LLM cost caps per user, and privacy policy.

## Data model (first cut, built in T003)
| Table | Fields |
|---|---|
| `users` | id, display_name, created_at (auth fields added in hosted mode) |
| `athlete` | user_id, bodyweight_lb, squat_1rm_lb, deadlift_1rm_lb, start_date |
| `programs` | id, owner_user_id (null = public template), name, json |
| `phase_state` | user_id, program_id, phase, week, day, started_on |
| `bodyweight_logs` | user_id, date, weight_lb |
| `sessions` | id, user_id, date, phase, week, day, soreness, sleep, energy, status (planned/done/adjusted/smart_rest) |
| `set_logs` | session_id, exercise, category, set_index, prescribed_weight_lb, prescribed_reps, target_rpe, rpe_cap, weight_lb, reps, rpe, form_ok, pain, note |
| `rides` | id, user_id, date, miles, minutes, elevation_ft, commute (null/in/out/round), zone, note |
| `xp_events` | id, user_id, ts, source, amount, ref_id |
| `badges` | user_id, key, earned_on |

`data/logs/*.jsonl` (format in `data/logs/README.md`) is the import/export format. Before the app exists, the user can log there and Claude can coach from it.

## Coach agent
- **Phase 1 (now):** Claude reads JSONL logs, runs the weekly check-in per METHODOLOGY, and writes `data/checkins/YYYY-Www.md`.
- **Phase 2 (T010):** a Coach page backed by the Claude API (default `claude-sonnet-5-5`, Haiku 4.5 for cheap summaries), with tools `get_recent_sessions`, `get_readiness_trend`, `preview_next_week` (engine), and `propose_rule_change` (writes a proposal and never applies it).
