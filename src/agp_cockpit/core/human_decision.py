"""Human decisions on NEEDS_HUMAN questions and the one-shot approval.

AGP_HUMAN_DECISION_V1
A remote NEEDS_HUMAN ends the mission with a question. The human answers in
the desktop app (approve or reject, optional note). The answer continues the
same task in the same conversation. An approval is a one-shot grant: it lets
exactly one following work order of that task use Kit commands with a remote
effect (AGP_REMOTE_EFFECT_GATE_V1); it is consumed on use and expires.
Raw git push/fetch/pull stay forbidden regardless.

AGP_HUMAN_APPROVAL_SCOPE_V2 (live test 4, steps 1489-1492): the approval
must actually enable the approved action. The continuation text orders the
approved action and lifts a "prepare only / do not execute" restriction of
the original task for exactly that action; while the grant is open the
local authority reports allow_network=true for it. A grant that the
continuation mission does not use expires when that mission ends or another
mission of the task starts.
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

    def _expire(self, record: dict, *, mission_id: str, reason: str) -> None:
        grant = record["grant"]
        grant["remaining"] = 0
        grant["expired_reason"] = reason
        grant["expired_with_mission"] = mission_id
        self._save(record)

    def grant_for_mission(self, task_id: str, mission_id: str, *, mission_ended: bool,
                          now: float | None = None) -> dict | None:
        """The open approval as seen by the current mission of the task.

        The grant belongs to the first mission after the one that asked (the
        continuation). That mission claims it; when it ends without using
        it, or another mission of the task shows up, the grant expires.
        """
        if not mission_id or not self.remote_effects_allowed(task_id, now=now):
            return None
        record = self.current()
        grant = record["grant"]
        if mission_id == record.get("mission_id"):
            return None
        claimed = grant.get("claimed_by")
        if claimed and claimed != mission_id:
            self._expire(record, mission_id=claimed,
                         reason="a later mission of the task started without using the approval")
            return None
        if mission_ended:
            self._expire(record, mission_id=mission_id,
                         reason="the continuation mission ended without using the approval")
            return None
        if not claimed:
            grant["claimed_by"] = mission_id
            self._save(record)
        return {"effect": "remote", "remaining": grant["remaining"],
                "question": record.get("question", ""), "note": record.get("note", "")}

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
            "APPROVED. The human approves exactly the action asked about above.\n"
            "- This approval supersedes any \"prepare only\", \"do not execute\" or similar "
            "restriction in the original task, for exactly this approved action.\n"
            "- Your next work order MUST perform the approved action now, through the matching "
            "Kit command from the attached command digest (for a branch push: "
            "`agentic-kit transfer push-current --branch <current branch> --json`, which sets "
            "the upstream on origin itself), and report its real result in the return bundle.\n"
            "- For exactly that one work order the local authority allows remote-effect Kit "
            "commands and network access (allow_network=true); the approval is consumed by it "
            "and expires when this mission ends.\n"
            "- Do not ask for the same approval again. Raw git push, git fetch and git pull stay "
            "forbidden; use only the Kit command."
        )
    else:
        verdict = (
            "REJECTED. Do not perform the remote effect. Finish the task, or ask a new "
            "question with NEEDS_HUMAN if another decision is required."
        )
    return (
        "HUMAN DECISION — continuation of the same task in this conversation.\n\n"
        f"The question was: {question or '—'}\n"
        f"Decision: {verdict}\n"
        f"Human note: {note or '—'}\n\n"
        + (
            "Original task (context only; the decision above takes precedence):\n"
            if decision == "APPROVE"
            else "Original task (unchanged):\n"
        )
        + str(goal_text or "")
    )
