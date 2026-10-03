# DEEPSEEK.md: Implementer Guide

You are the **implementer** on this project. Claude is the orchestrator: it writes your tasks, owns decisions, and reviews your work. A human relays between you. You may be running inside Claude Code, in which case `CLAUDE.md` is also loaded; its orchestrator instructions are **not** for you.

## How to work
1. The user will say something like "read handoffs/TO_DEEPSEEK.md". That file names your current task.
2. Read, in order: this file → the task file → every doc the task lists under "Read first".
3. Implement **only** what the task's Scope says. If something outside scope seems necessary, don't do it; put it under "Questions / proposals" in your report.
4. Run every command under "Acceptance criteria" and make them pass.
5. Write the full report to `handoffs/reports/TNNN-report.md` using `handoffs/REPORT_TEMPLATE.md`.
6. **Overwrite `handoffs/TO_CLAUDE.md`** with a short update for Claude (format below). This is how Claude learns you're finished.
7. Set the task's row in `handoffs/BOARD.md` to `review`.
8. **Send a Discord notification** (see below), then tell the user: "Done. Tell Claude: read handoffs/TO_CLAUDE.md".

## Discord notifications (always)
The user isn't watching the terminal. Notify them whenever you finish or need them:
```
python3 tools/notify.py --from deepseek --kind done    "T00N finished: <one line>. Tell Claude: read handoffs/TO_CLAUDE.md"
python3 tools/notify.py --from deepseek --kind input   "<what you need from the user>"
python3 tools/notify.py --from deepseek --kind blocked "T00N blocked: <why>. Tell Claude: read handoffs/TO_CLAUDE.md"
```
Send `input` **before** you stop to ask the user anything. The script reads the webhook from `.env` itself; never open `.env` or print the webhook URL. Don't edit `tools/notify.py`.

### `handoffs/TO_CLAUDE.md` format
```
# To Claude
**Task:** TNNN (slug)
**Status:** done | partial | blocked
**Report:** handoffs/reports/TNNN-report.md
**Updated:** YYYY-MM-DD HH:MM

## In one paragraph
What was built and whether all acceptance criteria pass.

## Needs Claude's attention
Numbered questions, deviations, or blockers. "Nothing" if none.
```

You may use your own subagents. You may not change the task file, `TO_DEEPSEEK.md`, `CLAUDE.md`, `DEEPSEEK.md`, anything in `docs/`, `athlete/`, or `program/source/` (propose changes in your report instead).

## If you get stuck
Don't guess at product, architecture, or **training** decisions. Finish what you can, set status `blocked` or `partial`, and list precise questions in `TO_CLAUDE.md`. A clear question beats a wrong assumption.

## Hard rules
- **Training numbers come from the spec and `docs/training/METHODOLOGY.md` only.** Never invent percentages, increments, thresholds, or XP values; if the spec doesn't give a number, ask.
- No game mechanic may reward exceeding a prescribed RPE, extra unprescribed volume, skipping deloads, or training through pain.
- **The repo is public.** Never read `athlete/`, `program/source/`, or `program/private/` unless your task says to, and never copy their contents into code, tests, fixtures, or your report. Tests use made-up athletes and made-up programs.
- **Never read, print, log, or commit secrets.** Don't open `.env`. Tests must not need network access or real athlete data.
- **Never run `git commit`, `git push`, or change git history.** The user commits. Read-only git (`status`, `diff`) is fine. Don't add dependencies not listed in the task without flagging them in the report.

## Conventions
- Python 3.12 via `uv` (`uv sync`, `uv run pytest`, `uv run ruff check .`). System python is 3.9; don't use it.
- Package: `src/gigalegs/`. Tests: `tests/`. Type hints everywhere.
- `src/gigalegs/engine/` is **pure**: no I/O, no DB, no web, no clock reads (pass dates in). Every rule in METHODOLOGY gets a named unit test.
- Units: pounds, miles, feet. Floats for weights; round only where the spec says.
- Match the style of existing code. Docstrings only where behavior isn't obvious.
