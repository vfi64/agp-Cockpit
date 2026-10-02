from dataclasses import dataclass
from enum import Enum


class ExecutionState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class TaskState(str, Enum):
    ACTIVE = "ACTIVE"
    WAITING_FOR_REMOTE = "WAITING_FOR_REMOTE"
    RECONCILING = "RECONCILING"
    SUSPENDED = "SUSPENDED"
    COMPLETE_PROPOSED = "COMPLETE_PROPOSED"
    VERIFIED_COMPLETE = "VERIFIED_COMPLETE"
    # AGP_TASK_CLOSE_ON_DONE_V1: a generic task ended by an accepted remote DONE
    # that the Cockpit could not verify itself (no completion contract, no CI gate).
    REMOTE_DONE = "REMOTE_DONE"
    CANCELLED = "CANCELLED"


class GovernanceState(str, Enum):
    CLEAR = "CLEAR"
    BLOCKED = "BLOCKED"


class SuspensionReason(str, Enum):
    WAITING_FOR_HUMAN = "WAITING_FOR_HUMAN"
    USER_PAUSED = "USER_PAUSED"
    BUDGET_EXHAUSTED = "BUDGET_EXHAUSTED"
    STALLED = "STALLED"
    WAITING_FOR_SERVICE = "WAITING_FOR_SERVICE"
    SAFETY_BLOCK = "SAFETY_BLOCK"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    STORAGE_BLOCKED = "STORAGE_BLOCKED"


@dataclass(frozen=True)
class Evidence:
    action_id: str
    outcome: str
    summary: str
    governance_blocked: bool = False

@dataclass(frozen=True)
class KitResultEvidence:
    action_id: str
    status: str
    producer: str
    command: tuple[str, ...]
    revision: str
    artifact_hash: str
    raw_hash: str
    recoverable: bool = False
    recovery_command: tuple[str, ...] | None = None

    def __post_init__(self):
        status = self.status.upper()
        if status not in {"PASS", "BLOCKED", "FAIL"}:
            raise ValueError("invalid Kit result status")
        if self.producer != "agentic-project-kit":
            raise ValueError("Kit evidence producer must be agentic-project-kit")
        if not self.action_id or not self.command or not self.revision or not self.raw_hash:
            raise ValueError("complete Kit evidence identity required")
        if self.recoverable and (status != "BLOCKED" or not self.recovery_command):
            raise ValueError("recoverable Kit BLOCKED requires an explicit Kit recovery command")
        if self.recovery_command and self.recovery_command[0] != "agentic-kit":
            raise ValueError("recovery path must remain Kit-owned")
