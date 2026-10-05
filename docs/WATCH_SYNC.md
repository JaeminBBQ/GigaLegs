# Apple Watch Sync

> **Status: deferred (D19).** Logging is manual for now (`docs/LOGGING.md`). This design is kept for later; don't build it until the board says so.

The athlete starts an Apple Watch workout before every lift and ride. A small native iOS app, **GigaLegs Sync**, reads those workouts (plus bodyweight and sleep) from HealthKit and POSTs them to the GigaLegs server. The server attaches them to lifting sessions and turns cycling workouts into rides. This contract is owned by Claude; both sides implement exactly this (D11, D12).

```
Apple Watch ──(Apple's own sync)──▶ iPhone Health ──HealthKit──▶ GigaLegs Sync (iOS)
                                                                    │ POST /api/v1/health/sync
                                                                    ▼ Bearer token, JSON v1
                                                      GigaLegs server (Mac on home Wi-Fi now; hosted later)
```

## What the watch gives us (and what it doesn't)
| Data | Used for |
|---|---|
| Strength workout: start/end, duration, active kcal, heart rate | Session duration, effort trend, kcal for nutrition; auto-matched to that day's lifting session |
| Cycling workout: distance, duration, elevation ascended, heart rate | **Creates rides automatically**; HR gives the zone check (METHODOLOGY §5) |
| Body mass (if logged in Health, e.g. a smart scale) | Bodyweight trend (NUTRITION.md) |
| Sleep (asleep minutes per night) | Shown as a hint next to the readiness check-in |

The watch does **not** know sets, reps, weight, or RPE. Those are still logged in the web app. We don't read GPS routes (not needed; privacy).

## Transport
- `POST {server}/api/v1/health/sync` with `Authorization: Bearer <token>` and `Content-Type: application/json`. The body is defined below; the JSON Schema is `docs/schemas/health-sync-v1.schema.json`.
- `GET {server}/api/v1/health/ping` (same auth) → `200 {"ok": true}`. The app's "Test connection" button uses it.
- **Pairing:** `uv run gigalegs pair` (T011) prints the server URL (`http://<mac-name>.local:8000`) and a new random token. The server stores only the token's hash. The user types both into the app, which keeps the token in the iOS Keychain. Hosted mode (later) uses the same flow over HTTPS with a per-user token.
- **Local network:** the app sets `NSAllowsLocalNetworking` (App Transport Security) and `NSLocalNetworkUsageDescription`. Plain HTTP is allowed only to local hosts.
- **Responses:** `200` with counts (below). `401` bad or missing token. `422` schema error, with a JSON body `{"error": "...", "path": "..."}`. Anything other than 2xx → the app keeps its anchors and retries next time.
- **Idempotent:** the server upserts by HealthKit UUID. Re-sending the same payload changes nothing.

## Payload v1
Units are always: lb, mi, ft, kcal, bpm, seconds. Timestamps are ISO 8601 with a UTC offset (e.g. `2026-10-05T17:32:10-07:00`).
```json
{
  "schema_version": 1,
  "client": {"app_version": "1.0", "device_model": "iPhone15,2"},
  "workouts": [
    {
      "uuid": "6F1C…",
      "activity": "strength",
      "hk_activity_type": "traditionalStrengthTraining",
      "start": "2026-10-05T17:32:10-07:00",
      "end": "2026-10-05T18:41:02-07:00",
      "duration_s": 4132,
      "active_kcal": 412.5,
      "distance_mi": null,
      "elevation_ascended_ft": null,
      "indoor": true,
      "avg_hr": 118,
      "max_hr": 163,
      "hr_series": [[0, 92], [10, 95], [20, 101]],
      "source_name": "Apple Watch"
    }
  ],
  "deleted_workout_uuids": [],
  "body_mass": [{"uuid": "A1B2…", "measured_at": "2026-10-05T07:01:00-07:00", "lb": 180.2}],
  "sleep": [{"wake_date": "2026-10-05", "asleep_min": 432}]
}
```
Field rules:
- `activity`: `"strength"` for traditional strength training, functional strength training, and core training; `"cycling"` for cycling; `"other"` for everything else (still sent, and the server ignores it for now). `hk_activity_type` is the Swift enum case name, for debugging.
- `hr_series`: `[seconds_from_start, mean_bpm]`, using 10-second buckets with the mean of the samples in each bucket. Empty buckets are omitted. Empty array if there's no HR.
- `avg_hr` / `max_hr`: integers computed from the raw samples (not the buckets); `null` if there's no HR.
- `distance_mi`: from the workout's cycling distance; `null` for non-cycling. `elevation_ascended_ft`: from `HKMetadataKeyElevationAscended` if present, else `null`. `indoor`: from `HKMetadataKeyIndoorWorkout` if present, else `null`.
- `sleep`: one entry per night, keyed by the local date you woke up. `asleep_min` = total minutes in any *asleep* stage (core, deep, REM, unspecified), with overlapping samples from the phone and watch **merged as a union of intervals**, never double-counted.
- Batching: at most 100 workouts per request. The first sync backfills 60 days.

Response `200`:
```json
{"workouts_new": 1, "workouts_updated": 0, "workouts_deleted": 0, "body_mass_new": 1, "sleep_upserted": 1}
```

## Server-side mapping (T011)
- Every workout is stored raw in `external_activities` (`source = "healthkit"`, `source_name`, `external_id = uuid`). Rides and session attachments are **derived** by the engine's merge rules (`docs/OURA_SYNC.md` → merge rules, D16), so the same ride from the watch and from the Oura ring is counted once.
- Derived strength activity → attached to that day's lifting session (nearest by start time). If no session exists yet, it's attached when the session is logged.
- Derived cycling activity → a `rides` row. The web app asks once per new ride: "Commute? in / home / round / no". Zone compliance comes from the HR series (METHODOLOGY §5).
- A deleted workout → its raw record is removed and derivations are recomputed (removing XP it earned if it was the only source).

## Apple-side constraints (user handles)
- Building to a real iPhone needs full **Xcode** and an Apple ID signed in under Xcode → Settings → Accounts.
- With a free Apple ID (Personal Team), apps installed from Xcode expire after **7 days** and must be re-run from Xcode. A paid Apple Developer membership ($99/yr) removes that and is required for TestFlight/App Store anyway (needed only if GigaLegs is ever hosted for other people).
- If Xcode refuses a HealthKit capability (e.g. background delivery) on a Personal Team, the app still works with sync-on-open plus the "Sync now" button.
