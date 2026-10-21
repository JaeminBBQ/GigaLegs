# Hosting: private access through Tailscale (D34)

The app runs in a **Docker container on the Mac mini** (SQLite stays on the Mac). The Mac mini always runs NordVPN, so **Tailscale runs on the Raspberry Pi**, which relays to the Mac over the home LAN. Only devices signed in to the athlete's tailnet can reach it, and the app checks who is asking.

```
phone (Tailscale) ──tailnet HTTPS──▶ Pi: tailscale serve :443 ──▶ Pi: Caddy 127.0.0.1:8001 ──LAN──▶ Mac mini :8000 (container)
                                       adds Tailscale-User-Login     adds X-Gigalegs-Proxy-Secret
```

- `tailscale serve` adds the signed-in user's login (and strips any copy the client sent). It only proxies to localhost, so Caddy on the Pi forwards to the Mac and adds a shared secret.
- Docker on macOS hides the real client IP, so the **secret** is what proves a request came through the Pi. The app (`web/access.py`) allows a request only from inside the container, or with the secret **and** an allowed login. Anything else on the LAN gets 403.
- URL: `https://rpi400.<tailnet>.ts.net` with a real certificate, so the PWA installs properly.
- The Pi also advertises a **subnet route to the Mac mini only** (`<mac-mini-ip>/32`), so any tailnet device can SSH or screen-share to the Mac mini from anywhere. App traffic that way still needs the secret, so it's 403 unless it comes through the Pi relay.

Pi details and the real LAN addresses: `~/Projects/rpi/CLAUDE.md` → "Tailscale" (private, not in this repo).

## Mac mini setup
1. **Docker:** install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or OrbStack) and turn on "Start when you log in".
2. **Code:** `git clone https://github.com/JaeminBBQ/GigaLegs.git ~/GigaLegs`
3. **Private files:** unpack the bundle Claude made on the MacBook (data, athlete, program, `.env` with the gate settings):
   ```
   tar xzf ~/Downloads/gigalegs-private.tgz -C ~/GigaLegs
   ```
   From then on the Mac mini's `data/gigalegs.db` is the only live copy; don't keep logging into the MacBook's copy.
4. **NordVPN:** Settings → allow LAN access (turn **off** "Invisibility on LAN" if it's on). If macOS asks whether Docker may accept incoming connections, click Allow.
5. **Run:**
   ```
   cd ~/GigaLegs && docker compose up -d --build
   docker compose ps            # should say "healthy" after a minute
   ```
6. **Check:** on the phone (Tailscale on), open `https://rpi400.<tailnet>.ts.net` → GigaLegs. Share → Add to Home Screen. From any browser *without* Tailscale, `http://<mac-mini-ip>:8000` must say **Forbidden**: that's the gate working.

## Day to day
- Update after a `git pull`: `docker compose up -d --build`. Logs: `docker compose logs -f`.
- The Mac mini (Docker running) and the Pi must be on.
- `.env` holds `GIGALEGS_PROXY_SECRET` (must match the Pi's `/etc/caddy/gigalegs.env`) and `GIGALEGS_ALLOWED_LOGINS` (your Tailscale login). Rotate the secret: change it on the Pi, restart Caddy, update `.env`, `docker compose up -d`.
- Plain local development still works without Docker: `uv run gigalegs serve` (no gate unless those two vars are set).

## Addresses
Give the Pi and the Mac mini **DHCP reservations** in the router. If the Mac mini's IP changes, update the Caddyfile and the advertised route on the Pi.
