# Training Methodology

This is the rulebook the rules engine implements and Claude (orchestrator/coach) enforces. Changing a rule = user approval + edit this file + an entry in `docs/DECISIONS.md`.

## 1. Sources of truth
- **The purchased program** (`program/source/`) defines exercises, sets, reps, %1RM / RPE targets for each week. Per its own guidance: *stick to the program* — don't swap exercises unless pain forces it, and then use the closest equivalent (e.g. deficit deadlift → Romanian deadlift).
- **This file** defines everything around the program: the on-ramp, autoregulation, recovery gates, cardio interference, and what happens after the program ends.

## 2. Effort: RPE
Standard 1–10 RPE (from the program guide):

| RPE | Meaning |
|---|---|
| 10 | Max effort, no reps left |
| 9 | 1 rep left |
| 8 | 2–3 reps left |
| 7 | 3–5 reps left |
| 6 | 6+ reps left, easy |
| ≤5 | Warm-up |

Every logged working set records the RPE actually felt. RPE 10 is only allowed on prescribed max / AMRAP sets and accessories.

## 3. Load progression ("linear-ish")
Applied per exercise, per week, by the engine:

1. **Hit the reps, form solid, RPE at or under the cap** → next prescribed weight as written (on RPE-based lifts: +10 lb for deadlift-pattern lifts, +5 lb for everything else).
2. **Hit the reps but went over the RPE cap** (the program's max RPE, or the on-ramp cap) → repeat the same weight next time. An unrated set counts as over the cap.
3. **Missed reps, or form broke down noticeably** → repeat the weight; if that happens twice in a row, drop 10% and rebuild.
4. **Never** increase weight when technique breaks down (program rule; also the engine can't see form, so the athlete's "form OK?" toggle on each set gates progression).

e1RM is estimated from top sets with the RPE-adjusted Epley formula: `e1RM = weight × (1 + (reps + (10 − RPE)) / 30)`. Only sets with RPE ≥ 7 count (lower RPE estimates are unreliable).

## 3b. Flexible scheduling (D20)
No fixed weekdays: the athlete trains by feel and availability and wants to do *something* most days.
- **The program is a queue, not a calendar.** Day 1 → Day 2 → Day 3 → (next week) Day 1… A program/on-ramp "week" is complete when its Day 3 is done, however many calendar days that took.
- **Heavy leg days are Day 1 and Day 3** (squat + deadlift pattern). Day 2 is rows/core/back work.
- **Spacing rules** (the program says to spread sessions apart):
  - ≥ 48 h between two heavy leg sessions (72 h preferred).
  - ≥ 20 h between any two lifting sessions.
  - At most 3 program sessions in any rolling 7 days.
- **Every other day is a ride, recovery, or rest.**
  - *Recovery* = 20–40 min walk, mobility, or an easy spin under 30 min. It counts as "doing something".
  - At least one rest or recovery day per rolling 7 days.
  - Never two hard days back to back, where hard = a heavy leg session or a ride over 60 min.
- **Daily recommendation (engine):** the app suggests one of: Lift (next queued day, if the spacing rules and readiness allow), Easy ride (Zone 1–2, length from the bike stage), Recovery, or Rest. Each suggestion comes with its reasons. It's a suggestion: the athlete can pick something else, and logging works the same either way.

## 4. Readiness and recovery gates
Before each lifting session the athlete answers 3 quick questions (0–10): **leg soreness**, **sleep quality**, **overall energy**.

| Condition | Action |
|---|---|
| Soreness ≥ 7 | Do the session at 90% of prescribed loads, cap RPE at target −1. |
| Soreness ≥ 7 two sessions in a row | Coach flags: repeat the week instead of advancing. |
| **Sharp/joint pain** (not muscle soreness) | Stop that exercise. Log it. Substitute a pain-free close variant or skip. Coach raises it at check-in. Pain that persists >1 week → see a professional. |
| Sleep ≤ 3 and energy ≤ 3 | Optional: swap to a light day or rest. Logged as "smart rest" (still keeps the streak — see GAMIFICATION). |

**Oura data is advisory for now (D17).** Readiness score, HRV vs. baseline, resting HR, and temperature deviation are shown next to the check-in, but they don't change loads automatically. After ~4 weeks of paired data (Oura + subjective scores + session RPEs), Claude reviews whether an Oura-based rule earns a place here (e.g. "Oura readiness < 60 *and* soreness ≥ 5 → treat as soreness ≥ 7"). How you feel and how the bar moves stay primary.

## 5. Cardio / bike interference
The program says cardio is fine and encouraged if **low intensity**, and should taper toward the end of the program so you peak.

- **Commute rides are Zone 1–2** (conversational; can speak full sentences). Hills: gear down, don't hammer.
- **Heart-rate zones (when the watch recorded HR, D13):** HRmax = measured value if known, else `208 − 0.7 × age`. Zone 1 < 60% HRmax, Zone 2 = 60–70%, Zone 3+ > 70%. A ride counts as **easy** (XP-eligible as Zone 1–2) if **≥ 80% of its HR-recorded time is ≤ 70% HRmax**. The 20% allowance covers the steep finish of the ride home. Without HR, the athlete's self-reported zone is used.
- **Don't ride hard the day before a heavy lower session.** A short easy spin the day before is fine.
- Prefer commuting on **non-lifting days** or after lifting, not hours before a heavy squat/deadlift session.
- Weekly ride volume grows ≤ ~15–20% per week (see BIKE_COMMUTE_PLAN).
- **Last 2–3 weeks of the program (peak):** cap commuting at 2 round trips/week, all easy.
- Commuting burns a lot of energy (rough order: 600–1,200 kcal per round trip depending on distance, speed, wind). The program requires eating at maintenance or above — **eat for the riding**, or squat and deadlift progress will stall.

## 6. Nutrition (program guide + D9)
- **Through the on-ramp and the deadlift program: maintain bodyweight.** The program says no caloric deficit, and commuting will quietly create one if you don't eat for it.
- **Fat loss comes after the program**, during the deload + squat volume block: a slow cut of ~0.5–1 lb/week, high protein, with lifting loads unchanged. Commuting at Stage 5 does a lot of the work.
- Details and gram targets: `NUTRITION.md`.

## 7. Deloads and blocks
- **On-ramp (3 weeks)** before program Week 1 — see `ONRAMP.md`.
- After the program: **1-week deload**, then **4–6 weeks of easier, different training** (program guide). We use that window for a **squat-focused hypertrophy/volume block** — moderate loads, the goal is building the base for heavy squats while the deadlift recovers.
- Then a squat strength block. The program should not be run back-to-back.

## 8. What agents may and may not do
- May: explain rules, summarize logs, flag readiness issues, propose rule changes (as a written proposal).
- May not: invent loads outside these rules, tell the athlete to train through joint pain, or remove a deload to "level up faster".
