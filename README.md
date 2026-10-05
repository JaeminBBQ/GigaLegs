# GigaLegs

A gamified, no-nonsense leg training coach: web app + agents.
Goals: squat heavy, and bike-commute Five Ridges (Sparks) → South Meadows (Reno).

## Run it
```
uv sync
uv run gigalegs serve          # prints a URL for your phone (same Wi-Fi)
```
On iPhone: open the printed URL in Safari → Share → Add to Home Screen.

Other commands: `uv run gigalegs log "<shorthand>" --save` (log from the terminal),
`uv run gigalegs export` (write `data/logs/*.jsonl` for Claude), `uv run pytest`, `uv run ruff check .`.

Private files (gitignored): `program/private/` (the purchased program), `athlete/` (profile, route),
`data/gigalegs.db` (your logs).

- Orchestrator (Claude): `CLAUDE.md` · Implementer (DeepSeek): `DEEPSEEK.md`
- Product and training docs: `docs/` · Work in flight: `handoffs/BOARD.md`, `handoffs/HUMAN.md`
