from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import socket
import subprocess
from typing import Iterable

OLLAMA_DEFAULT_HOST = "127.0.0.1"
OLLAMA_DEFAULT_PORT = 11434

@dataclass(frozen=True)
class ExecutableInfo:
    name: str
    path: Path | None

    @property
    def installed(self) -> bool:
        return self.path is not None

@dataclass(frozen=True)
class PortStatus:
    host: str
    port: int
    accepting_connections: bool

@dataclass(frozen=True)
class RuntimeStatus:
    ollama: ExecutableInfo
    hermes: ExecutableInfo
    ollama_port: PortStatus

def find_executable(name: str, *, extra_candidates: Iterable[str | Path] = ()) -> ExecutableInfo:
    resolved = shutil.which(name)
    if resolved:
        return ExecutableInfo(name=name, path=Path(resolved).resolve())
    for candidate in extra_candidates:
        path = Path(candidate).expanduser()
        if path.is_file() and path.stat().st_mode & 0o111:
            return ExecutableInfo(name=name, path=path.resolve())
    return ExecutableInfo(name=name, path=None)

def probe_tcp_port(host: str, port: int, *, timeout: float = 0.20) -> PortStatus:
    if not (0 < port < 65536):
        raise ValueError(f"invalid TCP port: {port}")
    try:
        with socket.create_connection((host, port), timeout=timeout):
            accepting = True
    except (ConnectionRefusedError, TimeoutError, OSError):
        accepting = False
    return PortStatus(host=host, port=port, accepting_connections=accepting)

def list_process_lines() -> tuple[str, ...]:
    completed = subprocess.run(
        ["ps", "-axo", "pid=,command="],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return ()
    return tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())

def process_name_present(process_name: str, *, process_lines: Iterable[str] | None = None) -> bool:
    lines = tuple(process_lines) if process_lines is not None else list_process_lines()
    needle = process_name.casefold()
    return any(needle in line.casefold() for line in lines)

def discover_local_runtime() -> RuntimeStatus:
    ollama = find_executable(
        "ollama",
        extra_candidates=(
            "/opt/homebrew/bin/ollama",
            "/usr/local/bin/ollama",
            "/Applications/Ollama.app/Contents/Resources/ollama",
        ),
    )
    hermes = find_executable(
        "hermes",
        extra_candidates=(
            "~/.local/bin/hermes",
            "/opt/homebrew/bin/hermes",
            "/usr/local/bin/hermes",
        ),
    )
    return RuntimeStatus(
        ollama=ollama,
        hermes=hermes,
        ollama_port=probe_tcp_port(OLLAMA_DEFAULT_HOST, OLLAMA_DEFAULT_PORT),
    )
