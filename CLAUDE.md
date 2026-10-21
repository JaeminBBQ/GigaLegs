# CLAUDE.md

GigaLegs is a gamified but legitimate training coach: a phone-first web app plus a coach agent, for one athlete (the user). **Pivoting (D27, 2026-10-20)** from the barbell-squat program to full-body gym work + endurance (bike or run) toward a local event, with a short "floor" option for bad days. Goals: be fit and look good, stay consistent. The plan is in `docs/training/` (v2); the app still runs v1 until T020 lands.

## Roles (D26)
- **Claude (builder + coach):** owns product, architecture, implementation, tests, and **all training decisions**. Tracks work in `handoffs/BOARD.md`. No implementer agent; no handoff relay.
- **User (human in the loop):** answers product/training questions, provides athlete data (logs, how sessions felt), does browser/visual/phone testing, manages accounts and secrets, runs all git commits.

## Workflow
1. Work is tracked in `handoffs/BOARD.md`; things the user must do go in `handoffs/HUMAN.md`. Write a task spec in `handoffs/tasks/` only when the work is big enough to need one.
2. Claude implements, then runs `uv run pytest -q` and `uv run ruff check .` itself before calling anything done.
3. When work is done, Claude checks `git status` for leaks and gives the user the exact `git add/commit` command. **The user runs all commits; Claude never commits.**

## Discord notifications (always)
The user may be away from the terminal. Before ending any turn where the user must act (answer a question, run a commit, do a browser test), send:
`python3 tools/notify.py --from claude --kind input "<exactly what to do>"`
Use `--kind done` for finished milestones and `--kind blocked` for blockers. The webhook lives in `.env` (`DISCORD_WEBHOOK_URL`); never print it.

## Source of truth
- `docs/PRODUCT.md`: what we're building, athlete goals and starting point
- `docs/ARCHITECTURE.md`: stack, layout, data model, engine and agent design
- `docs/DECISIONS.md`: decision log (append-only)
- `docs/GAMIFICATION.md`: XP, levels, streaks, badges, commute map
- `docs/training/METHODOLOGY.md`: the training rulebook the engine implements (hard rules)
- `docs/training/SEASON_PLAN.md`: the 2026–27 calendar (half → Tahoe ride → fall marathon)
- `docs/training/BIKE_COMMUTE_PLAN.md`: commute route, safety, bike basics (side quest)
- `docs/training/NUTRITION.md`: slow cut with high protein
- `docs/HOSTING.md`: private hosting via Tailscale on the Pi → Mac mini (D34)
- `docs/LOGGING.md`: manual logging shorthand + what Claude does with a log message
- `docs/WATCH_SYNC.md`, `docs/OURA_SYNC.md`: **deferred** (D19) wearable designs
- `program/private/`: normalized purchased program + concrete on-ramp sessions (gitignored)
- `athlete/PROFILE.md`: **private** personal data (address, bodyweight, maxes); gitignored
- `program/source/`: the purchased program files (read-only)
- `handoffs/BOARD.md`: task status; `handoffs/HUMAN.md`: what's needed from the user

## Logging and coaching from the app's data
- The web app (`uv run gigalegs serve`) is the main way to log. Its DB `data/gigalegs.db` is the source of truth.
- When the user sends a session/ride in chat, convert it to the shorthand (`docs/LOGGING.md`) and save it with `uv run gigalegs log "<text>" --save`, so chat and app logs land in the same place. Reply with the prescribed-vs-done table, decisions, and XP the command prints. Never invent missing numbers: ask.
- To coach (weekly check-in, questions), run `uv run gigalegs export` and read `data/logs/*.jsonl`.

## Hard rules
- **Training safety beats game mechanics.** No feature may reward exceeding prescribed RPE, extra unprescribed volume, skipping deloads, or training through pain. If a game idea conflicts with METHODOLOGY, METHODOLOGY wins.
- **Loads come from the deterministic engine, never from an LLM.** Agents (including an in-app coach) explain and propose; the engine computes. Rule changes go into METHODOLOGY + DECISIONS first, with the user's approval.
- **Never invent athlete numbers.** Unknown 1RM, bodyweight, or program load → leave it null and add a question to `handoffs/HUMAN.md`.
- Don't edit `program/source/`. Normalize into `program/` and document the derivation.
- Pain (joint, sharp) is never "push through". Persistent pain → recommend a professional.
- Never print, log, or commit `.env` contents.
- **The GitHub repo is public (D10).** Personal data (address, bodyweight, maxes, logs) lives only in gitignored `athlete/` and `data/`. The purchased program lives only in gitignored `program/source/` and `program/private/`. Never copy either into committed docs, code, tests, or task specs. Before giving the user a commit command, check `git status` for leaks.
- Build multi-user-ready (D8): `user_id` on user-owned tables, programs as data, no hard-coded athlete.

## Environment notes
- Stack (D3): Python 3.12 via `uv`, FastAPI + Jinja2 + HTMX, SQLite + SQLAlchemy + Alembic, pytest, ruff. System Python is 3.9; always `uv run ...`.
- Code map: `src/gigalegs/engine/` (pure rules), `services.py` (DB glue), `web/` (routes, templates, static), `cli.py`. Tests use `tests/fixtures/fake-program.json`, never the real program.
- Port 8765 is used by LeagueApp; GigaLegs defaults to 8000.
- Units: lb, miles, feet. Store raw; convert only in the UI.
- Git: the user commits. Branch `main`.
