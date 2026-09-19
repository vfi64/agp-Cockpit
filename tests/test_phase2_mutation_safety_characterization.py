"""Phase-2 characterization of mutation-capable seams using only fakes/temp files.

No live Ollama/Hermes process is started/stopped and ~/.hermes is never touched.
"""
from __future__ import annotations

import signal
from pathlib import Path

from agp_cockpit.core.hermes_writer import (
    restore_hermes_backup,
    update_hermes_model,
)
from agp_cockpit.core.process_control import (
    ProcessInfo,
    start_ollama,
    stop_ollama_processes,
)


class Probe:
    def __init__(self, accepting_connections: bool):
        self.accepting_connections = accepting_connections


def test_stop_ollama_targets_only_injected_ollama_processes():
    snapshots = [
        (
            ProcessInfo(pid=11, command="/Applications/Ollama.app/Contents/Resources/ollama serve"),
            ProcessInfo(pid=22, command="/usr/bin/python unrelated.py"),
        ),
        (ProcessInfo(pid=22, command="/usr/bin/python unrelated.py"),),
    ]
    signals = []
    clock = iter([0.0, 0.0, 0.1, 0.2, 0.3])

    def supplier():
        return snapshots.pop(0) if snapshots else ()

    result = stop_ollama_processes(
        timeout=1.0,
        kill_timeout=0.1,
        process_supplier=supplier,
        signal_sender=lambda pid, sig: signals.append((pid, sig)),
        sleep=lambda _s: None,
        monotonic=lambda: next(clock, 0.4),
        port_probe=lambda *_a, **_k: Probe(False),
    )

    assert signals == [(11, signal.SIGTERM)]
    assert result.targeted_pids == (11,)
    assert result.terminated_pids == (11,)
    assert result.remaining_pids == ()
    assert result.port_free is True


def test_start_ollama_uses_injected_popen_and_waits_for_injected_port():
    calls = []
    probes = iter([Probe(False), Probe(False), Probe(True)])
    clock = iter([0.0, 0.0, 0.1, 0.2, 0.3])

    class FakeProcess:
        pid = 4242

    def fake_popen(argv, **kwargs):
        calls.append((argv, kwargs))
        return FakeProcess()

    result = start_ollama(
        Path("/fake/ollama"),
        timeout=1.0,
        popen_factory=fake_popen,
        sleep=lambda _s: None,
        monotonic=lambda: next(clock, 0.4),
        port_probe=lambda *_a, **_k: next(probes, Probe(True)),
    )

    assert calls[0][0] == ["/fake/ollama", "serve"]
    assert result.pid == 4242
    assert result.port_ready is True


def test_start_ollama_refuses_busy_port_before_popen():
    called = []

    try:
        start_ollama(
            Path("/fake/ollama"),
            popen_factory=lambda *a, **k: called.append((a, k)),
            port_probe=lambda *_a, **_k: Probe(True),
        )
    except RuntimeError as exc:
        assert "already in use" in str(exc)
    else:
        raise AssertionError("busy port must refuse start")

    assert called == []


def test_update_hermes_model_uses_temp_config_backup_and_verifies(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text(
        "model: qwen3.5:9b-mlx\nother:\n  value: keep\n",
        encoding="utf-8",
    )

    result = update_hermes_model("qwen3.8:27b-mlx", path=path)

    assert result.old_model == "qwen3.5:9b-mlx"
    assert result.new_model == "qwen3.8:27b-mlx"
    assert result.verified is True
    assert result.backup_path.exists()
    assert "qwen3.8:27b-mlx" in path.read_text(encoding="utf-8")
    assert "qwen3.5:9b-mlx" in result.backup_path.read_text(encoding="utf-8")


def test_restore_hermes_backup_restores_temp_config(tmp_path):
    path = tmp_path / "config.yaml"
    backup = tmp_path / "config.yaml.agp-cockpit.bak"
    path.write_text("model: changed\n", encoding="utf-8")
    backup.write_text("model: original\n", encoding="utf-8")

    restored = restore_hermes_backup(path=path, backup_path=backup)

    assert path.read_text(encoding="utf-8") == "model: original\n"
    assert restored.model == "original"
