# Gamification Design

## Core principle
**The game rewards doing the plan, not doing more.** XP comes from compliance, quality, and consistency. There is no XP for extra sets, exceeding RPE caps, or skipping deloads. If a mechanic could tempt the athlete into a worse training decision, it's cut.

## XP sources
| Action | XP | Notes |
|---|---|---|
| Complete a lifting session as prescribed | 100 | Every planned exercise has its planned sets logged, none over the cap |
| Each working set logged with RPE + form toggle | 5 | Rewards good logging (the engine needs it) |
| Set RPE on target | +5 | Inside the program's RPE range; on-ramp: within 2 under the cap. Accuracy, not intensity |
| Readiness check-in before session | 10 | |
| Morning soreness check-in | 5 | First one per day |
| Recovery day logged (walk, mobility, easy spin) | 15 | "Something every day" without digging a hole (D20) |
| Timed hold logged (planks) | 5 | No RPE needed |
| Taking a gated adjustment (lighter day, repeat week) | 50 | Listening to the body is a skill |
| Logged "smart rest" (readiness gate triggered) | 25 | Keeps streak |
| Ride logged | 1 XP per mile, ×1.5 if a commute | Zone 1–2 only; no bonus for speed |
| Weekly check-in completed | 50 | |
| e1RM PR (squat/deadlift) | 150 | Only from sets with form OK and RPE ≥ 7 |
| Deload week completed | 200 | Deloads are worth *more*, not less |

**No XP** for: sets above the RPE cap, sets with form flagged bad, extra unprescribed volume, riding above Zone 2.

## Levels
`level = floor(sqrt(totalXP / 100)) + 1` (L2 at 100 XP, L5 at 1,600, L10 at 8,100, L20 at 36,100). Roughly one level per week early, slowing over time. Level titles are leg-themed (e.g. *Quad Squire → Hamstring Knight → Glute Baron → Giga Legs*). Designer owns the title list.

## Streaks
- Unit is the **week**, not the day: a week counts if all planned sessions were done *or* properly gated (smart rest / adjusted day). Daily streaks punish rest days — avoided on purpose.
- One "freeze" per 6 weeks for life events (travel, sickness).

## Quests and boss fights
- **Quests (weekly):** e.g. "Log every set with RPE this week", "Commute one way", "Hit protein 5 of 7 days".
- **Boss fights:** program max/AMRAP test days. The boss has HP = target weight × reps; dealing damage = logged result. Win or lose, the result feeds the engine. Losing a boss fight is just data.

## Commute map (the big progression bar)
The route Five Ridges → South Meadows rendered as a progress line with checkpoints unlocked by bike-plan stages and milestones:
1. *Leave the Ridge* — first ride logged
2. *Marina Laps* — Stage 1 complete
3. *Sparks Blvd* — first ride ≥ 10 mi
4. *I-80 Crossing* — route recon done
5. *Veterans Pkwy* — first one-way commute
6. *South Meadows* — first round trip
7. *Commuter* — 4 weeks at Stage 5

## Badges (examples)
- *Patience Pays* — completed the 3-week on-ramp without skipping ahead
- *Iron Lungs* — 100 commute miles
- *Smart Rest* — took 3 gated adjustments (shows the game respects recovery)
- *Plate Collector* — squat e1RM milestones: 225, 275, 315, 365, 405 lb
