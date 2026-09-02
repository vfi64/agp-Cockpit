from __future__ import annotations

from pathlib import Path

from agp_cockpit.core.process_control import (
    start_ollama,
    stop_ollama_processes,
    verify_ollama_port_ownership,
)
from agp_cockpit.core.runtime import find_executable
from agp_cockpit.core.startup import (
    StartupHooks,
    StartupResult,
    execute_guarded_startup,
)
from agp_cockpit.core.startup_probe import observe_live_read_only


def _ollama_executable() -> Path:
    info = find_executable(
        "ollama",
        extra_candidates=(
            "/opt/homebrew/bin/ollama",
            "/usr/local/bin/ollama",
            "/Applications/Ollama.app/Contents/Resources/ollama",
        ),
    )
    if info.path is None:
        raise RuntimeError("Ollama executable not found")
    return info.path


def guarded_start_live_ollama() -> None:
    executable = _ollama_executable()
    result = start_ollama(executable)
    if not result.port_ready:
        raise RuntimeError(
            "Ollama was started but port 11434 did not become ready"
        )


def guarded_recover_live_ollama() -> None:
    safe, owner = verify_ollama_port_ownership()
    if not safe:
        details = ", ".join(
            f"{p.pid}:{p.command}" for p in owner.processes
        ) or "unknown owner"
        raise RuntimeError(
            "Refusing recovery because port 11434 has a foreign owner: "
            + details
        )

    stopped = stop_ollama_processes()
    if stopped.remaining_pids:
        raise RuntimeError(
            "Could not stop all Ollama processes: "
            + ", ".join(map(str, stopped.remaining_pids))
        )
    if not stopped.port_free:
        raise RuntimeError(
            "Port 11434 is still occupied after stopping Ollama"
        )

    guarded_start_live_ollama()


def execute_live_guarded_startup() -> StartupResult:
    hooks = StartupHooks(
        observe=observe_live_read_only,
        start_ollama=guarded_start_live_ollama,
        recover_ollama=guarded_recover_live_ollama,
    )
    return execute_guarded_startup(hooks)
