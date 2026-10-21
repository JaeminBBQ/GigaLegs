"""Tailscale access gate (D34)."""

import pytest
from fastapi.testclient import TestClient

SECRET = "s3cret-from-the-pi"
LOGIN = "athlete@example.com"
LAN = "192.168.65.1"  # what Docker on macOS shows for every outside client


@pytest.fixture
def gated(app_env, monkeypatch):
    from gigalegs import config
    from gigalegs.web import access

    monkeypatch.setenv("GIGALEGS_PROXY_SECRET", f" {SECRET} ")
    monkeypatch.setenv("GIGALEGS_ALLOWED_LOGINS", f"{LOGIN.upper()}, other@example.com")
    config.get_settings.cache_clear()
    access.get_gate.cache_clear()
    yield
    access.get_gate.cache_clear()


def status(ip=LAN, secret=None, login=None, path="/") -> int:
    from gigalegs.web.app import app

    headers = {}
    if secret:
        headers["X-Gigalegs-Proxy-Secret"] = secret
    if login:
        headers["Tailscale-User-Login"] = login
    return TestClient(app, client=(ip, 50000)).get(path, headers=headers).status_code


def test_relay_with_allowed_login(gated):
    assert status(secret=SECRET, login=LOGIN) == 200


def test_localhost_allowed(gated):
    assert status(ip="127.0.0.1") == 200


@pytest.mark.parametrize(
    "secret,login",
    [
        (None, None),
        (None, LOGIN),  # someone on the LAN forging the login header
        ("wrong", LOGIN),
        (SECRET, None),
        (SECRET, "intruder@example.com"),
    ],
    ids=["nothing", "login-only", "wrong-secret", "secret-no-login", "secret-wrong-login"],
)
def test_denied(gated, secret, login):
    assert status(secret=secret, login=login) == 403


def test_static_files_also_gated(gated):
    assert status(path="/static/style.css") == 403


def test_open_when_not_configured(app_env):
    from gigalegs.web import access

    access.get_gate.cache_clear()
    assert status() == 200
