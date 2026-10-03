# Handoff Protocol

How work moves between Claude (orchestrator + coach), DeepSeek (implementer, running in Claude Code), and the user (relay, git commits, athlete data, human testing).

```
Claude writes tasks/TNNN-*.md and points TO_DEEPSEEK.md at it
        │
        ▼  user → DeepSeek:  "read handoffs/TO_DEEPSEEK.md"
DeepSeek implements, writes reports/TNNN-report.md, overwrites TO_CLAUDE.md
        │
        ▼  user → Claude:    "read handoffs/TO_CLAUDE.md"
Claude reviews the diff and re-runs the acceptance checks → done, or writes a fix task
        │
        ▼  Claude → user:    exact git commit command to run
```

## Files
| File | Written by | Purpose |
|---|---|---|
| `TO_DEEPSEEK.md` | Claude | DeepSeek's single entry point: the current task plus any notes. Overwritten per task. |
| `TO_CLAUDE.md` | DeepSeek | Latest status update for Claude. Overwritten per task. |
| `tasks/TNNN-slug.md` | Claude | Full task spec. DeepSeek never edits it. |
| `reports/TNNN-report.md` | DeepSeek | Full report (template: `REPORT_TEMPLATE.md`). Kept as history. |
| `BOARD.md` | both | Task statuses. DeepSeek only sets its own task to `review`. |
| `HUMAN.md` | Claude | Things Claude needs the user to do, decide, or report (including training feedback). |

## Statuses
`planned` (outline only) → `ready` (spec written) → `in-progress` → `review` (DeepSeek finished) → `done` (Claude verified; the user commits), or `rework` (a fix task was written). `blocked` = waiting on a question or on the user.

## Notifications
Both agents ping the user on Discord via `python3 tools/notify.py` whenever a task finishes or the user's input is needed (details in CLAUDE.md / DEEPSEEK.md).

## Git
The user runs all commits. After verifying a task, Claude gives the exact command, e.g. `git add -A && git commit -m "T001: scaffold and engine core"`. Neither agent commits.

## Task spec format (Claude)
A header (owner, depends on, size), then **Goal**, **Read first**, **Scope** (do / do not), **Acceptance criteria** (runnable commands and checks, never "looks good"), and **Report**.
