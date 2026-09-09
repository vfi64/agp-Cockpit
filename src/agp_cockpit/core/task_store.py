from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SUSPENSION_REASONS = {
    "WAITING_FOR_HUMAN",
    "USER_PAUSED",
    "BUDGET_EXHAUSTED",
    "STALLED",
    "WAITING_FOR_SERVICE",
    "SAFETY_BLOCK",
    "OUTCOME_UNKNOWN",
    "STORAGE_BLOCKED",
}


@dataclass(frozen=True)
class StoredAction:
    task_id: str
    action_id: str
    payload_hash: str
    payload_json: str
    status: str
    attempt_count: int
    predecessor_action_id: str | None


class TaskStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self._init()

    def close(self):
        self.db.close()

    def _init(self):
        with self.db:
            self.db.executescript(
                '''
CREATE TABLE IF NOT EXISTS metadata(
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks(
    task_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    execution_state TEXT NOT NULL,
    governance_state TEXT NOT NULL,
    remote_rounds_used INTEGER NOT NULL DEFAULT 0,
    local_actions_used INTEGER NOT NULL DEFAULT 0,
    retries_used INTEGER NOT NULL DEFAULT 0,
    no_progress_rounds INTEGER NOT NULL DEFAULT 0,
    controller_generation INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS actions(
    task_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    predecessor_action_id TEXT,
    PRIMARY KEY(task_id, action_id),
    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);
CREATE TABLE IF NOT EXISTS attempts(
    task_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    attempt_no INTEGER NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    PRIMARY KEY(task_id, action_id, attempt_no),
    FOREIGN KEY(task_id, action_id) REFERENCES actions(task_id, action_id)
);
CREATE TABLE IF NOT EXISTS messages(
    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    direction TEXT NOT NULL,
    kind TEXT NOT NULL,
    action_id TEXT,
    payload_json TEXT NOT NULL,
    delivered INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);
CREATE TABLE IF NOT EXISTS kit_evidence(
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    status TEXT NOT NULL,
    producer TEXT NOT NULL,
    command_json TEXT NOT NULL,
    revision TEXT NOT NULL,
    artifact_hash TEXT NOT NULL,
    raw_hash TEXT NOT NULL,
    recoverable INTEGER NOT NULL DEFAULT 0,
    recovery_command_json TEXT,
    UNIQUE(task_id, action_id, raw_hash)
);
CREATE TABLE IF NOT EXISTS evidence(
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    action_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    summary TEXT NOT NULL,
    governance_blocked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY(task_id, action_id) REFERENCES actions(task_id, action_id)
);
CREATE TABLE IF NOT EXISTS task_control(
    task_id TEXT PRIMARY KEY,
    suspension_reason TEXT,
    checkpoint_id TEXT,
    checkpoint_revision TEXT,
    checkpoint_artifact_hash TEXT,
    approved_checkpoint_id TEXT,
    approved_revision TEXT,
    approved_artifact_hash TEXT,
    progress_fingerprint TEXT,
    active_execution INTEGER NOT NULL DEFAULT 0,
    max_remote_rounds INTEGER,
    max_local_actions INTEGER,
    max_no_progress_rounds INTEGER,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
);
'''
            )
            row = self.db.execute(
                "SELECT value FROM metadata WHERE key='schema_version'"
            ).fetchone()
            if row is None:
                self.db.execute(
                    "INSERT INTO metadata(key,value) VALUES('schema_version',?)",
                    (str(SCHEMA_VERSION),),
                )
            elif int(row["value"]) != SCHEMA_VERSION:
                raise RuntimeError("unsupported task-store schema version")

    @staticmethod
    def canonical_payload(payload: Any) -> str:
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    @classmethod
    def payload_hash(cls, payload: Any) -> str:
        return hashlib.sha256(cls.canonical_payload(payload).encode()).hexdigest()

    def ensure_task(self, task_id: str):
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO tasks(task_id,state,execution_state,governance_state) VALUES(?,?,?,?)",
                (task_id, "ACTIVE", "IDLE", "CLEAR"),
            )
            self.db.execute(
                "INSERT OR IGNORE INTO task_control(task_id) VALUES(?)",
                (task_id,),
            )

    def task_row(self, task_id: str):
        row = self.db.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return row

    def control_row(self, task_id: str):
        self.ensure_task(task_id)
        row = self.db.execute("SELECT * FROM task_control WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return row

    def set_states(self, task_id: str, state=None, execution_state=None, governance_state=None):
        row = self.task_row(task_id)
        with self.db:
            self.db.execute(
                "UPDATE tasks SET state=?,execution_state=?,governance_state=? WHERE task_id=?",
                (
                    state or row["state"],
                    execution_state or row["execution_state"],
                    governance_state or row["governance_state"],
                    task_id,
                ),
            )

    def bump(self, task_id: str, field: str, n: int = 1):
        if field not in {"remote_rounds_used", "local_actions_used", "retries_used", "no_progress_rounds"}:
            raise ValueError("unsupported budget field")
        with self.db:
            self.db.execute(f"UPDATE tasks SET {field}={field}+? WHERE task_id=?", (n, task_id))

    def set_limits(self, task_id: str, *, max_remote_rounds=None, max_local_actions=None, max_no_progress_rounds=None):
        self.ensure_task(task_id)
        for value in (max_remote_rounds, max_local_actions, max_no_progress_rounds):
            if value is not None and value < 1:
                raise ValueError("budget limits must be >= 1")
        with self.db:
            self.db.execute(
                "UPDATE task_control SET max_remote_rounds=?,max_local_actions=?,max_no_progress_rounds=? WHERE task_id=?",
                (max_remote_rounds, max_local_actions, max_no_progress_rounds, task_id),
            )

    def suspend(self, task_id: str, reason: str):
        if reason not in SUSPENSION_REASONS:
            raise ValueError("unsupported suspension reason")
        self.ensure_task(task_id)
        with self.db:
            self.db.execute("UPDATE task_control SET suspension_reason=? WHERE task_id=?", (reason, task_id))
            self.set_states(task_id, state="SUSPENDED")

    def clear_suspension(self, task_id: str, *, next_state="WAITING_FOR_REMOTE"):
        self.ensure_task(task_id)
        with self.db:
            self.db.execute("UPDATE task_control SET suspension_reason=NULL WHERE task_id=?", (task_id,))
            self.set_states(task_id, state=next_state)

    def suspension_reason(self, task_id: str) -> str | None:
        return self.control_row(task_id)["suspension_reason"]

    def request_checkpoint(self, task_id: str, checkpoint_id: str, revision: str, artifact_hash: str):
        if not checkpoint_id or not revision or not artifact_hash:
            raise ValueError("checkpoint identity, revision and artifact required")
        self.ensure_task(task_id)
        with self.db:
            self.db.execute(
                "UPDATE task_control SET checkpoint_id=?,checkpoint_revision=?,checkpoint_artifact_hash=?,approved_checkpoint_id=NULL,approved_revision=NULL,approved_artifact_hash=NULL,suspension_reason='WAITING_FOR_HUMAN' WHERE task_id=?",
                (checkpoint_id, revision, artifact_hash, task_id),
            )
            self.set_states(task_id, state="SUSPENDED")

    def approve_checkpoint(self, task_id: str, checkpoint_id: str, revision: str, artifact_hash: str):
        control = self.control_row(task_id)
        if control["suspension_reason"] != "WAITING_FOR_HUMAN":
            raise RuntimeError("task is not waiting for human approval")
        expected = (
            control["checkpoint_id"],
            control["checkpoint_revision"],
            control["checkpoint_artifact_hash"],
        )
        if (checkpoint_id, revision, artifact_hash) != expected:
            raise ValueError("stale or mismatched human approval")
        with self.db:
            self.db.execute(
                "UPDATE task_control SET approved_checkpoint_id=?,approved_revision=?,approved_artifact_hash=?,suspension_reason=NULL WHERE task_id=?",
                (checkpoint_id, revision, artifact_hash, task_id),
            )
            self.set_states(task_id, state="WAITING_FOR_REMOTE")

    def checkpoint_approved_for(self, task_id: str, revision: str, artifact_hash: str) -> bool:
        control = self.control_row(task_id)
        return (
            control["approved_checkpoint_id"] is not None
            and control["approved_revision"] == revision
            and control["approved_artifact_hash"] == artifact_hash
        )

    def pause(self, task_id: str):
        self.suspend(task_id, "USER_PAUSED")

    def resume(self, task_id: str):
        if self.suspension_reason(task_id) != "USER_PAUSED":
            raise RuntimeError("only USER_PAUSED may resume directly")
        self.clear_suspension(task_id)

    def cancel(self, task_id: str):
        self.ensure_task(task_id)
        with self.db:
            self.db.execute(
                "UPDATE task_control SET suspension_reason=NULL,active_execution=0 WHERE task_id=?",
                (task_id,),
            )
            self.set_states(task_id, state="CANCELLED", execution_state="IDLE")

    def _budget_exhausted(self, task_id: str) -> str | None:
        task = self.task_row(task_id)
        control = self.control_row(task_id)
        for used_name, max_name in (
            ("remote_rounds_used", "max_remote_rounds"),
            ("local_actions_used", "max_local_actions"),
        ):
            limit = control[max_name]
            if limit is not None and int(task[used_name]) >= int(limit):
                return max_name
        return None

    def require_dispatch_allowed(self, task_id: str):
        task = self.task_row(task_id)
        reason = self.suspension_reason(task_id)
        if task["state"] == "CANCELLED":
            raise RuntimeError("task is cancelled")
        if reason is not None:
            raise RuntimeError(f"task suspended: {reason}")
        exhausted = self._budget_exhausted(task_id)
        if exhausted is not None:
            self.suspend(task_id, "BUDGET_EXHAUSTED")
            raise RuntimeError(f"task budget exhausted: {exhausted}")

    def register_action(self, task_id, action_id, payload, predecessor_action_id=None):
        self.ensure_task(task_id)
        canonical = self.canonical_payload(payload)
        digest = self.payload_hash(payload)
        row = self.db.execute(
            "SELECT * FROM actions WHERE task_id=? AND action_id=?",
            (task_id, action_id),
        ).fetchone()
        if row is not None:
            if row["payload_hash"] != digest:
                raise ValueError("action_id reused with changed payload")
            return "DUPLICATE"
        self.require_dispatch_allowed(task_id)
        if predecessor_action_id:
            predecessor = self.db.execute(
                "SELECT status FROM actions WHERE task_id=? AND action_id=?",
                (task_id, predecessor_action_id),
            ).fetchone()
            if predecessor is None:
                raise ValueError("unknown predecessor")
            if predecessor["status"] == "OUTCOME_UNKNOWN":
                raise RuntimeError("predecessor outcome unresolved")
        with self.db:
            self.db.execute(
                "INSERT INTO actions(task_id,action_id,payload_hash,payload_json,status,predecessor_action_id) VALUES(?,?,?,?,?,?)",
                (task_id, action_id, digest, canonical, "REGISTERED", predecessor_action_id),
            )
            self.db.execute(
                "INSERT INTO messages(task_id,direction,kind,action_id,payload_json,delivered) VALUES(?,?,?,?,?,1)",
                (task_id, "IN", "ACTION", action_id, canonical),
            )
        return "NEW"

    def begin_attempt(self, task_id, action_id):
        self.require_dispatch_allowed(task_id)
        row = self.db.execute(
            "SELECT * FROM actions WHERE task_id=? AND action_id=?",
            (task_id, action_id),
        ).fetchone()
        if row is None:
            raise KeyError(action_id)
        if row["status"] == "OUTCOME_UNKNOWN":
            raise RuntimeError("cannot retry unresolved outcome")
        attempt_no = int(row["attempt_count"]) + 1
        with self.db:
            self.db.execute(
                "UPDATE actions SET attempt_count=?,status='DISPATCH_INTENT' WHERE task_id=? AND action_id=?",
                (attempt_no, task_id, action_id),
            )
            self.db.execute(
                "INSERT INTO attempts(task_id,action_id,attempt_no,status) VALUES(?,?,?,'DISPATCH_INTENT')",
                (task_id, action_id, attempt_no),
            )
            self.bump(task_id, "local_actions_used")
            self.db.execute("UPDATE task_control SET active_execution=1 WHERE task_id=?", (task_id,))
            self.set_states(task_id, state="ACTIVE", execution_state="RUNNING")
        return attempt_no

    def record_kit_evidence(self, task_id, evidence):
        import json
        status=evidence.status.upper()
        with self.db:
            self.db.execute(
                "INSERT OR IGNORE INTO kit_evidence(task_id,action_id,status,producer,command_json,revision,artifact_hash,raw_hash,recoverable,recovery_command_json) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (task_id,evidence.action_id,status,evidence.producer,json.dumps(list(evidence.command)),evidence.revision,
                 evidence.artifact_hash,evidence.raw_hash,1 if evidence.recoverable else 0,
                 json.dumps(list(evidence.recovery_command)) if evidence.recovery_command else None))
            if status == "BLOCKED" and not evidence.recoverable:
                self.db.execute("UPDATE task_control SET suspension_reason='SAFETY_BLOCK' WHERE task_id=?",(task_id,))
            self.db.execute("UPDATE tasks SET governance_state=? WHERE task_id=?",
                ("BLOCKED" if status=="BLOCKED" else ("CLEAR" if status=="PASS" else "FAILED"),task_id))

    def kit_evidence_for(self, task_id, action_id):
        row=self.db.execute("SELECT * FROM kit_evidence WHERE task_id=? AND action_id=? ORDER BY evidence_id DESC LIMIT 1",
            (task_id,action_id)).fetchone()
        return dict(row) if row else None


    def record_result(self, task_id, action_id, attempt_no, outcome, summary, governance_blocked=False):
        normalized = outcome.upper()
        if normalized not in {"PASS", "FAIL", "BLOCKED"}:
            raise ValueError("unsupported outcome")
        execution_state = {"PASS": "SUCCEEDED", "FAIL": "FAILED", "BLOCKED": "BLOCKED"}[normalized]
        payload = self.canonical_payload(
            {"outcome": normalized, "summary": summary, "governance_blocked": governance_blocked}
        )
        with self.db:
            self.db.execute(
                "UPDATE attempts SET status=?,result_json=? WHERE task_id=? AND action_id=? AND attempt_no=?",
                (normalized, payload, task_id, action_id, attempt_no),
            )
            self.db.execute(
                "UPDATE actions SET status=? WHERE task_id=? AND action_id=?",
                (normalized, task_id, action_id),
            )
            self.db.execute(
                "INSERT INTO evidence(task_id,action_id,outcome,summary,governance_blocked) VALUES(?,?,?,?,?)",
                (task_id, action_id, normalized, summary, 1 if governance_blocked else 0),
            )
            self.db.execute(
                "INSERT INTO messages(task_id,direction,kind,action_id,payload_json,delivered) VALUES(?,?,?,?,?,0)",
                (task_id, "OUT", "RESULT", action_id, payload),
            )
            self.db.execute("UPDATE task_control SET active_execution=0 WHERE task_id=?", (task_id,))
            self.set_states(
                task_id,
                state="WAITING_FOR_REMOTE",
                execution_state=execution_state,
                governance_state="BLOCKED" if governance_blocked or normalized == "BLOCKED" else "CLEAR",
            )

    def mark_unknown(self, task_id, action_id, attempt_no, reason):
        with self.db:
            self.db.execute(
                "UPDATE attempts SET status='OUTCOME_UNKNOWN',result_json=? WHERE task_id=? AND action_id=? AND attempt_no=?",
                (self.canonical_payload({"reason": reason}), task_id, action_id, attempt_no),
            )
            self.db.execute(
                "UPDATE actions SET status='OUTCOME_UNKNOWN' WHERE task_id=? AND action_id=?",
                (task_id, action_id),
            )
            self.db.execute("UPDATE task_control SET active_execution=0 WHERE task_id=?", (task_id,))
            self.set_states(task_id, state="RECONCILING", execution_state="OUTCOME_UNKNOWN")

    def reconcile(self, task_id, action_id, conclusion):
        if conclusion not in {"CONFIRMED_APPLIED", "CONFIRMED_NOT_APPLIED", "STILL_UNKNOWN"}:
            raise ValueError("invalid reconciliation conclusion")
        row = self.db.execute(
            "SELECT status FROM actions WHERE task_id=? AND action_id=?",
            (task_id, action_id),
        ).fetchone()
        if row is None or row["status"] != "OUTCOME_UNKNOWN":
            raise RuntimeError("action is not outcome-unknown")
        if conclusion == "STILL_UNKNOWN":
            self.suspend(task_id, "OUTCOME_UNKNOWN")
            self.set_states(task_id, execution_state="OUTCOME_UNKNOWN")
            return
        status = "RECONCILED_APPLIED" if conclusion == "CONFIRMED_APPLIED" else "RECONCILED_NOT_APPLIED"
        with self.db:
            self.db.execute(
                "UPDATE actions SET status=? WHERE task_id=? AND action_id=?",
                (status, task_id, action_id),
            )
            self.set_states(
                task_id,
                state="WAITING_FOR_REMOTE",
                execution_state="SUCCEEDED" if conclusion == "CONFIRMED_APPLIED" else "FAILED",
            )

    def observe_progress(self, task_id: str, fingerprint: str):
        if not fingerprint:
            raise ValueError("progress fingerprint required")
        task = self.task_row(task_id)
        control = self.control_row(task_id)
        if int(control["active_execution"]):
            return "ACTIVE_EXECUTION"
        if task["state"] == "CANCELLED":
            return "CANCELLED"
        if control["suspension_reason"] is not None:
            return control["suspension_reason"]
        previous = control["progress_fingerprint"]
        if previous is None or previous != fingerprint:
            with self.db:
                self.db.execute(
                    "UPDATE task_control SET progress_fingerprint=? WHERE task_id=?",
                    (fingerprint, task_id),
                )
                self.db.execute("UPDATE tasks SET no_progress_rounds=0 WHERE task_id=?", (task_id,))
            return "PROGRESS"
        self.bump(task_id, "no_progress_rounds")
        task = self.task_row(task_id)
        limit = self.control_row(task_id)["max_no_progress_rounds"]
        if limit is not None and int(task["no_progress_rounds"]) >= int(limit):
            self.suspend(task_id, "STALLED")
            return "STALLED"
        return "NO_PROGRESS"

    def pending_outbox(self, task_id):
        return self.db.execute(
            "SELECT * FROM messages WHERE task_id=? AND direction='OUT' AND delivered=0 ORDER BY message_id",
            (task_id,),
        ).fetchall()

    def mark_delivered(self, message_id):
        with self.db:
            self.db.execute("UPDATE messages SET delivered=1 WHERE message_id=?", (message_id,))
