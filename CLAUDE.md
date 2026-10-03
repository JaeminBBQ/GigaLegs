# CLAUDE.md

> **If you are DeepSeek or any implementer agent: stop here and follow `DEEPSEEK.md` instead.**
> This file is for the orchestrator (Claude).

GigaLegs is a gamified but legitimate leg-training coach: a phone-first web app plus a coach agent, for one athlete (the user). Goals: squat heavy, and bike-commute Five Ridges (Sparks) → Sparks Blvd → Veterans Pkwy → South Meadows (Reno), with efficient, linear-ish progress.

## Roles
- **Claude (orchestrator + coach):** owns product, architecture, and **all training decisions** (loads, progression rules, on-ramp, bike plan, check-ins). Writes task handoffs, reviews and verifies DeepSeek's work, and does the hard or judgment-heavy work directly.
- **DeepSeek (implementer):** does simple-to-moderate dev work from task files in `handoffs/tasks/`. Cannot be spawned by Claude; the user relays handoffs manually.
- **User (human in the loop):** relays handoffs, answers product/training questions, provides athlete data (maxes, logs, how sessions felt), does browser/visual/phone testing, manages accounts and secrets, runs all git commits.

## Handoff workflow (see `handoffs/README.md` for the full protocol)
1. Claude writes `handoffs/tasks/TNNN-slug.md`, points `handoffs/TO_DEEPSEEK.md` at it (with any notes), and sets it `ready` in `handoffs/BOARD.md`.
2. Claude pauses and tells the user: say **"read handoffs/TO_DEEPSEEK.md"** to DeepSeek.
3. DeepSeek implements, writes `handoffs/reports/TNNN-report.md`, and overwrites `handoffs/TO_CLAUDE.md`.
4. The user tells Claude "read handoffs/TO_CLAUDE.md". Claude reads it and the report, inspects `git diff`, **runs the acceptance commands itself**, and either marks the task `done` or writes a follow-up task (`TNNNa-fix-...`). Never mark done on DeepSeek's word alone.
5. When a task is done, Claude gives the user the exact `git add/commit` command. **The user runs all commits; Claude and DeepSeek never commit.**

## Discord notifications (always)
The user may be away from the terminal. Before ending any turn where the user must act (hand off to DeepSeek, answer a question, run a commit, do a browser test), send:
`python3 tools/notify.py --from claude --kind input "<exactly what to do>"`
Use `--kind done` for finished milestones and `--kind blocked` for blockers. The webhook lives in `.env` (`DISCORD_WEBHOOK_URL`); never print it.

What goes to DeepSeek: well-specified implementation with clear, runnable acceptance tests. What stays with Claude: decisions, specs, reviews, anything ambiguous, **anything that sets or changes training numbers or rules**, anything touching secrets or the user's personal data.

## Source of truth
- `docs/PRODUCT.md`: what we're building, athlete goals and starting point
- `docs/ARCHITECTURE.md`: stack, layout, data model, engine and agent design
- `docs/DECISIONS.md`: decision log (append-only)
- `docs/GAMIFICATION.md`: XP, levels, streaks, badges, commute map
- `docs/training/METHODOLOGY.md`: the training rulebook the engine implements (hard rules)
- `docs/training/ONRAMP.md`: 3-week lead-in before program Week 1
- `docs/training/BIKE_COMMUTE_PLAN.md`: staged build-up to the commute
- `docs/training/NUTRITION.md`: maintain through the program, slow cut after
- `athlete/PROFILE.md`: **private** personal data (address, bodyweight, maxes); gitignored
- `program/source/`: the purchased program files (read-only)
- `handoffs/BOARD.md`: task status; `handoffs/HUMAN.md`: what's needed from the user

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
- Units: lb, miles, feet. Store raw; convert only in the UI.
- DeepSeek runs inside Claude Code, so it also loads this file and the auto-memory; the redirect at the top matters.
- Git: the user commits. Branch `main`.
