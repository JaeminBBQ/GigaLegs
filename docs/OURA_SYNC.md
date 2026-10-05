# Oura Ring Sync

> **Status: deferred (D19).** Logging is manual for now (`docs/LOGGING.md`). This design is kept for later; don't build it until the board says so.

The athlete wears an Oura ring all day and night, and probably on bike rides. The Apple Watch is mostly worn during lifting. Oura adds what the watch doesn't cover: **overnight HRV, resting HR, sleep, temperature deviation, a readiness score**, all-day HR, and ring-detected workouts (rides without the watch).

## How the data gets here
Oura's cloud API v2, pulled **server-side** (no iOS work needed). Personal Access Tokens were deprecated in December 2025, so we use **OAuth 2.0 Authorization Code**:
- Authorize: `https://cloud.ouraring.com/oauth/authorize` · Token: `https://api.ouraring.com/oauth/token`
- Scopes: `daily heartrate workout personal`
- The user registers an OAuth application in the Oura developer portal and puts `OURA_CLIENT_ID` / `OURA_CLIENT_SECRET` in `.env`. Local redirect URI: `http://localhost:8000/oauth/oura/callback`.
- Settings page has a "Connect Oura" button → consent → the callback stores the access and refresh tokens in the DB (per `user_id`; never logged). It refreshes on 401 or before expiry.
- The API needs an active Oura membership (a lapsed membership returns 403).
- An unapproved Oura app can connect at most 10 users. That's fine locally; a public hosted GigaLegs would need Oura's approval (D8).

## What we pull (T014)
| Endpoint (`/v2/usercollection/…`) | Fields we keep | Used for |
|---|---|---|
| `daily_readiness` | day, score, temperature_deviation, contributors (hrv_balance, resting_heart_rate, recovery_index, sleep_balance) | Readiness panel (advisory, D17) |
| `sleep` (periods; keep `type == "long_sleep"`) | day, total_sleep_duration, average_hrv, lowest_heart_rate, average_heart_rate | Sleep hint, HRV/RHR trend |
| `daily_sleep` | day, score | Sleep hint |
| `workout` | id, activity, start_datetime, end_datetime, calories, distance, source | Rides when the watch wasn't worn |
| `heartrate` | timestamp, bpm, source (only fetched for workout windows) | Zone check for ring-only rides |

Pull schedule: on server start, every 2 hours while running, and the "Sync now" button. The first pull backfills 60 days. Use `start_date` / `end_date` with `next_token` pagination. Upsert by Oura `id` (or by `day` for daily docs). Tests use recorded/mocked responses only; never the network.

## One activity, many sources: merge rules (D16, engine T015)
A single ride can arrive three times: an Apple Watch workout (HealthKit), an Oura workout (API), and Oura's copy in Apple Health (if Oura→Health sharing is on). All raw records land in `external_activities`. The **pure engine** turns them into rides and session attachments:
1. **Cluster:** two records are the same activity if they overlap in time by ≥ 50% of the shorter one and their kinds are compatible (cycling↔cycling, strength↔strength, `other`↔anything).
2. **Primary source per cluster:** Apple Watch > Oura API > any other HealthKit source. Fields the primary lacks are filled from the next source (e.g. Oura HR for a watch workout that has no HR).
3. **Ride distance when no source has it** (ring-only rides usually have none): if the athlete marks the ride as a commute, use the measured route distance (in or home = one way; round = both). Otherwise the ride logger asks for miles.
4. **Sleep:** Oura is primary; the HealthKit sleep union is the fallback for nights without Oura data.
5. **Bodyweight:** HealthKit (scale/manual entries) only.

## Best data for rides (athlete tip)
If the watch is on a ride, start an **Outdoor Cycle** workout on it: it records GPS distance and elevation, which the ring can't. If only the ring is on, the ride is still detected and its HR still checks the Zone 1–2 rule; just confirm "commute in / home" and the miles fill in.
