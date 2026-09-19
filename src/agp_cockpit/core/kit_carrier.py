from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.work_order import LocalWorkOrder


@dataclass(frozen=True)
class KitAuthorityResult:
    is_kit_command: bool
    command_for_returncode: int | None
    command_for_stdout: str
    command_for_stderr: str
    accepted: bool
    reason: str


def _is_agentic_kit_argv(argv: tuple[str, ...]) -> bool:
    if not argv:
        return False
    executable = Path(argv[0]).name
    return executable == "agentic-kit"


def inspect_kit_authority(
    order: LocalWorkOrder,
    *,
    kit_binary: Path,
) -> KitAuthorityResult:
    if not _is_agentic_kit_argv(order.argv):
        return KitAuthorityResult(
            is_kit_command=False,
            command_for_returncode=None,
            command_for_stdout="",
            command_for_stderr="",
            accepted=True,
            reason="generic diagnostic/fallback command",
        )

    raw = " ".join(order.argv)

    completed = subprocess.run(
        [
            str(kit_binary),
            "command-for",
            "--raw",
            raw,
            "--root",
            str(order.cwd),
            "--json",
        ],
        cwd=order.cwd,
        text=True,
        capture_output=True,
        check=False,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if completed.returncode != 0:
        return KitAuthorityResult(
            is_kit_command=True,
            command_for_returncode=completed.returncode,
            command_for_stdout=stdout,
            command_for_stderr=stderr,
            accepted=False,
            reason="agentic-kit command-for rejected or failed",
        )

    accepted = True
    reason = "current Kit authority consulted successfully"

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        data = None

    if isinstance(data, dict):
        status = str(data.get("status", "")).casefold()
        if status in {"unknown", "unknown_tag", "blocked", "fail"}:
            accepted = False
            reason = f"command-for status={status}"

    return KitAuthorityResult(
        is_kit_command=True,
        command_for_returncode=completed.returncode,
        command_for_stdout=stdout,
        command_for_stderr=stderr,
        accepted=accepted,
        reason=reason,
    )


def require_kit_authority(
    order: LocalWorkOrder,
    *,
    kit_binary: Path,
) -> KitAuthorityResult:
    result = inspect_kit_authority(
        order,
        kit_binary=kit_binary,
    )
    if result.is_kit_command and not result.accepted:
        raise PermissionError(
            f"Kit command not accepted by current authority check: {result.reason}"
        )
    return result
