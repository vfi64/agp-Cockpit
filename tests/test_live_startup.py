from pathlib import Path

import pytest

import agp_cockpit.core.live_startup as live


class StartResult:
    port_ready = True


class StopResult:
    remaining_pids = ()
    port_free = True


def test_guarded_start_uses_discovered_executable(monkeypatch):
    calls = []

    class Info:
        path = Path("/opt/homebrew/bin/ollama")

    monkeypatch.setattr(
        live,
        "find_executable",
        lambda *a, **k: Info(),
    )
    monkeypatch.setattr(
        live,
        "start_ollama",
        lambda path: calls.append(path) or StartResult(),
    )

    live.guarded_start_live_ollama()

    assert calls == [Path("/opt/homebrew/bin/ollama")]


def test_recovery_refuses_foreign_port_owner(monkeypatch):
    class Owner:
        processes = ()

    monkeypatch.setattr(
        live,
        "verify_ollama_port_ownership",
        lambda: (False, Owner()),
    )

    with pytest.raises(RuntimeError):
        live.guarded_recover_live_ollama()


def test_recovery_stops_then_starts(monkeypatch):
    calls = []

    class Owner:
        processes = ()

    monkeypatch.setattr(
        live,
        "verify_ollama_port_ownership",
        lambda: (True, Owner()),
    )
    monkeypatch.setattr(
        live,
        "stop_ollama_processes",
        lambda: calls.append("stop") or StopResult(),
    )
    monkeypatch.setattr(
        live,
        "guarded_start_live_ollama",
        lambda: calls.append("start"),
    )

    live.guarded_recover_live_ollama()

    assert calls == ["stop", "start"]
