# Logging

Three ways in, one database (`data/gigalegs.db`):
1. **The web app** (`uv run gigalegs serve`): tap through the day's sets on Today, or use the **Quick log** box.
2. **Message Claude** in chat. Claude saves it with `uv run gigalegs log "<text>" --save`.
3. **Terminal:** the same `gigalegs log` command.

The Quick log box, the CLI, and Claude all read the shorthand below (parser: `engine/shorthand.py`).

**Free-form is always fine** ("did the squats at 100 for 2 sets of 7, felt easy, RDLs a bit harder"). The shorthand below is just faster to type on a phone and unambiguous.

## Shorthand

### Lifting session
```
lift [date] [onramp A|B|C | week N] [day N]
<exercise> <weight>x<reps>x<sets> @<rpe>     # identical sets
<exercise> <weight>x<reps> @<rpe>, <weight>x<reps> @<rpe>   # sets that differ
<exercise> <seconds>s x<sets>                 # timed holds
ready <soreness> <sleep> <energy>              # optional pre-session check-in, each 0–10
note <anything>
```
Everything in `[]` is optional:
- The date defaults to today and accepts `10/5` or `mon`.
- Phase, week, and day are inferred from the schedule in `program/private/onramp-sessions.md`.
- Bodyweight exercises can drop the weight: `situp x10x3 @6`.

**Flags**, on the same line as a set:
- `!form`: form broke down on that set (it doesn't count toward progression).
- `!pain <where>`: pain on that set, e.g. `!pain left knee`. Claude follows up.
- `amrap`: the set was as many reps as possible.

**Exercise aliases:**
| Type | Means |
|---|---|
| `psq` | high-bar paused squat |
| `sq` | back squat |
| `dl` | deadlift |
| `ddl` | deficit deadlift |
| `rdl` | Romanian deadlift |
| `row` / `prow` | barbell row / Pendlay row |
| `situp` / `dsitup` | weighted sit-up / decline weighted sit-up |
| `bext` / `pbext` | back extension / paused back extension |
| `plank` / `splank` / `hipdrop` | plank / side plank / side plank hip drop |

Any other name is fine; Claude maps it.

### Ride
```
ride [date] <miles>mi <minutes>min [z1|z2|z3] [in|home|round] [+<feet>ft] [note ...]
```
`in` / `home` / `round` marks it as a commute. If you were wearing the watch or ring, read the miles and minutes off it.

### Morning-after and body
```
sore [date] <0–10>        # next-morning leg soreness (drives the on-ramp gate)
bw [date] <lb>            # morning bodyweight
```

## Example
```
lift onramp A day 1
ready 2 7 8
psq 100x7x2 @4
rdl 160x10x2 @5
plank 60s x2
splank 40s x2
note squats felt like warmups, rdl grip fine
```
```
ride sat 8.5mi 42min z2 note marina loop
sore 3
bw 180.6
```

## What Claude does with a log message
1. Converts it to shorthand and saves it via `gigalegs log --save`, which fills in phase, week, and day from the queue. For coaching, `gigalegs export` writes `data/logs/*.jsonl`.
2. Replies with a compact table, **prescribed vs. done**. It flags any set over the RPE cap, missed reps, `!form`, or `!pain`.
3. States what it means, using METHODOLOGY:
   - The on-ramp gate status ("next week: B if soreness ≤ 5 on Wednesday").
   - Progression decisions per lift.
   - XP earned (computed by the engine).
4. If something was misparsed, Claude fixes it (an edit/delete button in History is T018).
5. Once a week (T008), Claude writes a check-in to `data/checkins/`.
