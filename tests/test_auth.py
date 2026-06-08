"""Shared-password gate: off when APP_PASSWORD unset; enforced when set; /health open."""

import base64

import director_agent.api.app as appmod
from fastapi.testclient import TestClient

client = TestClient(appmod.app)


def _basic(pw, user="doner"):
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()}


def test_gate_off_when_unset(monkeypatch):
    monkeypatch.delenv("APP_PASSWORD", raising=False)
    assert client.get("/health").status_code == 200
    assert client.get("/").status_code == 200


def test_gate_enforced_when_set(monkeypatch):
    monkeypatch.setenv("APP_PASSWORD", "letmein")
    # No creds -> 401 with a Basic challenge
    r = client.get("/")
    assert r.status_code == 401 and "Basic" in r.headers.get("WWW-Authenticate", "")
    # Wrong password -> 401
    assert client.get("/", headers=_basic("nope")).status_code == 401
    # Right password (any username) -> allowed
    assert client.get("/", headers=_basic("letmein")).status_code == 200
    assert client.get("/project", headers=_basic("letmein", user="anyone")).status_code == 200
    # /health stays open for the host health check
    assert client.get("/health").status_code == 200
