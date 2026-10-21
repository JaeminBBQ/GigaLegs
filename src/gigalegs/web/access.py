"""Private access through Tailscale on the Pi (docs/HOSTING.md, D34).

The app runs in a container on the Mac mini and listens on the LAN. The Pi runs
`tailscale serve`, which adds the signed-in user's login in `Tailscale-User-Login`
(stripping any client copy), and a Caddy relay that forwards to the Mac and adds
a shared secret. Docker on macOS hides the real client IP, so the secret is what
proves a request came through the Pi. A request is allowed only from inside the
container (localhost) or with the secret and an allowed login.
"""

import hmac
from dataclasses import dataclass
from functools import lru_cache

from ..config import get_settings

LOGIN_HEADER = "tailscale-user-login"
SECRET_HEADER = "x-gigalegs-proxy-secret"
LOCALHOST = frozenset({"127.0.0.1", "::1"})


@dataclass(frozen=True)
class AccessGate:
    proxy_secret: str
    allowed_logins: frozenset[str]

    def allows(self, client_ip: str | None, secret: str | None, login: str | None) -> bool:
        if client_ip in LOCALHOST:
            return True
        if not hmac.compare_digest((secret or "").encode(), self.proxy_secret.encode()):
            return False
        return (login or "").strip().lower() in self.allowed_logins


@lru_cache
def get_gate() -> AccessGate | None:
    """None = not configured (plain local mode, no gate)."""
    s = get_settings()
    if not (s.proxy_secret and s.allowed_logins):
        return None
    return AccessGate(s.proxy_secret, s.allowed_logins)
