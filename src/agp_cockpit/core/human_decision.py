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

AGP_CI_GREEN_COMPLETION_V1: an approval also carries a bounded repair budget.
Once the task published work, the Cockpit accepts DONE only when GitHub is
verified green (ci_gate); repairing needs further runs. Within the same
continuation mission up to REPAIR_BUDGET further work orders may re-run the
Kit commands the approval already ran, the push/PR primitives and, after an
approved merging orchestrator, the publishing and closeout commands of that
lifecycle, without asking again. Every other remote effect still needs a new
decision. The approval text never prescribes a Kit command: the remote side
chooses from the digest, orchestrators first (live 1501-1519).

AGP_START_CLICK_APPROVAL_V1 (plan P5/P6, R4): a standard task whose start
click is the approval records a pre-approval before its first mission. It is
claimed by that mission and limited to the task's declared ``scope`` of
remote-effect commands for every work order (first and repair); any other
remote effect still asks. Every consumption is logged with its step and
commands so the UI can show the auto-approved effects.
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
               note: str = "", now: float | None = None, scope=None) -> dict:
        decision = str(decision or "").upper()
        if decision not in DECISIONS:
            raise ValueError("decision must be APPROVE or REJECT")
        if not mission_id or not task_id:
            raise ValueError("decision requires the mission and its task")
        previous = self.current()
        record = {
            "mission_id": mission_id,
            "task_id": task_id,
            # AGP_EFFECTS_LOG_CONTINUITY_V1 (live 2026-10-04, steps 1676/1680): a later
            # decision of the same task replaced the record and the UI claimed that
            # no approved effect had run, although step 1676 had run one.
            "effects": list(_effects_of(previous)) if previous.get("task_id") == task_id else [],
            "decision": decision,
            "question": " ".join(str(question or "").split())[:2000],
            "note": " ".join(str(note or "").split())[:2000],
            "decided_at": time.time() if now is None else now,
            "grant": None,
        }
        if decision == "APPROVE":
            from agp_cockpit.core.ci_gate import REPAIR_BUDGET
            record["grant"] = {"effect": "remote", "remaining": 1,
                               "repair_pushes": REPAIR_BUDGET, "consumed_by": None}
            if scope is not None:
                record["grant"]["scope"] = sorted(scope)
        self._save(record)
        return record

    def pre_approve(self, *, task_id: str, label: str, scope, now: float | None = None) -> dict:
        """AGP_START_CLICK_APPROVAL_V1: the start click approves ``scope``."""
        if not scope:
            raise ValueError("a start-click approval needs a declared scope")
        return self.record(mission_id=f"pre-approval:{task_id}", task_id=task_id,
                           decision="APPROVE", now=now, scope=scope,
                           question=f"Start von „{label}“ — Freigabe durch den Start-Klick")

    def effects_log(self, task_id: str) -> list[dict]:
        record = self.current()
        if record.get("task_id") != task_id:
            return []
        return list(_effects_of(record))

    def remote_effects_allowed(self, task_id: str, now: float | None = None) -> bool:
        """True while any part of the task's approval is open."""
        record = self.current()
        grant = record.get("grant") or {}
        age = (time.time() if now is None else now) - float(record.get("decided_at") or 0)
        return bool(
            task_id
            and record.get("task_id") == task_id
            and (grant.get("remaining", 0) > 0 or grant.get("repair_pushes", 0) > 0)
            and age <= GRANT_TTL_SECONDS
        )

    def permits(self, task_id: str, wanted, *, ci_gate_active: bool,
                now: float | None = None) -> bool:
        """Whether the open approval covers exactly these remote-effect commands.

        The first executed work order may use any remote effect (the asked
        action). Afterwards the repair budget covers the Kit commands that the
        approval already ran, the push/PR primitives and, when the approved
        run merges, the publishing and closeout commands of that lifecycle.
        """
        from agp_cockpit.core.ci_gate import (
            LIFECYCLE_COMMANDS,
            MERGE_COMMANDS,
            REPAIR_PUSH_COMMANDS,
        )
        if not self.remote_effects_allowed(task_id, now=now):
            return False
        grant = self.current().get("grant") or {}
        if grant.get("scope") is not None:
            return bool(wanted) and set(wanted) <= set(grant["scope"])
        if grant.get("remaining", 0) > 0:
            return True
        approved = set(grant.get("approved_commands") or ())
        allowed = set(REPAIR_PUSH_COMMANDS) | approved
        if approved & MERGE_COMMANDS:
            allowed |= LIFECYCLE_COMMANDS
        return bool(
            ci_gate_active
            and grant.get("repair_pushes", 0) > 0
            and wanted
            and set(wanted) <= allowed
        )

    def _expire(self, record: dict, *, mission_id: str, reason: str) -> None:
        grant = record["grant"]
        grant["remaining"] = 0
        grant["repair_pushes"] = 0
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
        return {"effect": "remote", "remaining": grant.get("remaining", 0),
                "repair_pushes": grant.get("repair_pushes", 0),
                "question": record.get("question", ""), "note": record.get("note", ""),
                "scope": list(grant.get("scope") or ())}

    def consume(self, task_id: str, command_sha256: str, used=(), step: int | None = None,
                now: float | None = None) -> dict:
        record = self.current()
        grant = record.get("grant") or {}
        if record.get("task_id") != task_id or (
            grant.get("remaining", 0) <= 0 and grant.get("repair_pushes", 0) <= 0
        ):
            raise ValueError("no approval available to consume")
        if grant.get("remaining", 0) > 0:
            grant["remaining"] = 0
            grant["approved_commands"] = sorted(set(used))
        else:
            grant["repair_pushes"] = int(grant.get("repair_pushes", 0)) - 1
        grant["consumed_by"] = command_sha256
        grant["consumed"] = [*grant.get("consumed", []), command_sha256]
        entry = {"at": time.time() if now is None else now, "step": step,
                 "commands": sorted(set(used)), "command_sha256": command_sha256,
                 # AGP_EFFECTS_BY_APPROVAL_V1: start click or decision box
                 "source": "start" if str(record.get("mission_id", "")).startswith("pre-approval:")
                 else "decision"}
        record["effects"] = [*_effects_of(record), entry]
        grant["log"] = [*grant.get("log", []), entry]
        record["grant"] = grant
        self._save(record)
        return record


def _effects_of(record: dict) -> list[dict]:
    """Every approved effect of the record's task, also from earlier decisions."""
    if "effects" in record:
        return list(record.get("effects") or [])
    return list((record.get("grant") or {}).get("log") or [])   # records before the field


def decision_mission_text(*, goal_text: str, decision: str, question: str, note: str) -> str:
    """Mission text that continues the same task after the human decision."""
    decision = str(decision).upper()
    if decision == "APPROVE":
        verdict = (
            "APPROVED. The human approves exactly the action asked about above.\n"
            "- This approval supersedes any \"prepare only\", \"do not execute\" or similar "
            "restriction in the original task, for exactly this approved action.\n"
            "- Your next work order MUST perform the approved action now and report its real "
            "result in the return bundle. Choose the Kit command yourself from the attached "
            "command digest: the most comprehensive orchestrator that covers the approved action "
            "and the lifecycle the task asks for (publishing, CI, and a merge with its post-merge "
            "closeout when the task includes one) in one run; use primitives only where no "
            "orchestrator fits.\n"
            "- For that work order the local authority allows remote-effect Kit commands and "
            "network access (allow_network=true). Afterwards, within this mission, a bounded "
            "repair budget lets you re-run the approved Kit commands and the publishing and "
            "closeout commands of the same lifecycle to fix failures without asking again. The "
            "approval expires when this mission ends.\n"
            "- Do not ask for the same approval again. Raw git push, git fetch, git pull and gh "
            "stay forbidden.\n"
            "- Completion is verified locally by the Cockpit: a task that published work is DONE "
            "only when the pull request CI is green for the local HEAD and, if the task includes "
            "a merge, the pull request is merged, local main is synchronized, the Kit post-merge "
            "check passes and main is green. Name the pull request as \"pr\" in the DONE file."
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
