# Logs

How to log (the shorthand you send Claude): `docs/LOGGING.md`. Files here are gitignored (private).

Source of truth for training history until the app exists (afterwards, the app exports here).
One JSON object per line. Append only; fix mistakes by appending a correction with `"corrects": "<id>"`.

## `lifts.jsonl` — one line per set
```json
{"id":"2026-10-06-sq-1","date":"2026-10-06","phase":"onramp","week":"A","day":1,"exercise":"back_squat","set":1,"weight_lb":135,"reps":5,"rpe":5.5,"form_ok":true,"pain":false,"note":""}
```

## `readiness.jsonl` — one line per lifting session (before training)
```json
{"date":"2026-10-06","soreness":2,"sleep":7,"energy":7}
```

## `rides.jsonl` — one line per ride
```json
{"date":"2026-10-07","miles":8.2,"minutes":40,"elevation_ft":120,"commute":null,"zone":2,"note":"Marina loop"}
```
`commute`: `null` | `"in"` | `"out"` | `"round"` (the shorthand `home` is stored as `"out"`).

Exercise keys: lowercase snake_case (`back_squat`, `deadlift`, `deficit_deadlift`, `romanian_deadlift`, …). The normalized program in `program/` defines the full list.

## `soreness.jsonl` — next-morning leg soreness
```json
{"date":"2026-10-06","soreness":3}
```

## `bodyweight.jsonl`
```json
{"date":"2026-10-06","lb":180.6}
```
