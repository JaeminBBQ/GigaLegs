# Task Board

| ID | Task | Owner | Status | Depends on |
|---|---|---|---|---|
| T001 | Scaffold (uv, ruff, pytest) + pure engine core: rounding/plates, on-ramp scaling + gate, e1RM, progression, readiness, XP/levels | DeepSeek | ready | — |
| T002 | Normalize the program lb sheet → `program/private/deadlift-program.json`; write the real on-ramp A/B/C sessions | Claude | blocked (HUMAN.md: lb sheet, maxes, training days) | — |
| T003 | Config (`GIGALEGS_MODE`), multi-user-ready DB models + Alembic migration, JSONL log import/export CLI | DeepSeek | planned | T001 |
| T004 | Web MVP: Today (prescription + plates + readiness), set logger, ride logger, XP header; PWA manifest | DeepSeek | planned | T002, T003 |
| T005 | Streaks, badges, commute map | DeepSeek | planned | T004 |
| T006 | Record the measured route in `athlete/PROFILE.md`; pick commute weekdays | Claude + user | blocked (HUMAN.md: route miles, commute days) | — |
| T007 | Nutrition targets incl. ride days (`docs/training/NUTRITION.md`) | Claude | done | — |
| T008 | Weekly check-in procedure (Phase 1 coach) → `data/checkins/` | Claude | planned | T002 |
| T009 | Phone access on the home network (local mode); public hosting + auth is a later milestone (D8) | Claude + user | planned | T004 |
| T010 | In-app coach (Claude API, engine as tools) | DeepSeek | planned | T004, T008 |

Only `ready` tasks have full specs in `tasks/`. Claude writes the next spec after reviewing the previous task, so later specs can build on what was learned.
