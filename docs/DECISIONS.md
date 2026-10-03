# Decision Log

Append-only. When a decision changes, add a new entry that supersedes the old one.

| # | Date | Decision | Why |
|---|---|---|---|
| D1 | 2026-10-03 | Orchestration: Claude plans, reviews, and coaches; DeepSeek implements via `handoffs/` md files; the user relays and runs all git commits | User's standard workflow (`~/Projects/ORCHESTRATOR_PROMPT.md`), same layout as LeagueApp |
| D2 | 2026-10-03 | Loads, progression, and XP come only from the pure `engine/`, never from an LLM | Keeps the coaching legitimate and testable |
| D3 | 2026-10-03 | Stack: Python 3.12/uv, FastAPI + Jinja2 + HTMX, SQLite + SQLAlchemy + Alembic | Proven with DeepSeek on LeagueApp; no JS build; cheap to host |
| D4 | 2026-10-03 | 3-week on-ramp (60/75/90% load, 50/70/100% sets) before program Week 1, gated on soreness ≤ 5 and no joint pain | User wants to avoid a week-long DOMS crater; repeated-bout effect |
| D5 | 2026-10-03 | Game rewards compliance, not volume: no XP above the RPE cap, deloads worth more XP, streaks counted in weeks | Gamification must never push worse training decisions |
| D6 | 2026-10-03 | Progression: 2 misses in a row → −10%; RPE-lift increments +10 lb deadlift-pattern, +5 lb otherwise | Turns METHODOLOGY's "5–10%" and "+5–10 lb" ranges into exact numbers the engine can use |
| D7 | 2026-10-03 | Bike: Zone 1–2 only, staged build to commuting, ride one way into work first, ≤ 2 round trips/wk during peak | Program guide: low-intensity cardio, tapered near the end |
| D8 | 2026-10-03 | Local-hosted single user now, built **multi-user-ready**: every user-owned table has `user_id`, local mode auto-uses user 1 with no login, auth lives behind one module | The user wants the option to host it later for anyone who trains legs; retrofitting `user_id` later is painful |
| D9 | 2026-10-03 | Maintain bodyweight through the on-ramp + program; slow cut (0.5–1 lb/wk) afterwards during the deload + squat volume block | The program forbids a deficit; the user would like to lose a few lb |
| D10 | 2026-10-03 | The repo is public: the purchased program, personal data (`athlete/`), and logs are gitignored. The engine is program-agnostic; a hosted build ships only original program templates, and users can import their own private program | Paid content can't be redistributed; the user's address and body data shouldn't be public |
