# Needs the Human

Items Claude needs from the user. Claude adds items; the user answers inline or in chat.
**The repo is public:** keep answers with personal details in chat or in `athlete/PROFILE.md`, not in this file.

## Open
### Training data (blocks T002: the real on-ramp numbers)
- [ ] **The program's lb sheet.** `program/source/Deadlift.csv` has only the guide text (rules, RPE, FAQ); the weeks/days/sets/lb tab isn't in it. Export that tab (or every tab) as CSV, or drop in the original `.xlsx`, under `program/source/`. It's gitignored, so it won't be published.
- [ ] **Current maxes:** squat and deadlift 1RM, or a recent heavy set (weight × reps, plus how hard it felt).
- [ ] **Schedule:** how many lifting days per week, and which weekdays.
- [ ] **Injuries/pain:** anything in the knees, back, or hips Claude should know about?

### Bike (blocks T006)
- [ ] **Measure the route:** Google Maps → directions from home to work → bike icon → the Sparks Blvd / Veterans Pkwy option. Paste the miles and elevation gain in chat.
- [ ] **Tune-up:** take the bike to a local shop for a basic tune-up + saddle-height check before Stage 2 (see "Bike basics" in BIKE_COMMUTE_PLAN).
- [ ] Is there a shower or a place to change at work?
- [ ] Which weekdays you'd eventually want to commute.

### Optional
- [ ] **Permission-prompt forwarding to Discord:** create `.claude/settings.json` with the same `Notification` hook as LeagueApp (Claude wasn't allowed to write the agent's own settings file):
  ```json
  {"hooks": {"Notification": [{"hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/tools/notify.py\" --hook"}]}]}}
  ```

## Done
- [x] Workflow: Claude orchestrates, DeepSeek implements, and you relay and commit (2026-10-03).
- [x] Git repo created; local identity matches ChessCoach (JaeminBBQ). The remote `JaeminBBQ/GigaLegs` is **public** (D10).
- [x] Discord webhook copied from ChessCoach into `.env`; test ping sent.
- [x] Bodyweight and goal → maintain through the program, slow cut after (D9, NUTRITION.md).
- [x] Hosting: local for now, built multi-user-ready for a possible public version (D8).
- [x] Work address recorded (privately, in `athlete/PROFILE.md`).
