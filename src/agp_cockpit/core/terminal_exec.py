from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class TerminalCommand:
    argv: tuple[str, ...]
    cwd: Path
    timeout_seconds: float = 120.0

    def validate(self) -> None:
        if not self.argv:
            raise ValueError("argv must not be empty")
        if any(not isinstance(part, str) or part == "" for part in self.argv):
            raise ValueError("argv must contain non-empty strings")
        if not self.cwd.exists() or not self.cwd.is_dir():
            raise ValueError(f"cwd is not a directory: {self.cwd}")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")


@dataclass(frozen=True)
class TerminalResult:
    argv: tuple[str, ...]
    cwd: Path
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration_seconds: float


class RunningTerminalProcess(Protocol):
    @property
    def pid(self) -> int: ...

    def cancel(self) -> None: ...

    def wait(self) -> TerminalResult: ...


def start_command(command: TerminalCommand) -> RunningTerminalProcess:
    """Compatibility wrapper; concrete subprocess ownership lives in the adapter."""
    from agp_cockpit.adapters.local_terminal import start_subprocess_command
    return start_subprocess_command(command)


def run_command(command: TerminalCommand) -> TerminalResult:
    """Compatibility wrapper around the adapter-level local executor."""
    from agp_cockpit.adapters.local_terminal import SubprocessTerminalAdapter
    return SubprocessTerminalAdapter().execute(command)


def preview_command(command: TerminalCommand) -> str:
    command.validate()
    lines = [
        f"CWD: {command.cwd}",
        "ARGV:",
    ]
    lines.extend(
        f"  [{index}] {part}"
        for index, part in enumerate(command.argv)
    )
    lines.append(f"TIMEOUT: {command.timeout_seconds:.1f}s")
    return "\n".join(lines)
