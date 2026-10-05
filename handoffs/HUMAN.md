# Needs the Human

Items Claude needs from the user. Claude adds items; the user answers inline or in chat.
**The repo is public:** keep answers with personal details in chat or in `athlete/PROFILE.md`, not in this file.

## Open
### Start training (no app needed)
- [ ] **Start the app:** `cd ~/Projects/GigaLegs && uv run gigalegs serve`. Open the printed phone URL in Safari (same Wi-Fi) → Share → Add to Home Screen. The Mac has to be awake with the server running.
- [ ] Each morning, tap your soreness (0–10) on Today; it drives the on-ramp gate and the daily suggestion. Log lifts by tapping through the sets; log rides, recovery, and rest days from Today. Messaging Claude still works too.
- [ ] **Injuries/pain:** anything in the knees, back, or hips Claude should know about?

### Bike
- [ ] **Recon ride** (a weekend, before Stage 3): Sparks Blvd → Erica Greif Memorial Bikeway (the path beside Veterans) → South Meadows Pkwy. Tell Claude about anything sketchy, especially the I-80 ramps and the last mile of Veterans.
- [ ] On rides: if you're wearing the watch, start an **Outdoor Cycle** workout and read the miles/minutes off it when you log the ride.
- [ ] **Tune-up** before Stage 2 (see "Bike basics" in BIKE_COMMUTE_PLAN).
- [ ] Is there a shower or a place to change at work?
- [ ] Which weekdays you'd eventually want to commute.

### Optional
- [ ] **Permission-prompt forwarding to Discord:** create `.claude/settings.json` with the same `Notification` hook as LeagueApp (Claude wasn't allowed to write the agent's own settings file):
  ```json
  {"hooks": {"Notification": [{"hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/tools/notify.py\" --hook"}]}]}}
  ```

## Done
- [x] Web app MVP built (D21); no fixed training days (D20); Sparks Blvd bike lane confirmed on Street View (D22).
- [x] Wearable sync deferred; logging is manual via chat for now (D19).
- [x] Workflow: Claude orchestrates, DeepSeek implements, and you relay and commit (2026-10-03).
- [x] Git: local identity + SSH key (`~/.ssh/id_ed25519_github`) match ChessCoach; GitHub auth verified. The repo is **public** (D10).
- [x] Discord webhook copied from ChessCoach into `.env`; test ping sent.
- [x] Bodyweight and goal → maintain through the program, slow cut after (D9).
- [x] Hosting: local for now, built multi-user-ready (D8).
- [x] lb sheet → normalized program + concrete on-ramp sessions (T002).
- [x] Maxes: 365 / 495 all-time; the program runs off your entered 275 / 405 (D14).
- [x] Route measured: 16.7 mi, ~230 ft up on the way in / ~615 ft up on the way home (T006).
