import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path
    database_url: str
    mode: str  # local | hosted (D8)
    timezone: str
    program_path: Path
    season_path: Path
    route_path: Path
    onramp_start: str  # ISO date the on-ramp starts, for the Path timeline
    bike_stage: int
    # Tailscale gate (D34); both set = only localhost, or the Pi relay's secret + an allowed login
    proxy_secret: str = ""
    allowed_logins: frozenset[str] = frozenset()


def _csv(name: str) -> frozenset[str]:
    return frozenset(v.strip().lower() for v in os.environ.get(name, "").split(",") if v.strip())


@lru_cache
def get_settings() -> Settings:
    root = Path(os.environ.get("GIGALEGS_ROOT", Path.cwd()))
    return Settings(
        root=root,
        database_url=os.environ.get("DATABASE_URL", f"sqlite:///{root / 'data' / 'gigalegs.db'}"),
        mode=os.environ.get("GIGALEGS_MODE", "local"),
        timezone=os.environ.get("GIGALEGS_TZ", "America/Los_Angeles"),
        program_path=Path(
            os.environ.get(
                "GIGALEGS_PROGRAM", root / "program" / "private" / "deadlift-program.json"
            )
        ),
        season_path=Path(os.environ.get("GIGALEGS_SEASON", root / "program" / "season-2026.json")),
        route_path=Path(os.environ.get("GIGALEGS_ROUTE", root / "athlete" / "route.geojson")),
        onramp_start=os.environ.get("GIGALEGS_ONRAMP_START", "2026-10-05"),
        bike_stage=int(os.environ.get("GIGALEGS_BIKE_STAGE", "1")),
        proxy_secret=os.environ.get("GIGALEGS_PROXY_SECRET", "").strip(),
        allowed_logins=_csv("GIGALEGS_ALLOWED_LOGINS"),
    )
