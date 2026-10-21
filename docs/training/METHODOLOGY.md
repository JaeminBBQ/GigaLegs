# Training Methodology (v2, D27–D31)

This is the rulebook the rules engine implements and Claude (coach) enforces. Changing a rule = user approval + edit this file + an entry in `docs/DECISIONS.md`. The calendar (weeks, distances, dates) lives in `SEASON_PLAN.md`. v1 (the purchased deadlift program + on-ramp) is in git history up to commit `591b2e2`; the on-ramp doc is in `archive/`.

## 1. Goals and priorities
1. **Show up every day.** Consistency is the main problem to solve, so every day has a short option that counts (§2).
2. **Look good:** keep and build muscle with full-body gym work, and get leaner slowly (§6).
3. **Events, trained together all season (D32):** the Biggest Little Half Marathon (Apr 24, 2027), America's Most Beautiful Bike Ride, 72 mi (Jun 6, 2027), then a full marathon in the fall (Lake Tahoe Marathon, Oct 2027; planned later). Running and riding are equal partners. Finishing healthy beats a fast time. Extra muscle slowing the events down is fine.

## 2. Every day: floor, standard, push
The engine offers one **mission** per day with three levels. Any time of day counts: morning, lunch, or before bed. The day closes at midnight.

| Level | What | Counts for |
|---|---|---|
| **Floor** | 15–20 min from the floor menu (below) | Daily streak |
| **Standard** | The next session in the week's plan | Daily streak + the week's checklist |
| **Push** (optional) | The standard session plus its pre-written add-on (§2b) | Same as standard, plus a small capped bonus (GAMIFICATION) |

**Floor menu:** pick one.
- 20-min walk
- 20-min easy spin (gym bike or outside)
- **Floor circuit** (~12 min, no equipment): 3 rounds of 10 push-ups (incline or knees is fine), 15 bodyweight squats, 10 glute bridges, 30 s plank. Rest as needed.
- 15 min of mobility (hips, calves, thoracic spine, hamstrings).

A floor day doesn't drop the planned session: the session queue just waits (§3).

### 2b. Push add-ons (written in advance; nothing else counts as push)
- **Gym:** +1 set on up to 2 upper-body exercises, *or* the arm/shoulder finisher (2 × lateral raise + 2 × curl + 2 × triceps, 12–20 reps). Never extra leg sets.
- **Easy ride:** +15 min, still easy.
- **Long ride:** none (it's already the week's big ride).
- **Easy run:** from Week 9, 4–6 × 20 s strides at the end (fast but relaxed, full walk-back recovery). No push in Weeks 1–8.
- **Long run, tempo run, race weeks, down weeks, and any day with pain:** no push.

## 3. The week: a checklist, not a calendar
Like v1 (D20), there are no fixed weekdays. Each plan week is a set of **slots**; the app suggests which slot fits today. Doing two slots in one day is fine (e.g. a gym session in the morning and an easy ride after work), except long run + long ride.

Base week (exact contents per week in `SEASON_PLAN.md`):
- **Gym × 3** (alternate A and B: A-B-A, then B-A-B), ~45–55 min
- **Run × 3:** Easy 1, Easy 2, Long (from Week 17, Easy 1 becomes a tempo run)
- **Ride × 2:** Easy ride + Long ride (commutes count)
- Every other day is a floor or recovery day, which still keeps the streak.

**Ordering rules (the engine checks these when it suggests today's slot):**
- No two run days in a row in Weeks 1–12 (tendons and shins adapt slower than lungs).
- The long run and the tempo run are never on back-to-back days.
- Long run and long ride on back-to-back days is fine (the normal weekend). Do the long run first when you can: impact work goes on fresh legs. Never both on the same day.
- **Gym A (leg-emphasis) is never the day before the long run or tempo run.**
- At most 2 hard days in a row, where hard = long run, tempo, long ride (> 2 h), or Gym A.
- **Weeks follow the calendar (Mon–Sun, D35).** Unfinished slots don't carry over. To keep growth safe, **runs and the long ride only move up a level after a week where you did them** (≥ 2 runs; the long ride): miss a week and the next one repeats the level instead of jumping ahead. From the taper (Week 24) and the ride peak's end (Week 31), the calendar rules so race weeks stay put.

## 4. Running
- **Easy means conversational:** you can speak full sentences. Walk breaks are allowed in any easy run. HR guide: easy ≤ 75% HRmax; the talk test wins if they disagree (D30). Exact bpm is in `athlete/PROFILE.md`.
- **Tempo:** "comfortably hard", 80–88% HRmax; you can speak a few words.
- **Volume grows ≤ ~10% per week** by time, and **every 4th week is a down week** (≈ −25%). The `SEASON_PLAN.md` table already follows this; the engine never adds to it.
- **Start with walk-run** even though cardio fitness will feel ahead of it. Strong lifters' muscles and lungs outrun their tendons and bones, and that gap is where shin splints and Achilles trouble come from.
- **Shoes:** get fitted at a running store before Week 1 runs feel serious.
- **Pain rules:** any sharp or joint pain, or pain that changes how you run → stop, walk home, log it. Next run waits until a pain-free walk and 10 pain-free hops on that leg. Shin pain that's sore to press on a specific spot, or pain lasting > 1 week → see a professional. Normal muscle soreness is fine.

## 4b. Riding
- **Easy rides** follow the HR zones of D13 (Zone 1–2, ≤ 70% HRmax for ≥ 80% of the ride; the allowance covers climbs). Long rides: same, except steady climbs may go into Zone 3.
- **Long-ride time grows ≤ ~20% over the previous longest ride**, with the down weeks in `SEASON_PLAN.md`. Indoor rides count.
- Fuel every ride over 90 min (NUTRITION). Bike safety and basics: `BIKE_COMMUTE_PLAN.md`.

## 5. Gym (full body, double progression)
### Templates
Each line is a **slot**: pick any listed option (variety keeps it fun) and stick with that pick for a few weeks so progress is measurable. Options marked * are the defaults.

**Gym A, leg emphasis**
| Slot | Options | Sets × reps |
|---|---|---|
| Squat pattern | leg press*, hack squat, goblet squat, barbell squat | 3 × 8–12 |
| Horizontal press | DB bench*, machine chest press, push-ups | 3 × 8–12 |
| Vertical pull | lat pulldown*, pull-ups, assisted pull-ups | 3 × 8–12 |
| Side delts | DB lateral raise*, cable lateral raise | 3 × 12–20 |
| Calves | standing calf raise*, seated calf raise, leg-press calf raise | 3 × 10–15 |
| Biceps | any curl | 2 × 10–15 |

**Gym B, upper emphasis**
| Slot | Options | Sets × reps |
|---|---|---|
| Hinge | DB Romanian deadlift*, 45° back extension, cable pull-through | 3 × 8–12 |
| Incline press | incline DB press*, incline machine press | 3 × 8–12 |
| Row | chest-supported row*, seated cable row, machine row | 3 × 8–12 |
| Shoulder press | DB shoulder press*, machine shoulder press | 2 × 8–12 |
| Hamstrings | leg curl (seated* or lying) | 2 × 10–15 |
| Triceps | cable pushdown*, overhead cable extension, dips | 2 × 10–15 |
| Core | plank*, dead bug, hanging knee raise, cable crunch | 2 sets |

### Effort (RPE, same scale as v1: 10 = nothing left, 8 = 2–3 reps left)
- **Weeks 1–2:** cap RPE 7 on everything. Pick starting weights by feel in the session; nobody types in a number in advance. This avoids the DOMS crater that would also wreck the first runs (the v1 on-ramp lesson).
- **From Week 3:** leg exercises cap RPE 8; upper-body exercises target RPE 8–9.
- RPE 10 only on the last set of an upper-body isolation exercise, and only as a push add-on.

### Double progression (engine)
Per exercise, per session, using the sets logged at that exercise's working weight:
1. **All sets hit the top of the rep range, at or under the cap, form OK** → add weight next time: +5 lb on upper-body, isolation, and dumbbell lifts (or the next dumbbell up), +10 lb on leg press, hack squat, and barbell lower-body lifts.
2. **Reps inside the range** → same weight; aim for more reps.
3. **Any set below the bottom of the range, form flagged, or over the cap** → same weight. Twice in a row → −10% and build back.
4. Swapping the option in a slot starts that exercise fresh (the first session sets the weight by feel).

### Running and lifting together
- **Down weeks:** gym sets −1 per exercise.
- **Weeks 21–25 (half peak and taper):** gym drops to 2 sessions/week; leg exercises −1 set and cap RPE 7.
- **Race weeks:** one short upper-body session only, ≥ 3 days before the race.

## 6. Body composition and nutrition (D31)
Get leaner slowly while keeping strength and training quality: ~0.25–0.75 lb/week on the 7-day average, high protein. No deficit in race weeks or during illness. Details and targets: `NUTRITION.md`.

## 7. Readiness, bad days, and pain
- **Bad day (tired, busy, unmotivated):** do the floor. That's the whole point of it. Done is better than skipped.
- **Very sore legs (≥ 7/10) or poor sleep two nights in a row:** the app offers a floor or an easy ride instead of a run or Gym A. Accepting it earns the "smart call" XP.
- **Sick:** above-the-neck cold → floor walk is OK; fever, chest, or stomach → rest and use a streak freeze. Return with 2 easy days before any long or tempo session.
- **Pain:** §4 pain rules apply to all training. Pain is never "push through"; persistent pain → a professional.

## 8. What agents may and may not do
- May: explain rules, suggest today's slot, summarize logs, flag readiness or pain issues, propose rule changes in writing.
- May not: invent loads or distances outside these rules and `SEASON_PLAN.md`, tell the athlete to train through pain, reward extra unplanned volume, or remove a down week or taper.
