# Gamification Design (v2, D29)

## Core principle
**The game rewards showing up and doing the plan, not doing more.** The athlete's problem is motivation, so the biggest rewards go to consistency, and the smallest possible effort (the floor) always counts. There is still no XP for unplanned extra volume, going over RPE caps, skipping down weeks or tapers, or training through pain (METHODOLOGY wins any conflict).

## Daily mission
Today screen shows one mission with three buttons: **Floor · Standard · Push** (METHODOLOGY §2). Logging a floor takes 2 taps.

| Action | XP | Notes |
|---|---|---|
| Floor done | 30 | Any option on the floor menu |
| Standard session done | 100 | Gym, easy run, easy ride |
| Key session done | 150 | Long run, tempo run, long ride |
| Push add-on done | +20 | Max **2 per week**; only the add-ons written in METHODOLOGY §2b |
| Working set logged with RPE + form toggle, at or under the cap | 5, +5 if within 2 of the cap | Helps the engine progress your weights; accuracy, not intensity |
| Weight increase earned (double progression) | 25 | Per exercise; rewards quality reps, not max effort |
| Smart call (took the floor/easy option the app offered for soreness, sleep, sickness, or pain) | 50 | Listening to your body is a skill |
| Week's checklist complete | 100 | |
| Down week or taper week complete | 200 | Worth *more* than a normal week |
| Race finished | 1,000 | |

**No XP** for: sets over the cap, sets with form flagged, a third+ push in a week, runs beyond the plan, pace or speed.

## Streaks
- **Daily streak:** any floor or standard logged that calendar day (any time before midnight).
- **Freezes:** earn 1 for every 14-day streak, hold at most 2. A missed day spends one automatically. Logged sickness or pain rest spends none (it's a smart call).
- **Weekly streak:** weeks whose checklist was completed (or properly adjusted). Kept from v1.

## Levels
Same curve as v1: `level = floor(sqrt(totalXP / 100)) + 1`. Titles get a full-body/endurance theme (e.g. *Rookie → Regular → Grinder → Hybrid → Engine → Machine → Giga*). XP and levels from v1 logs carry over.

## Season map (replaces the commute map as the big progress bar)
Starter week → Week 8 *First 20 min nonstop* → Week 16 *Base built* → Week 23 *11 miles* → **Apr 24 Half** → Week 30 *60-mile ride* → **Jun 6 Tahoe 72** → **Oct Marathon**. The commute map stays as a side quest.

## Badges
- *First Floor*: first floor logged ("the bad-day plan worked")
- *Never Zero*: 30-day daily streak; *Never Zero II*: 100 days
- *Nonstop*: first continuous 20-min run
- *Double Digits*: first 10-mile run
- *Half*: finished the half marathon; *Tahoe 72*: finished the ride; *Marathoner*: finished the marathon
- *Smart Rest*: 3 smart calls
- *Iron Lungs*: 100 commute miles (kept); *Run 100* / *Run 500*: lifetime run miles
- *Progress Machine*: 25 weight increases earned
- v1 badges already earned stay; squat plate badges stay earnable.
