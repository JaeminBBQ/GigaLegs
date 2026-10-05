import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def fake_program_data() -> dict:
    return json.loads((FIXTURES / "fake-program.json").read_text())


@pytest.fixture
def app_env(tmp_path, monkeypatch):
    """A fresh app wired to a temp DB and the made-up program (never real athlete data)."""
    monkeypatch.setenv("GIGALEGS_ROOT", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("GIGALEGS_PROGRAM", str(FIXTURES / "fake-program.json"))
    monkeypatch.setenv("GIGALEGS_ROUTE", str(tmp_path / "no-route.geojson"))
    from gigalegs import config, db, services

    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()
    services._load_program_file.cache_clear()
    from gigalegs.models import Base

    Base.metadata.create_all(db.get_engine())
    yield
    db.get_engine().dispose()
    config.get_settings.cache_clear()
    db.get_engine.cache_clear()
    db.get_sessionmaker.cache_clear()
