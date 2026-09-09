from pathlib import Path
from typing import Any

from .task_store import TaskStore


class DurableTaskController:
    def __init__(self, task_id: str, store_path: str | Path):
        self.task_id = task_id
        self.store = TaskStore(store_path)
        self.store.ensure_task(task_id)

    def close(self):
        self.store.close()

    @property
    def snapshot(self):
        row = dict(self.store.task_row(self.task_id))
        row["suspension_reason"] = self.store.suspension_reason(self.task_id)
        return row

    @property
    def control_snapshot(self):
        return dict(self.store.control_row(self.task_id))

    def set_limits(self, *, max_remote_rounds=None, max_local_actions=None, max_no_progress_rounds=None):
        self.store.set_limits(
            self.task_id,
            max_remote_rounds=max_remote_rounds,
            max_local_actions=max_local_actions,
            max_no_progress_rounds=max_no_progress_rounds,
        )

    def accept_remote_action(self, action_id: str, payload: Any, predecessor_action_id: str | None = None):
        mode = self.store.register_action(self.task_id, action_id, payload, predecessor_action_id)
        if mode == "NEW":
            self.store.bump(self.task_id, "remote_rounds_used")
        return mode

    def begin_attempt(self, action_id):
        return self.store.begin_attempt(self.task_id, action_id)

    def record_local_result(self, action_id, attempt_no, outcome, summary, governance_blocked=False):
        self.store.record_result(
            self.task_id, action_id, attempt_no, outcome, summary, governance_blocked
        )

    def mark_outcome_unknown(self, action_id, attempt_no, reason):
        self.store.mark_unknown(self.task_id, action_id, attempt_no, reason)

    def reconcile(self, action_id, conclusion):
        self.store.reconcile(self.task_id, action_id, conclusion)

    def pending_results(self):
        return [dict(row) for row in self.store.pending_outbox(self.task_id)]

    def mark_result_delivered(self, message_id):
        self.store.mark_delivered(message_id)

    def request_human_checkpoint(self, checkpoint_id: str, revision: str, artifact_hash: str):
        self.store.request_checkpoint(self.task_id, checkpoint_id, revision, artifact_hash)

    def approve_human_checkpoint(self, checkpoint_id: str, revision: str, artifact_hash: str):
        self.store.approve_checkpoint(self.task_id, checkpoint_id, revision, artifact_hash)

    def checkpoint_approved_for(self, revision: str, artifact_hash: str):
        return self.store.checkpoint_approved_for(self.task_id, revision, artifact_hash)

    def pause(self):
        self.store.pause(self.task_id)

    def resume(self):
        self.store.resume(self.task_id)

    def cancel(self):
        self.store.cancel(self.task_id)

    def observe_progress(self, fingerprint: str):
        return self.store.observe_progress(self.task_id, fingerprint)

    def propose_complete(self):
        if self.snapshot["state"] in {"CANCELLED", "SUSPENDED"}:
            return False
        self.store.set_states(self.task_id, state="COMPLETE_PROPOSED")
        return True

    def verify_complete(self, passed):
        if self.snapshot["state"] != "COMPLETE_PROPOSED":
            return False
        self.store.set_states(
            self.task_id,
            state="VERIFIED_COMPLETE" if passed else "WAITING_FOR_REMOTE",
        )
        return bool(passed)


from dataclasses import dataclass, field
from .task_models import Evidence, ExecutionState, GovernanceState, TaskState


@dataclass
class TaskController:
    task_state: TaskState = TaskState.ACTIVE
    execution_state: ExecutionState = ExecutionState.IDLE
    governance_state: GovernanceState = GovernanceState.CLEAR
    seen_action_ids: set[str] = field(default_factory=set)
    evidence: list[Evidence] = field(default_factory=list)

    def accept_remote_action(self, action_id: str) -> bool:
        if (
            self.task_state in {TaskState.VERIFIED_COMPLETE, TaskState.CANCELLED}
            or action_id in self.seen_action_ids
        ):
            return False
        self.seen_action_ids.add(action_id)
        self.execution_state = ExecutionState.RUNNING
        self.task_state = TaskState.ACTIVE
        return True

    def record_local_result(self, action_id: str, outcome: str, summary: str, governance_blocked: bool = False) -> None:
        if action_id not in self.seen_action_ids:
            raise ValueError("unknown action_id")
        normalized = outcome.upper()
        if normalized not in {"PASS", "FAIL", "BLOCKED"}:
            raise ValueError("unsupported outcome")
        self.evidence.append(Evidence(action_id, normalized, summary, governance_blocked))
        self.execution_state = {
            "PASS": ExecutionState.SUCCEEDED,
            "FAIL": ExecutionState.FAILED,
            "BLOCKED": ExecutionState.BLOCKED,
        }[normalized]
        self.governance_state = (
            GovernanceState.BLOCKED
            if governance_blocked or normalized == "BLOCKED"
            else GovernanceState.CLEAR
        )
        self.task_state = TaskState.WAITING_FOR_REMOTE

    def propose_complete(self) -> None:
        self.task_state = TaskState.COMPLETE_PROPOSED

    def verify_complete(self, passed: bool) -> bool:
        if self.task_state is not TaskState.COMPLETE_PROPOSED:
            return False
        if passed:
            self.task_state = TaskState.VERIFIED_COMPLETE
            return True
        self.task_state = TaskState.WAITING_FOR_REMOTE
        return False
