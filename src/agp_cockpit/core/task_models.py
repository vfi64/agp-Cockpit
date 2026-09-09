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
