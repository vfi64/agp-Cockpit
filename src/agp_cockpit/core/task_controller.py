from pathlib import Path
from typing import Any

from .task_store import TaskStore
from .task_contract import LocalTaskContract


class DurableTaskController:
    def __init__(self, task_id: str, store_path: str | Path, *, local_contract: LocalTaskContract | None = None):
        self.task_id = task_id
        self.store = TaskStore(store_path)
        self.store.ensure_task(task_id)
        self.local_contract = local_contract
        if local_contract is not None:
            self.store.set_task_authority(task_id, repository_root=local_contract.repository_root, allowed_effects=local_contract.allowed_effects, allowed_tools=local_contract.allowed_tools, allow_network=local_contract.allow_network)

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

    @staticmethod
    def negotiate_remote_context_version(client_versions) -> int:
        supported = {2}
        offered = {int(v) for v in client_versions}
        common = supported & offered
        if not common:
            raise RuntimeError("REMOTE_CONTEXT_CAPABILITY_MISMATCH")
        return max(common)

    def bind_remote_context(self, conversation_ref: str) -> int:
        if not conversation_ref:
            raise ValueError("conversation_ref required")
        row = self.store.db.execute(
            "SELECT COALESCE(MAX(binding_epoch),0) AS epoch FROM remote_bindings WHERE task_id=?",
            (self.task_id,),
        ).fetchone()
        epoch = int(row["epoch"]) + 1
        with self.store.db:
            self.store.db.execute(
                "UPDATE remote_bindings SET status='STALE' WHERE task_id=? AND status='ACTIVE'",
                (self.task_id,),
            )
            self.store.db.execute(
                "INSERT INTO remote_bindings(task_id,binding_epoch,conversation_ref,status) VALUES(?,?,?,'ACTIVE')",
                (self.task_id, epoch, conversation_ref),
            )
        return epoch

    def active_remote_binding(self):
        row = self.store.db.execute(
            "SELECT binding_epoch,conversation_ref,status FROM remote_bindings WHERE task_id=? AND status='ACTIVE' ORDER BY binding_epoch DESC LIMIT 1",
            (self.task_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def binding_has_execution_authority(self, binding_epoch: int) -> bool:
        active = self.active_remote_binding()
        return bool(active and int(active["binding_epoch"]) == int(binding_epoch))

    def remote_context_refresh(self) -> dict:
        active = self.active_remote_binding()
        if active is None:
            raise RuntimeError("REMOTE_BINDING_REQUIRED")
        task = self.snapshot
        control = self.control_snapshot
        return {
            "task_id": self.task_id,
            "binding_epoch": int(active["binding_epoch"]),
            "conversation_ref": active["conversation_ref"],
            "state": task["state"],
            "execution_state": task["execution_state"],
            "governance_state": task["governance_state"],
            "suspension_reason": task["suspension_reason"],
            "remote_rounds_used": task["remote_rounds_used"],
            "local_actions_used": task["local_actions_used"],
            "retries_used": task["retries_used"],
            "no_progress_rounds": task["no_progress_rounds"],
            "controller_generation": task["controller_generation"],
            "checkpoint_id": control["checkpoint_id"],
            "checkpoint_revision": control["checkpoint_revision"],
            "checkpoint_artifact_hash": control["checkpoint_artifact_hash"],
            "approved_checkpoint_id": control["approved_checkpoint_id"],
            "approved_revision": control["approved_revision"],
            "approved_artifact_hash": control["approved_artifact_hash"],
            "goal_scope_deadline": self.store.runtime_contract(self.task_id),
            "authority": self.store.task_authority(self.task_id),
            "evidence": [
                dict(row) for row in self.store.db.execute(
                    "SELECT action_id,outcome,summary,governance_blocked FROM evidence WHERE task_id=? ORDER BY evidence_id",
                    (self.task_id,),
                ).fetchall()
            ],
            "open_effects": [
                dict(row) for row in self.store.db.execute(
                    "SELECT action_id,status,payload_json FROM actions WHERE task_id=? AND status NOT IN "
                    "('PASS','FAIL','BLOCKED','RECONCILED_APPLIED','RECONCILED_NOT_APPLIED') ORDER BY action_id",
                    (self.task_id,),
                ).fetchall()
            ],
            "approvals": {
                "checkpoint_id": control["approved_checkpoint_id"],
                "revision": control["approved_revision"],
                "artifact_hash": control["approved_artifact_hash"],
            },
            "budgets": {
                "remote_rounds_used": task["remote_rounds_used"],
                "local_actions_used": task["local_actions_used"],
                "retries_used": task["retries_used"],
                "no_progress_rounds": task["no_progress_rounds"],
                "max_remote_rounds": control["max_remote_rounds"],
                "max_local_actions": control["max_local_actions"],
                "max_no_progress_rounds": control["max_no_progress_rounds"],
            },
            "completion_contract": self.completion_contract(),
        }

    def accept_remote_action(self, action_id: str, payload: Any, predecessor_action_id: str | None = None):
        from datetime import datetime, timezone
        self.store.require_deadline_open(self.task_id, datetime.now(timezone.utc).isoformat())
        active = self.active_remote_binding()
        epoch = 0
        if active is not None:
            # Admission binds the action to the current authoritative epoch.
            # Existing protocol callers may omit the explicit epoch.
            epoch = int(active["binding_epoch"])
            if isinstance(payload, dict) and "binding_epoch" in payload:
                epoch = int(payload["binding_epoch"])
                if not self.binding_has_execution_authority(epoch):
                    raise PermissionError("stale remote binding")
        elif isinstance(payload, dict) and "binding_epoch" in payload:
            raise PermissionError("remote binding required for binding_epoch action")

        mode = self.store.register_action(self.task_id, action_id, payload, predecessor_action_id)
        if mode == "NEW":
            try:
                with self.store.db:
                    self.store.reserve_action_budgets(self.task_id, action_id, epoch)
                    self.store.consume_remote_round_reservation(self.task_id, action_id)
            except Exception:
                with self.store.db:
                    self.store.db.execute(
                        "DELETE FROM messages WHERE task_id=? AND action_id=? AND direction='IN'",
                        (self.task_id, action_id),
                    )
                    self.store.db.execute(
                        "DELETE FROM actions WHERE task_id=? AND action_id=?",
                        (self.task_id, action_id),
                    )
                raise
        return mode

    def begin_attempt(self, action_id):
        return self.store.begin_attempt(self.task_id, action_id)

    def set_task_authority(self,*,repository_root,allowed_effects,allowed_tools,allow_network=False):self.store.set_task_authority(self.task_id,repository_root=repository_root,allowed_effects=allowed_effects,allowed_tools=allowed_tools,allow_network=allow_network)
    def action_authorized(self,payload):
        import json
        a=self.store.task_authority(self.task_id)
        if a is None or not isinstance(payload,dict):return False
        if str(payload.get("effect") or "") not in set(json.loads(a["allowed_effects_json"])):return False
        argv=payload.get("argv") or []
        if not argv or Path(str(argv[0])).name not in set(json.loads(a["allowed_tools_json"])):return False
        tool=Path(str(argv[0])).name
        if tool in {"curl","wget","ssh","scp"} and not bool(a.get("allow_network",0)):return False
        if payload.get("cwd") is not None:
            try:Path(str(payload["cwd"])).expanduser().resolve().relative_to(Path(a["repository_root"]))
            except ValueError:return False
        return True
    def record_kit_result(self,evidence):self.store.record_kit_evidence(self.task_id,evidence,trusted=False,acquisition_source="caller")
    def record_verified_kit_result(self,evidence,*,acquisition_source):
        if not acquisition_source:raise ValueError("trusted evidence acquisition source required")
        self.store.record_kit_evidence(self.task_id,evidence,trusted=True,acquisition_source=acquisition_source)
    def acquire_and_record_verified_kit_result(self,action_id,run,*,repository_root):
        from .work_order_runner import acquire_trusted_kit_evidence
        evidence=acquire_trusted_kit_evidence(action_id,run,repository_root=Path(repository_root))
        self.record_verified_kit_result(evidence,acquisition_source="local-kit-execution")
        return evidence

    def authorize_kit_recovery(self, blocked_action_id: str, requested_command) -> tuple[str, ...]:
        evidence=self.store.kit_evidence_for(self.task_id,blocked_action_id)
        if not evidence or evidence["status"]!="BLOCKED":
            raise ValueError("Kit BLOCKED evidence required")
        if not evidence["recoverable"] or not evidence["recovery_command_json"]:
            raise PermissionError("non-resolvable Kit gate requires suspension")
        import json
        allowed=tuple(json.loads(evidence["recovery_command_json"])); requested=tuple(requested_command)
        if requested!=allowed or not requested or requested[0]!="agentic-kit":
            raise PermissionError("only the evidenced Kit recovery path is authorized")
        return requested

    def kit_pass_matches(self, action_id: str, revision: str, artifact_hash: str, raw_hash: str) -> bool:
        evidence = self.store.kit_evidence_for(self.task_id, action_id)
        action = self.store.db.execute(
            "SELECT status FROM actions WHERE task_id=? AND action_id=?",
            (self.task_id, action_id),
        ).fetchone()
        return bool(
            action and action["status"] == "PASS"
            and evidence and evidence["status"] == "PASS"
            and evidence["producer"] == "agentic-project-kit"
            and evidence["revision"] == revision
            and evidence["artifact_hash"] == artifact_hash
            and evidence["raw_hash"] == raw_hash
        )


    def record_local_result(self, action_id, attempt_no, outcome, summary, governance_blocked=False):
        self.store.record_result(
            self.task_id, action_id, attempt_no, outcome, summary, governance_blocked
        )

    def mark_outcome_unknown(self, action_id, attempt_no, reason):
        self.store.mark_unknown(self.task_id, action_id, attempt_no, reason)

    def reconcile(self, action_id, conclusion):
        self.store.reconcile(self.task_id, action_id, conclusion)

    def recover_interrupted_dispatches(self):
        return self.store.recover_interrupted_dispatches(self.task_id)

    def wait_for_service(self, reason: str = ""):
        self.store.wait_for_service(self.task_id)

    def service_recovered(self):
        self.store.service_recovered(self.task_id)

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

    def set_completion_contract(self, revision, artifact_hash, required_kit_action_id, required_kit_raw_hash, *, human_checkpoint_required=False):
        if not all((revision, artifact_hash, required_kit_action_id, required_kit_raw_hash)):
            raise ValueError("complete completion-contract identity required")
        with self.store.db:
            self.store.db.execute(
                "INSERT INTO completion_contracts(task_id,revision,artifact_hash,required_kit_action_id,required_kit_raw_hash,human_checkpoint_required,status,rejection_reason) VALUES(?,?,?,?,?,?,'ACTIVE',NULL) "
                "ON CONFLICT(task_id) DO UPDATE SET revision=excluded.revision,artifact_hash=excluded.artifact_hash,required_kit_action_id=excluded.required_kit_action_id,required_kit_raw_hash=excluded.required_kit_raw_hash,human_checkpoint_required=excluded.human_checkpoint_required,status='ACTIVE',rejection_reason=NULL",
                (self.task_id, revision, artifact_hash, required_kit_action_id, required_kit_raw_hash, 1 if human_checkpoint_required else 0),
            )

    def completion_contract(self):
        row = self.store.db.execute("SELECT * FROM completion_contracts WHERE task_id=?", (self.task_id,)).fetchone()
        return dict(row) if row is not None else None

    def verify_completion_contract(self):
        contract = self.completion_contract()
        if self.snapshot["state"] != "COMPLETE_PROPOSED":
            return False
        reason = None
        if contract is None:
            reason = "MISSING_COMPLETION_CONTRACT"
        elif self.snapshot["governance_state"] != "CLEAR":
            reason = "GOVERNANCE_NOT_CLEAR"
        elif self.snapshot["execution_state"] in {"RUNNING", "OUTCOME_UNKNOWN", "BLOCKED"}:
            reason = "EXECUTION_NOT_SETTLED"
        elif (lambda ev: ev is not None and int(ev.get("trusted",0)) != 1)(self.store.kit_evidence_for(self.task_id, contract["required_kit_action_id"])):
            reason = "UNTRUSTED_KIT_EVIDENCE"
        elif not self.kit_pass_matches(contract["required_kit_action_id"], contract["revision"], contract["artifact_hash"], contract["required_kit_raw_hash"]):
            reason = "MISSING_OR_STALE_KIT_PASS"
        elif int(contract["human_checkpoint_required"]) and not self.checkpoint_approved_for(contract["revision"], contract["artifact_hash"]):
            reason = "MISSING_OR_STALE_HUMAN_APPROVAL"
        with self.store.db:
            self.store.db.execute("UPDATE completion_contracts SET status=?,rejection_reason=? WHERE task_id=?", ("VERIFIED" if reason is None else "REJECTED", reason, self.task_id))
        self.store.set_states(self.task_id, state="VERIFIED_COMPLETE" if reason is None else "WAITING_FOR_REMOTE")
        return reason is None

    def propose_complete(self):
        if self.snapshot["state"] in {"CANCELLED", "SUSPENDED"}:
            return False
        self.store.set_states(self.task_id, state="COMPLETE_PROPOSED")
        return True

    def verify_complete(self, passed):
        if self.snapshot["state"] != "COMPLETE_PROPOSED":
            return False
        self.store.set_states(self.task_id, state="WAITING_FOR_REMOTE")
        return False


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
