from pathlib import Path
import signal

import pytest

from agp_cockpit.core.process_control import (
    ProcessInfo,
    ollama_processes,
    parse_ps_lines,
    port_owner,
    start_ollama,
    stop_ollama_processes,
    verify_ollama_port_ownership,
)


class Probe:
    def __init__(self, accepting_connections: bool) -> None:
        self.accepting_connections = accepting_connections


def test_parse_ps_lines() -> None:
    processes = parse_ps_lines(("  123 /opt/homebrew/bin/ollama serve", "  456 /bin/zsh", "garbage"))
    assert processes == (
        ProcessInfo(123, "/opt/homebrew/bin/ollama serve"),
        ProcessInfo(456, "/bin/zsh"),
    )


def test_ollama_process_filter() -> None:
    processes = (ProcessInfo(1, "/opt/homebrew/bin/ollama serve"), ProcessInfo(2, "/bin/zsh"))
    assert ollama_processes(processes=processes) == (processes[0],)


def test_port_owner_matches_supplied_pids() -> None:
    processes = (ProcessInfo(10, "/opt/homebrew/bin/ollama serve"), ProcessInfo(20, "/bin/python"))
    owner = port_owner(11434, processes=processes, listening_pids=(10,))
    assert owner.processes == (processes[0],)


def test_verify_ollama_port_ownership_rejects_foreign_process() -> None:
    processes = (ProcessInfo(20, "/bin/python server.py"),)
    ok, owner = verify_ollama_port_ownership(processes=processes, listening_pids=(20,))
    assert ok is False
    assert owner.processes == processes


def test_verify_empty_port_is_safe() -> None:
    ok, owner = verify_ollama_port_ownership(processes=(), listening_pids=())
    assert ok is True
    assert owner.processes == ()


def test_stop_ollama_targets_only_ollama() -> None:
    calls: list[tuple[int, int]] = []
    states = iter((
        (ProcessInfo(11, "/opt/homebrew/bin/ollama serve"), ProcessInfo(22, "/bin/zsh")),
        (ProcessInfo(22, "/bin/zsh"),),
    ))

    def supplier():
        try:
            return next(states)
        except StopIteration:
            return (ProcessInfo(22, "/bin/zsh"),)

    times = iter((0.0, 0.0, 0.001, 0.002, 0.003))
    result = stop_ollama_processes(
        timeout=0.01,
        process_supplier=supplier,
        signal_sender=lambda pid, sig: calls.append((pid, sig)),
        sleep=lambda _: None,
        monotonic=lambda: next(times, 0.004),
        port_probe=lambda *_args, **_kwargs: Probe(False),
    )

    assert calls == [(11, signal.SIGTERM)]
    assert result.targeted_pids == (11,)
    assert result.remaining_pids == ()
    assert result.port_free is True


def test_start_ollama_refuses_busy_port() -> None:
    with pytest.raises(RuntimeError):
        start_ollama(Path("/opt/homebrew/bin/ollama"), port_probe=lambda *_a, **_k: Probe(True))


def test_start_ollama_waits_for_port() -> None:
    class FakeProcess:
        pid = 99

    probes = iter((Probe(False), Probe(False), Probe(True)))
    calls: list[list[str]] = []
    times = iter((0.0, 0.0, 0.001, 0.002, 0.003))

    def probe(*_args, **_kwargs):
        try:
            return next(probes)
        except StopIteration:
            return Probe(True)

    def popen(argv, **_kwargs):
        calls.append(argv)
        return FakeProcess()

    result = start_ollama(
        Path("/opt/homebrew/bin/ollama"),
        timeout=0.01,
        popen_factory=popen,
        sleep=lambda _: None,
        monotonic=lambda: next(times, 0.004),
        port_probe=probe,
    )

    assert calls == [["/opt/homebrew/bin/ollama", "serve"]]
    assert result.pid == 99
    assert result.port_ready is True
