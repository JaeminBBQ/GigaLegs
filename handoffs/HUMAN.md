# Needs the Human

Items Claude needs from the user. Claude adds items; the user answers inline or in chat.
**The repo is public:** keep answers with personal details in chat or in `athlete/PROFILE.md`, not in this file.

## Open
### Season v2 (D27–D31)
- [ ] **Read the plan and say OK** (or what to change): `docs/training/METHODOLOGY.md` + `SEASON_PLAN.md`.
- [ ] **Register:** Biggest Little Half (Apr 24) and America's Most Beautiful Bike Ride (Jun 6; 72 mi). Check the dates on the official pages first.
- [ ] **Running shoes:** get fitted at a running store before Week 1 (Oct 26).
- [ ] **Starter week (now → Oct 25):** something every day; try Gym A and Gym B once each at RPE ≤ 7; one walk-run. Message Claude what you did.
- [ ] **Injuries/pain:** anything in the knees, back, hips, shins, or feet Claude should know about?

The items below are from v1. The bike recon and tune-up still apply; ignore the on-ramp parts.

### Start training (no app needed)
- [ ] **Start the app:** `cd ~/Projects/GigaLegs && uv run gigalegs serve`. Open the printed phone URL in Safari (same Wi-Fi) → Share → Add to Home Screen. The Mac has to be awake with the server running.
- [ ] Each morning, tap your soreness (0–10) on Today; it drives the on-ramp gate and the daily suggestion. Log lifts by tapping through the sets; log rides, recovery, and rest days from Today. Messaging Claude still works too.

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
- [x] Workflow: Claude builds and coaches; you commit (D26, 2026-10-20; replaced the DeepSeek relay).
- [x] Git: local identity + SSH key (`~/.ssh/id_ed25519_github`) match ChessCoach; GitHub auth verified. The repo is **public** (D10).
- [x] Discord webhook copied from ChessCoach into `.env`; test ping sent.
- [x] Bodyweight and goal → maintain through the program, slow cut after (D9).
- [x] Hosting: local for now, built multi-user-ready (D8).
- [x] lb sheet → normalized program + concrete on-ramp sessions (T002).
- [x] Maxes: 365 / 495 all-time; the program runs off your entered 275 / 405 (D14).
- [x] Route measured: 16.7 mi, ~230 ft up on the way in / ~615 ft up on the way home (T006).
