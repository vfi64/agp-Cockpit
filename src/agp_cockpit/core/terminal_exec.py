from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import time


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


class RunningTerminalProcess:
    def __init__(self, process: subprocess.Popen[str], command: TerminalCommand) -> None:
        self._process = process
        self.command = command

    @property
    def pid(self) -> int:
        return self._process.pid

    def cancel(self) -> None:
        if self._process.poll() is None:
            self._process.terminate()

    def wait(self) -> TerminalResult:
        start = time.monotonic()
        try:
            stdout, stderr = self._process.communicate(
                timeout=self.command.timeout_seconds
            )
            return TerminalResult(
                argv=self.command.argv,
                cwd=self.command.cwd,
                returncode=self._process.returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=False,
                duration_seconds=time.monotonic() - start,
            )
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                stdout, stderr = self._process.communicate(timeout=2.0)
            except subprocess.TimeoutExpired:
                self._process.kill()
                stdout, stderr = self._process.communicate()

            return TerminalResult(
                argv=self.command.argv,
                cwd=self.command.cwd,
                returncode=self._process.returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
                duration_seconds=time.monotonic() - start,
            )


def start_command(command: TerminalCommand) -> RunningTerminalProcess:
    command.validate()
    process = subprocess.Popen(
        list(command.argv),
        cwd=str(command.cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    return RunningTerminalProcess(process, command)


def run_command(command: TerminalCommand) -> TerminalResult:
    return start_command(command).wait()


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
