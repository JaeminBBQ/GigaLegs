# T012: GigaLegs Sync, a native iOS app (HealthKit → server)

- **Owner:** DeepSeek
- **Depends on:** the user installing full Xcode (see `handoffs/HUMAN.md`). It does **not** depend on the Python server: you build against the contract plus a stdlib mock server, so this can run before or alongside T003/T011.
- **Size:** moderate–large

## Goal
A small SwiftUI iPhone app that reads Apple Watch workouts, bodyweight, and sleep from HealthKit and sends them to the GigaLegs server exactly as specified in `docs/WATCH_SYNC.md`. Plus a stdlib Python mock server so the whole path can be tested before the real endpoint (T011) exists.

## Read first
1. `DEEPSEEK.md`
2. `docs/WATCH_SYNC.md`: **the contract. Follow it exactly.** If something in it seems wrong or impossible with HealthKit, don't change it; ask in your report.
3. `docs/schemas/health-sync-v1.schema.json`

## Scope
**Do:**

1. **Project** at `ios/GigaLegsSync/`, generated with **XcodeGen** (`project.yml`; `brew install xcodegen` is an allowed dependency). Don't commit the generated `.xcodeproj` (add `ios/**/*.xcodeproj`, `ios/**/xcuserdata/`, and `DerivedData/` to `.gitignore`).
   - iOS deployment target 17.0, SwiftUI app lifecycle, Swift 6 language mode. If strict concurrency becomes a fight, use Swift 5 mode and say so in your report.
   - Targets: `GigaLegsSync` (app) and `GigaLegsSyncTests` (unit tests). **No third-party packages.**
   - Bundle id `com.jaeminbbq.gigalegs.sync`. Leave `DEVELOPMENT_TEAM` empty (the user sets it in Xcode).
   - Entitlements: `com.apple.developer.healthkit` = true, `com.apple.developer.healthkit.background-delivery` = true.
   - Info.plist: `NSHealthShareUsageDescription` ("GigaLegs reads your workouts, heart rate, body weight and sleep to log your training."), `NSLocalNetworkUsageDescription` ("GigaLegs Sync sends your workouts to the GigaLegs server on your home network."), and `NSAppTransportSecurity` → `NSAllowsLocalNetworking` = true. **Read-only**: request no HealthKit write types.

2. **Structure.** Keep HealthKit behind a protocol so almost everything is unit-testable without a device:
   - `Models/`: plain `Codable` DTOs mirroring payload v1 exactly (`SyncPayload`, `WorkoutDTO`, `BodyMassDTO`, `SleepDTO`, `SyncResponse`). Encoding: snake_case keys as in the contract, dates as ISO 8601 strings **with the local UTC offset**, and `null` encoded explicitly for nil optionals (the schema requires the keys to be present).
   - `Health/HealthSource.swift`: a protocol with async methods that return *raw* domain values (not HK types), e.g. `newWorkouts(since anchor) -> (workouts: [RawWorkout], deleted: [String], newAnchor: Data)`, `heartRateSamples(for workout) -> [(Date, Double)]`, `bodyMass(since anchor)`, and `sleepIntervals(from:to:) -> [(start: Date, end: Date, isAsleep: Bool)]`.
   - `Health/HealthKitSource.swift`: the real implementation (`HKAnchoredObjectQuery` for workouts and body mass with persisted anchors; `HKSampleQuery` for HR within the workout's time range; sleep analysis for the backfill window).
   - `Sync/HRBucketer.swift` (**pure**): raw `(Date, bpm)` samples + workout start → `[[Int, Double]]` 10-second buckets (mean per bucket, empty buckets omitted, sorted), plus `avg_hr` / `max_hr` as rounded integers from the raw samples.
   - `Sync/ActivityMapper.swift` (**pure**): HK activity type → `"strength"` (traditionalStrengthTraining, functionalStrengthTraining, coreTraining), `"cycling"` (cycling), `"other"` for the rest.
   - `Sync/SleepAggregator.swift` (**pure**): intervals → one `SleepDTO` per wake date. Merge overlapping *asleep* intervals (union) before summing; key each night by the local date of its last asleep interval's end.
   - `Sync/Units.swift` (**pure**): meters → miles (÷ 1609.344), meters → feet (× 3.28084), kg → lb (× 2.20462262).
   - `Sync/PayloadBuilder.swift` (**pure**): assembles payloads and splits workouts into batches of ≤ 100.
   - `Sync/SyncClient.swift`: `URLSession`-based, injectable for tests (custom `URLProtocol` stub). It sends `Authorization: Bearer`, maps 200 / 401 / 422 / other to a typed result.
   - `Sync/AnchorStore.swift`: persists HealthKit anchors (UserDefaults is fine) and **only advances them after a 2xx** for the batch that included those samples.
   - `Sync/SyncCoordinator.swift`: one sync at a time (an actor). The first sync backfills 60 days. It records the last sync time, counts, and last error.
   - `Settings/`: server URL in UserDefaults, token in the **Keychain** (never UserDefaults, never logged).

3. **UI**: one simple screen.
   - Fields: server URL, token (secure field), and a "Connect Health" button (requests authorization).
   - Buttons: "Test connection" (GET `/api/v1/health/ping`) and "Sync now".
   - Status: last sync time, the counts from the last response, the last error in plain language.
   - Sync automatically when the app becomes active. Register an `HKObserverQuery` on workouts with `enableBackgroundDelivery(.immediate)`. If that fails (e.g. Personal Team limits), log it and carry on.

4. **Mock server**: `tools/mock_health_server.py`, Python **stdlib only**.
   - `--port 8000 --token devtoken`. Serves `GET /api/v1/health/ping` and `POST /api/v1/health/sync`.
   - Checks the bearer token (401 if wrong) and the payload against the contract by hand: required keys, enum values, types, units sanity, and ≤ 100 workouts. Returns 422 with `{"error", "path"}` on failure, otherwise 200 with the counts, upserting by uuid in memory so a re-send shows `workouts_new: 0`.
   - Prints a one-line summary per request (never prints the token).
   - `--selftest` validates `ios/GigaLegsSync/Tests/Fixtures/sample-payload.json` plus a few hand-made bad payloads, then exits 0/1.

5. **Tests** (XCTest or Swift Testing), each a named test:
   - HRBucketer: samples at 0 s, 4 s, 12 s → buckets `[[0, mean(first two)], [10, third]]`; no samples → `[]`, with avg/max `nil`; out-of-order samples get sorted.
   - ActivityMapper: the three strength types → strength; cycling → cycling; running → other.
   - SleepAggregator: phone interval 23:00–07:00 overlapping watch interval 23:30–06:30 → 480 min, not 900; "in bed"/"awake" intervals are excluded; two separate nights → two entries with the correct wake dates.
   - Units: 26,876 m → 16.70 mi (±0.01); 187.5 m → 615.2 ft (±0.1); 81.65 kg → 180.0 lb (±0.1).
   - PayloadBuilder: 250 workouts → 3 batches (100/100/50); encoding the fixture DTOs produces JSON equal to `Tests/Fixtures/sample-payload.json` (compare parsed JSON, not strings), and the nil fields are present as `null`.
   - SyncClient + AnchorStore (stubbed URLProtocol): 200 → anchor advances; 401 → anchor unchanged and the error is "check your token"; 500 → anchor unchanged; the request carries the bearer header and `Content-Type: application/json`.
   - The Keychain wrapper round-trips a token (skip the test with a clear message if the simulator Keychain is unavailable).

6. `ios/GigaLegsSync/README.md` (≤ 40 lines): how to generate, build, and run in the simulator; how to run on the user's iPhone (set the team in Signing & Capabilities, trust the developer profile on the phone, the 7-day re-install note); how to run the mock server and point the app at `http://<mac-name>.local:8000`.

**Do not:**
- Write any of the real Python server endpoint, DB, or pairing code (that's T011).
- Read GPS routes or request any HealthKit write permissions.
- Add analytics, crash reporters, or any third-party code.
- Hardcode a server URL other than an empty field with a placeholder, or any token.
- Modify `docs/`, the contract, or the schema. Propose changes in your report instead.
- Run `git commit`.

## Acceptance criteria
1. `cd ios/GigaLegsSync && xcodegen generate` succeeds.
2. `xcodebuild test -project ios/GigaLegsSync/GigaLegsSync.xcodeproj -scheme GigaLegsSync -destination 'platform=iOS Simulator,name=<an installed iPhone simulator>'` passes, with every test listed in Scope §5 present. Put the exact destination you used in the report.
3. `xcodebuild build -project ios/GigaLegsSync/GigaLegsSync.xcodeproj -scheme GigaLegsSync -destination 'generic/platform=iOS' CODE_SIGNING_ALLOWED=NO` succeeds.
4. `python3 tools/mock_health_server.py --selftest` exits 0.
5. **End-to-end in the simulator**: start the mock server, run the app in the simulator, add a sample workout via the simulator's Health app (or skip the data step if that isn't possible and say so), tap "Test connection" (200) and "Sync now" (200). Paste the mock server's log lines into the report.
6. `grep -rn "devtoken\|Bearer [A-Za-z0-9]" ios/GigaLegsSync/Sources` prints nothing (no hardcoded tokens).
7. `git status` shows no `.xcodeproj` or `xcuserdata` files.

## Report
Follow `DEEPSEEK.md` steps 5–8. Include in the report: the Xcode and Swift versions, the simulator used, which HealthKit capabilities compiled without a team, and anything in `docs/WATCH_SYNC.md` that HealthKit made awkward.
