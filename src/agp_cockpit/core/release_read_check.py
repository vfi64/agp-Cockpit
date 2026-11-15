"""The Kit's read check before the release question (AGP_RELEASE_READ_CHECK_V1, workflow-friction plan C4).

Live 2026-11-13 (V11): the owner approved Release 0.4.1, and only step A2 of the Kit's release run found that
the changelog gate rejected the Unreleased entry, after the approval. The Release task now runs that step
first: the repository's own Kit answers ``release ready --version <v> --json`` (step A2 of ``release run``;
without summary lines the Unreleased entries of a curated workspace are the summary, as in the run). The
Cockpit asks the owner only on PASS. Any other answer is shown as the Kit gives it: its stopped steps, the
check id and the resolving command with its consent flag (G3), or the Kit's reason when no Kit command
resolves it. The Cockpit judges nothing itself (SCOPE_BOUNDARY): it reads ``result_status``, ``blockers``,
``check_id`` and the route fields and never looks into the steps.

When main already names the version, the release is a resumed one (the Kit's run continues from its own
state; without release.approval: upfront only the tag is missing). The check is not run then: it would judge
a release that is already prepared.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

READ_CHECK_TIMEOUT = 1800          # the scan and the release-notes step may take minutes on a large history

PASS = "PASS"
STOPPED = "STOPPED"                # the Kit answered with anything but PASS
NO_KIT = "NO_KIT"
NO_ANSWER = "NO_ANSWER"
KIND_KIT = "kit"


@dataclass(frozen=True)
class ReadCheck:
    result: str
    status: str = ""                  # the Kit's result_status
    blockers: tuple[str, ...] = ()
    check_id: str = ""
    next_command: str = ""
    next_command_kind: str = ""
    next_command_autonomous: bool = False
    next_command_reason: str = ""
    reason: str = ""                  # why there is no Kit answer (NO_KIT, NO_ANSWER)

    @property
    def passed(self) -> bool:
        return self.result == PASS


def argv(binary: Path | str, version: str) -> list[str]:
    """Step A2 of the Kit's release run, as the run calls it without summary lines."""
    return [str(binary), "release", "ready", "--version", version, "--json"]


def needed(root: Path, version: str) -> bool:
    """False for a resumed release: main already names the version."""
    from agp_cockpit.core.standard_tasks import _current_version
    return _current_version(Path(root)) != str(version or "").strip()


def read(root: Path, version: str, runner: Callable = subprocess.run) -> ReadCheck:
    from agp_cockpit.core.kit_installation import discover
    root = Path(root)
    kit = discover(root)
    if kit is None:
        return ReadCheck(NO_KIT, reason="kein Kit installiert")
    try:
        done = runner(argv(kit.binary, version), cwd=str(root), capture_output=True, text=True,
                      timeout=READ_CHECK_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ReadCheck(NO_ANSWER, reason=f"das Kit antwortet nicht ({type(exc).__name__})")
    text = f"{getattr(done, 'stdout', '') or ''}"
    try:
        data = json.loads(text[text.index("{"):])
    except ValueError:
        data = None
    if not isinstance(data, dict) or not data.get("result_status"):
        detail = next((line.strip() for line in f"{getattr(done, 'stderr', '') or ''}".splitlines() if line.strip()), "")
        return ReadCheck(NO_ANSWER, reason="das Kit lieferte kein Ergebnis" + (f": {detail}" if detail else ""))
    status = str(data["result_status"])
    blockers = data.get("blockers")
    return ReadCheck(
        PASS if status == PASS else STOPPED,
        status=status,
        blockers=tuple(str(b) for b in blockers) if isinstance(blockers, list) else (),
        check_id=str(data.get("check_id") or ""),
        next_command=str(data.get("next_command") or ""),
        next_command_kind=str(data.get("next_command_kind") or ""),
        next_command_autonomous=data.get("next_command_autonomous") is True,
        next_command_reason=str(data.get("next_command_reason") or ""),
    )


def stop_text(check: ReadCheck, version: str) -> str:
    """German text for the window when the release does not start; the Kit's words, unjudged."""
    if check.result == NO_KIT:
        return f"Release {version} nicht gestartet: Die Lese-Prüfung des Kits ist nicht möglich ({check.reason})."
    if check.result == NO_ANSWER:
        return (f"Release {version} nicht gestartet: Die Lese-Prüfung des Kits (release ready) lieferte kein "
                f"Ergebnis ({check.reason}). Später erneut versuchen; bleibt es so, mit Claude klären.")
    lines = [f"Das Kit stoppt Release {version} schon vor dem Start (release ready: {check.status})."]
    if check.blockers:
        lines.append("Gestoppte Schritte: " + ", ".join(check.blockers))
    if check.check_id:
        lines.append(f"Prüfung: {check.check_id}")
    if check.next_command_kind == KIND_KIT and check.next_command:
        consent = ("darf ohne neue Zustimmung laufen" if check.next_command_autonomous
                   else "braucht deine Zustimmung")
        lines.append(f"Behebender Befehl laut Kit ({consent}):\n{check.next_command}")
    else:
        lines.append("Das Kit nennt keinen behebenden Befehl"
                     + (f": {check.next_command_reason}" if check.next_command_reason else "."))
    lines.append("Nichts wurde gestartet und nichts gefragt. Nach der Behebung „Release“ erneut klicken.")
    return "\n\n".join(lines)
