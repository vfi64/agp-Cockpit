from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agp_cockpit.core.terminal_exec import TerminalCommand, TerminalResult


@dataclass(frozen=True)
class LocalWorkOrder:
    argv: tuple[str, ...]
    cwd: Path
    timeout_seconds: float = 120.0
    label: str = "Lokaler Auftrag"
    kind: str = "generic"

    def to_terminal_command(self) -> TerminalCommand:
        return TerminalCommand(
            argv=self.argv,
            cwd=self.cwd,
            timeout_seconds=self.timeout_seconds,
        )


def parse_work_order_json(text: str) -> LocalWorkOrder:
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Ungültiges JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise TypeError("Work Order muss ein JSON-Objekt sein")

    argv = data.get("argv")
    cwd = data.get("cwd")
    timeout = data.get("timeout_seconds", 120.0)
    label = data.get("label", "Lokaler Auftrag")
    kind = data.get("kind", "generic")

    if not isinstance(argv, list) or not argv:
        raise ValueError("argv muss eine nichtleere JSON-Liste sein")
    if any(not isinstance(x, str) or not x for x in argv):
        raise ValueError("argv darf nur nichtleere Strings enthalten")
    if not isinstance(cwd, str) or not cwd.strip():
        raise ValueError("cwd muss als Pfad angegeben sein")
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("timeout_seconds muss positiv sein")
    if not isinstance(label, str):
        raise TypeError("label muss ein String sein")
    if kind not in {"generic", "kit"}:
        raise ValueError("kind muss 'generic' oder 'kit' sein")

    if kind == "kit" and Path(argv[0]).name != "agentic-kit":
        raise ValueError(
            "kind='kit' requires argv[0] to be agentic-kit"
        )

    return LocalWorkOrder(
        argv=tuple(argv),
        cwd=Path(cwd).expanduser(),
        timeout_seconds=float(timeout),
        label=label,
        kind=kind,
    )


def format_result_block(
    order: LocalWorkOrder,
    result: TerminalResult,
) -> str:
    line = "=" * 79
    stdout = result.stdout.rstrip()
    stderr = result.stderr.rstrip()

    parts = [
        line,
        line,
        "=== BEGINN ERGEBNISBLOCK – BITTE AB HIER KOPIEREN ===",
        f"=== {order.label} ===",
        line,
        line,
        f"KIND={order.kind}",
        f"CWD={result.cwd}",
        f"ARGV={list(result.argv)!r}",
        f"RC={result.returncode}",
        f"TIMED_OUT={'true' if result.timed_out else 'false'}",
        f"DURATION_SECONDS={result.duration_seconds:.3f}",
        "",
        "STDOUT:",
        stdout if stdout else "<leer>",
        "",
        "STDERR:",
        stderr if stderr else "<leer>",
        line,
        "=== ENDE ERGEBNISBLOCK ===",
        line,
    ]
    return "\n".join(parts)
