# Task Board

| ID | Task | Owner | Status | Depends on |
|---|---|---|---|---|
| T001 | Scaffold + pure engine core | Claude (D21) | done (superseded the DeepSeek spec) | — |
| T002 | Normalize the lb sheet → `program/private/deadlift-program.json`; real on-ramp sessions | Claude | done | — |
| T017 | Shorthand parser + `gigalegs log` CLI | Claude (D21) | done | T001 |
| T003 | Config, multi-user-ready DB models + Alembic, program loader, JSONL export | Claude (D21) | done | T001 |
| T004 | Web MVP: Today (daily recommendation, plan, plates, readiness), session logger, quick log, ride/recovery/rest, History, Insights charts, Path (timeline, bike stages, route map), PWA | Claude (D21) | done | T003, T017 |
| T005 | Weekly streaks + badges | DeepSeek | done (verified by Claude) | T004 |
| T018 | Edit/delete logged entries from History (sessions, sets, rides, metrics), recomputing XP | DeepSeek | done (verified by Claude 2026-10-20: 114 tests, ruff clean) | T005 |
| T019 | Simple after-the-fact logging (one prefilled form, no readiness prompts) + on-ramp floor (D23, D24) | Claude | on hold: rescope after the pivot (on-ramp floor is obsolete) | T018 |
| T020 | Pivot docs: METHODOLOGY v2, SEASON_PLAN, NUTRITION, GAMIFICATION (D27–D31) | Claude | done, awaiting athlete OK | — |
| T021 | Plan as data: season weeks + gym A/B slots → committed `program/season-2026.json` (original, public) + loader | Claude | planned | T020 |
| T022 | Engine: daily mission (floor/standard/push), slot suggestion + ordering rules, double progression, runs as an activity, daily streak + freezes, v2 XP/badges | Claude | planned | T021 |
| T023 | UI: Today = mission card (2-tap floor), run logger, gym slot picker, season map; shorthand for runs/floors | Claude | planned | T022 |
| D25 | On-ramp accessories by feel (full volume, no cap); gate uses main lifts only | Claude | done | — |
| T006 | Measure + review the commute route | Claude | done (D18, D22) | — |
| T007 | Nutrition targets incl. ride days | Claude | done | — |
| T008 | Weekly check-in procedure (Phase 1 coach) → `data/checkins/` | Claude | planned | first week of logs |
| T009 | Private hosting: app on Mac mini, Tailscale serve on the Pi, app-side login gate (D34, `docs/HOSTING.md`) | Claude + user | gate done; Pi has Tailscale; waiting on login + Mac mini SSH | T004 |
| T010 | In-app coach (Claude API, engine as tools) | Claude | planned | T008 |
| T011–T016 | Wearable sync (watch, Oura, merge) | — | deferred (D19) | — |

Claude does all work (D26). Next: T021–T023 once the athlete OKs the v2 plan. Until then, log by messaging Claude.
