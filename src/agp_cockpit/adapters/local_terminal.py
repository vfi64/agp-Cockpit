from __future__ import annotations

import subprocess
import time

from agp_cockpit.core.terminal_exec import (
    TerminalCommand,
    TerminalResult,
    preview_command,
)


class _RunningSubprocess:
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


def start_subprocess_command(command: TerminalCommand) -> _RunningSubprocess:
    command.validate()
    process = subprocess.Popen(
        list(command.argv),
        cwd=str(command.cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    return _RunningSubprocess(process, command)


class SubprocessTerminalAdapter:
    """Concrete local TerminalPort implementation backed by subprocess."""

    def preview(self, command: TerminalCommand) -> str:
        return preview_command(command)

    def execute(self, command: TerminalCommand) -> TerminalResult:
        return start_subprocess_command(command).wait()
