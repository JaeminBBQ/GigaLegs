# Product

## What we're building
A coach that makes training **easy to show up for every day** and **hard to screw up**. Every day has a short floor option, a standard session, and an optional push (`training/METHODOLOGY.md`). The game layer (XP, daily + weekly streaks, badges, a season map) rewards consistency and doing the plan (`GAMIFICATION.md`). The coaching layer (deterministic engine + Claude as coach) progresses weights and running volume safely.

Today it's one user (the owner), running locally, built multi-user-ready (D8). No social features.

## Athlete goals (D27, 2026-10-20)
1. **Consistency:** something every day, morning or evening.
2. **Fit and aesthetic:** full-body gym work for muscle (upper body now in scope), get leaner slowly.
3. **Events:** Biggest Little Half Marathon (Apr 24, 2027) → America's Most Beautiful Bike Ride, 72 mi (Jun 6, 2027) → a fall marathon (Oct 2027). Calendar: `training/SEASON_PLAN.md`.
4. **Bike commute** Five Ridges → South Meadows stays a side quest (`training/BIKE_COMMUTE_PLAN.md`).

## Starting point (2026-10-20)
- Former competitive powerlifter: strong and fit, but with little running base. Details are private (`athlete/PROFILE.md`).
- Did ~2 weeks of the v1 on-ramp (purchased deadlift program) and dropped it for lack of motivation. That history stays in the DB.

## History
v1 (2026-10-02 → 10-20) was a leg-strength app around a purchased deadlift program with a 3-week on-ramp (D4–D25). Superseded by D27.

## Logging now
Manual: message Claude after each session or ride using the shorthand in `LOGGING.md` (free-form works too). Claude logs it, compares it to the prescription, and says what's next.

## MVP features (phone-first web app)
1. **Today:** the day's session with exact loads (on-ramp scaling applied), plate math, and the readiness check-in (soreness / sleep / energy) that can lighten the session.
2. **Quick log:** a text box that accepts the same shorthand you send Claude (`LOGGING.md`), parsed by the engine.
3. **Set logger:** weight, reps, RPE, form-OK toggle, pain flag. At most 3 taps per set when you hit the prescription.
4. **Ride logger:** miles, minutes, elevation, commute direction, zone.
5. **Game layer:** XP/level header, weekly streak, badges, and a commute map from Five Ridges to South Meadows.
6. **Progress:** squat/deadlift e1RM charts, weekly ride miles.
7. **Later (deferred, D19): Apple Watch + Oura sync.** rides are created automatically from watch cycling workouts; lifting sessions get duration/HR/kcal from watch strength workouts; bodyweight and sleep come from Health (`WATCH_SYNC.md`).
8. **Coach:** a weekly check-in. Phase 1: Claude reads exported logs and writes `data/checkins/`. Phase 2: an in-app coach on the Claude API that uses engine functions as tools.

## Later: hosted for anyone (not now)
Accounts, onboarding (enter maxes → pick a template program), original public program templates (never the purchased one, D10), and per-user cost limits on the coach.

## Non-goals
Calorie or food tracking (we only give targets; bodyweight is logged), upper-body programming, social features, and Strava/Garmin sync (maybe later).
