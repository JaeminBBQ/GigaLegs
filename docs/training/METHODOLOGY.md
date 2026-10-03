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

1. **Hit target, form solid, RPE at or below target** → next prescribed weight as written (on RPE-based lifts: +10 lb for deadlift-pattern lifts, +5 lb for everything else).
2. **Hit target but RPE ≥ 1 above target** → repeat the same weight next time.
3. **Missed reps, or form broke down noticeably** → repeat the weight; if that happens twice in a row, drop 10% and rebuild.
4. **Never** increase weight when technique breaks down (program rule; also the engine can't see form, so the athlete's "form OK?" toggle on each set gates progression).

e1RM is estimated from top sets with the RPE-adjusted Epley formula: `e1RM = weight × (1 + (reps + (10 − RPE)) / 30)`. Only sets with RPE ≥ 7 count (lower RPE estimates are unreliable).

## 4. Readiness and recovery gates
Before each lifting session the athlete answers 3 quick questions (0–10): **leg soreness**, **sleep quality**, **overall energy**.

| Condition | Action |
|---|---|
| Soreness ≥ 7 | Do the session at 90% of prescribed loads, cap RPE at target −1. |
| Soreness ≥ 7 two sessions in a row | Coach flags: repeat the week instead of advancing. |
| **Sharp/joint pain** (not muscle soreness) | Stop that exercise. Log it. Substitute a pain-free close variant or skip. Coach raises it at check-in. Pain that persists >1 week → see a professional. |
| Sleep ≤ 3 and energy ≤ 3 | Optional: swap to a light day or rest. Logged as "smart rest" (still keeps the streak — see GAMIFICATION). |

## 5. Cardio / bike interference
The program says cardio is fine and encouraged if **low intensity**, and should taper toward the end of the program so you peak.

- **Commute rides are Zone 1–2** (conversational; can speak full sentences). Hills: gear down, don't hammer.
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
