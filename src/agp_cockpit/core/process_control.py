from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.runtime import (
    OLLAMA_DEFAULT_HOST,
    OLLAMA_DEFAULT_PORT,
    probe_tcp_port,
)


@dataclass(frozen=True)
class ProcessInfo:
    pid: int
    command: str


@dataclass(frozen=True)
class PortOwner:
    port: int
    processes: tuple[ProcessInfo, ...]


@dataclass(frozen=True)
class StopResult:
    targeted_pids: tuple[int, ...]
    terminated_pids: tuple[int, ...]
    remaining_pids: tuple[int, ...]
    port_free: bool


@dataclass(frozen=True)
class StartResult:
    pid: int
    port_ready: bool


def parse_ps_lines(lines: Iterable[str]) -> tuple[ProcessInfo, ...]:
    result: list[ProcessInfo] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        first, sep, rest = line.partition(" ")
        if not sep:
            continue
        try:
            pid = int(first)
        except ValueError:
            continue
        command = rest.strip()
        if command:
            result.append(ProcessInfo(pid=pid, command=command))
    return tuple(result)



def list_processes() -> tuple[ProcessInfo, ...]:
    from agp_cockpit.adapters.macos_process_control import list_processes as impl
    return impl()

def ollama_processes(*, processes: Iterable[ProcessInfo] | None = None) -> tuple[ProcessInfo, ...]:
    current = tuple(processes) if processes is not None else list_processes()
    matches: list[ProcessInfo] = []
    for process in current:
        command = process.command.casefold()
        if "ollama" not in command:
            continue
        if "agp_cockpit" in command:
            continue
        matches.append(process)
    return tuple(matches)



def pids_listening_on_port(port: int) -> tuple[int, ...]:
    from agp_cockpit.adapters.macos_process_control import (
        pids_listening_on_port as impl,
    )
    return impl(port)

def port_owner(
    port: int,
    *,
    processes: Iterable[ProcessInfo] | None = None,
    listening_pids: Iterable[int] | None = None,
) -> PortOwner:
    current = tuple(processes) if processes is not None else list_processes()
    pids = tuple(listening_pids) if listening_pids is not None else pids_listening_on_port(port)
    by_pid = {process.pid: process for process in current}
    owners = tuple(by_pid[pid] for pid in pids if pid in by_pid)
    return PortOwner(port=port, processes=owners)


def verify_ollama_port_ownership(
    port: int = OLLAMA_DEFAULT_PORT,
    *,
    processes: Iterable[ProcessInfo] | None = None,
    listening_pids: Iterable[int] | None = None,
) -> tuple[bool, PortOwner]:
    owner = port_owner(port, processes=processes, listening_pids=listening_pids)
    if not owner.processes:
        return True, owner
    owner_pids = {p.pid for p in owner.processes}
    ollama_pids = {p.pid for p in ollama_processes(processes=owner.processes)}
    return owner_pids == ollama_pids, owner


def stop_ollama_processes(
    *,
    timeout: float = 5.0,
    kill_timeout: float = 2.0,
    process_supplier: Callable[[], tuple[ProcessInfo, ...]] = list_processes,
    signal_sender: Callable[[int, int], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    port_probe: Callable[..., object] = probe_tcp_port,
) -> StopResult:
    targets = ollama_processes(processes=process_supplier())
    target_pids = tuple(p.pid for p in targets)

    for pid in target_pids:
        if signal_sender is None:
            from agp_cockpit.adapters.macos_process_control import send_sigterm
            send_sigterm(pid)
        else:
            signal_sender(pid, 15)

    deadline = monotonic() + timeout
    remaining = set(target_pids)
    while remaining and monotonic() < deadline:
        current = {p.pid for p in process_supplier()}
        remaining &= current
        if remaining:
            sleep(0.1)

    if remaining:
        for pid in tuple(sorted(remaining)):
            if signal_sender is None:
                from agp_cockpit.adapters.macos_process_control import send_sigkill
                send_sigkill(pid)
            else:
                signal_sender(pid, 9)
        kill_deadline = monotonic() + kill_timeout
        while remaining and monotonic() < kill_deadline:
            current = {p.pid for p in process_supplier()}
            remaining &= current
            if remaining:
                sleep(0.1)

    probe = port_probe(OLLAMA_DEFAULT_HOST, OLLAMA_DEFAULT_PORT)
    return StopResult(
        targeted_pids=target_pids,
        terminated_pids=tuple(pid for pid in target_pids if pid not in remaining),
        remaining_pids=tuple(sorted(remaining)),
        port_free=not bool(probe.accepting_connections),
    )


def start_ollama(
    executable: Path,
    *,
    timeout: float = 10.0,
    popen_factory: Callable[..., object] | None = None,
    sleep: Callable[[float], None] = time.sleep,
    monotonic: Callable[[], float] = time.monotonic,
    port_probe: Callable[..., object] = probe_tcp_port,
) -> StartResult:
    before = port_probe(OLLAMA_DEFAULT_HOST, OLLAMA_DEFAULT_PORT)
    if bool(before.accepting_connections):
        raise RuntimeError(f"refusing to start Ollama: port {OLLAMA_DEFAULT_PORT} is already in use")

    if popen_factory is None:
        from agp_cockpit.adapters.macos_process_control import spawn_detached
        process = spawn_detached([str(executable), "serve"])
    else:
        process = popen_factory([str(executable), "serve"], start_new_session=True)

    deadline = monotonic() + timeout
    ready = False
    while monotonic() < deadline:
        probe = port_probe(OLLAMA_DEFAULT_HOST, OLLAMA_DEFAULT_PORT)
        if bool(probe.accepting_connections):
            ready = True
            break
        sleep(0.1)

    return StartResult(pid=process.pid, port_ready=ready)
