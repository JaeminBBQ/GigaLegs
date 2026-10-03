# Product

## What we're building
A coach that makes leg training **fun to show up for** and **hard to screw up**. The game layer (XP, levels, weekly streaks, badges, a commute map) rewards doing the plan as written (see `GAMIFICATION.md`). The coaching layer (deterministic rules engine + Claude as coach) keeps progress efficient and roughly linear, and pulls the brakes when recovery, form, or pain say so (see `training/METHODOLOGY.md`).

Today it's one user (the owner), running locally. It's built so it can later become a hosted app for anyone who trains legs (D8). No social features.

## Athlete goals (priority order)
1. **Squat heavy.** Built through the purchased deadlift-focused program (it includes back squat work), then squat-focused blocks after it.
2. **Bike-commute to work:** Five Ridges (north Sparks) → Sparks Blvd → Veterans Pkwy → South Meadows (south Reno). Estimated ~17–19 mi each way, not measured yet. See `training/BIKE_COMMUTE_PLAN.md`.
3. **Efficient, linear-ish progress** without the week-long soreness wipeouts you get from starting cold at full loads.

## Starting point (2026-10-02)
- Hasn't started the deadlift program or biking yet.
- Tried squatting near the program's numbers and chose to ramp in over a few weeks to avoid heavy DOMS → `training/ONRAMP.md`.
- The program guide says it's meant for lifters with 8+ months of training who know their squat and deadlift 1RMs. The on-ramp bridges that gap.

## Macrocycle (dates approximate)
| Phase | Length | Dates (proposed) | Bike stage |
|---|---|---|---|
| On-ramp A/B/C | 3 wk | 2026-10-05 → 10-25 | 1 |
| Deadlift program | N wk (from the lb sheet) | 2026-10-26 → … | 2 → 5 |
| Peak (last 2–3 wk of program) | | | 5, capped at 2 round trips/wk |
| Deload | 1 wk | | easy rides |
| Squat volume block | 4–6 wk | | 5 |
| Squat strength block | 6–8 wk | | 5 |

## MVP features (phone-first web app)
1. **Today:** the day's session with exact loads (on-ramp scaling applied), plate math, and the readiness check-in (soreness / sleep / energy) that can lighten the session.
2. **Set logger:** weight, reps, RPE, form-OK toggle, pain flag. At most 3 taps per set when you hit the prescription.
3. **Ride logger:** miles, minutes, elevation, commute direction, zone.
4. **Game layer:** XP/level header, weekly streak, badges, and a commute map from Five Ridges to South Meadows.
5. **Progress:** squat/deadlift e1RM charts, weekly ride miles.
6. **Coach:** a weekly check-in. Phase 1: Claude reads exported logs and writes `data/checkins/`. Phase 2: an in-app coach on the Claude API that uses engine functions as tools.

## Later: hosted for anyone (not now)
Accounts, onboarding (enter maxes → pick a template program), original public program templates (never the purchased one, D10), and per-user cost limits on the coach.

## Non-goals
Calorie or food tracking (we only give targets; bodyweight is logged), upper-body programming, social features, and Strava/Garmin sync (maybe later).
