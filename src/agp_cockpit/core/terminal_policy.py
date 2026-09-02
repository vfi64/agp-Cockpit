from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.terminal_exec import TerminalCommand


@dataclass(frozen=True)
class ExecutionPolicy:
    repository_root: Path
    allow_external_cwd: bool = False

    def validate(self, command: TerminalCommand) -> None:
        command.validate()

        repo = self.repository_root.resolve()
        cwd = command.cwd.resolve()

        if not self.allow_external_cwd:
            try:
                cwd.relative_to(repo)
            except ValueError as exc:
                raise PermissionError(
                    f"cwd outside configured repository: {cwd}"
                ) from exc

        executable = Path(command.argv[0]).name
        if executable in {"sudo", "su"}:
            raise PermissionError(
                f"privilege escalation command is not allowed: {executable}"
            )
