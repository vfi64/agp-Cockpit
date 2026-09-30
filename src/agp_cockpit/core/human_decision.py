"""Human decisions on NEEDS_HUMAN questions and the one-shot approval.

AGP_HUMAN_DECISION_V1
A remote NEEDS_HUMAN ends the mission with a question. The human answers in
the desktop app (approve or reject, optional note). The answer continues the
same task in the same conversation. An approval is a one-shot grant: it lets
exactly one following work order of that task use Kit commands with a remote
effect (AGP_REMOTE_EFFECT_GATE_V1); it is consumed on use and expires.
Raw git push/fetch/pull stay forbidden regardless.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

DECISIONS = frozenset({"APPROVE", "REJECT"})
GRANT_TTL_SECONDS = 24 * 3600


class HumanDecisionStore:
    def __init__(self, runtime_root: Path) -> None:
        self.path = Path(runtime_root) / "human-decision.json"

    def current(self) -> dict:
        if not self.path.is_file():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, sort_keys=True, indent=1), encoding="utf-8")
        temporary.replace(self.path)

    def record(self, *, mission_id: str, task_id: str, decision: str, question: str,
               note: str = "", now: float | None = None) -> dict:
        decision = str(decision or "").upper()
        if decision not in DECISIONS:
            raise ValueError("decision must be APPROVE or REJECT")
        if not mission_id or not task_id:
            raise ValueError("decision requires the mission and its task")
        record = {
            "mission_id": mission_id,
            "task_id": task_id,
            "decision": decision,
            "question": " ".join(str(question or "").split())[:2000],
            "note": " ".join(str(note or "").split())[:2000],
            "decided_at": time.time() if now is None else now,
            "grant": None,
        }
        if decision == "APPROVE":
            record["grant"] = {"effect": "remote", "remaining": 1, "consumed_by": None}
        self._save(record)
        return record

    def remote_effects_allowed(self, task_id: str, now: float | None = None) -> bool:
        record = self.current()
        grant = record.get("grant") or {}
        age = (time.time() if now is None else now) - float(record.get("decided_at") or 0)
        return bool(
            task_id
            and record.get("task_id") == task_id
            and grant.get("remaining", 0) > 0
            and age <= GRANT_TTL_SECONDS
        )

    def consume(self, task_id: str, command_sha256: str) -> dict:
        record = self.current()
        grant = record.get("grant") or {}
        if record.get("task_id") != task_id or grant.get("remaining", 0) <= 0:
            raise ValueError("no approval available to consume")
        grant["remaining"] = 0
        grant["consumed_by"] = command_sha256
        record["grant"] = grant
        self._save(record)
        return record


def decision_mission_text(*, goal_text: str, decision: str, question: str, note: str) -> str:
    """Mission text that continues the same task after the human decision."""
    decision = str(decision).upper()
    if decision == "APPROVE":
        verdict = (
            "APPROVED. The approval authorizes remote-effect Kit commands (e.g. a push through "
            "`agentic-kit transfer push-current`) for exactly the next work order of this task. "
            "Raw git push, git fetch and git pull stay forbidden."
        )
    else:
        verdict = (
            "REJECTED. Do not perform the remote effect. Finish the task, or ask a new "
            "question with NEEDS_HUMAN if another decision is required."
        )
    return (
        "HUMAN DECISION — continuation of the same task in this conversation.\n\n"
        f"Your question was: {question or '—'}\n"
        f"Decision: {verdict}\n"
        f"Human note: {note or '—'}\n\n"
        "Original task (unchanged):\n" + str(goal_text or "")
    )
