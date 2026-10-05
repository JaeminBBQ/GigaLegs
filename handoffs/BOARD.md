# Task Board

| ID | Task | Owner | Status | Depends on |
|---|---|---|---|---|
| T001 | Scaffold + pure engine core | Claude (D21) | done (superseded the DeepSeek spec) | — |
| T002 | Normalize the lb sheet → `program/private/deadlift-program.json`; real on-ramp sessions | Claude | done | — |
| T017 | Shorthand parser + `gigalegs log` CLI | Claude (D21) | done | T001 |
| T003 | Config, multi-user-ready DB models + Alembic, program loader, JSONL export | Claude (D21) | done | T001 |
| T004 | Web MVP: Today (daily recommendation, plan, plates, readiness), session logger, quick log, ride/recovery/rest, History, Insights charts, Path (timeline, bike stages, route map), PWA | Claude (D21) | done | T003, T017 |
| T005 | Weekly streaks + badges | DeepSeek | done (verified by Claude) | T004 |
| T018 | Edit/delete logged entries from History (sessions, sets, rides, metrics), recomputing XP | DeepSeek | **ready** | T005 |
| T006 | Measure + review the commute route | Claude | done (D18, D22) | — |
| T007 | Nutrition targets incl. ride days | Claude | done | — |
| T008 | Weekly check-in procedure (Phase 1 coach) → `data/checkins/` | Claude | planned | first week of logs |
| T009 | Phone access: LAN works now (`gigalegs serve` prints the URL); keep-it-running + public hosting + auth later (D8) | Claude + user | planned | T004 |
| T010 | In-app coach (Claude API, engine as tools) | DeepSeek | planned | T008 |
| T011–T016 | Wearable sync (watch, Oura, merge) | — | deferred (D19) | — |

**Order of work for DeepSeek:** T018.

Only `ready` tasks have full specs in `tasks/`. Claude writes the next spec after reviewing the previous task.
