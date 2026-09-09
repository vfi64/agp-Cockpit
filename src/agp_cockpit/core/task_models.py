from dataclasses import dataclass
from enum import Enum
class ExecutionState(str,Enum): IDLE="IDLE"; RUNNING="RUNNING"; SUCCEEDED="SUCCEEDED"; FAILED="FAILED"; BLOCKED="BLOCKED"
class TaskState(str,Enum): ACTIVE="ACTIVE"; WAITING_FOR_REMOTE="WAITING_FOR_REMOTE"; COMPLETE_PROPOSED="COMPLETE_PROPOSED"; VERIFIED_COMPLETE="VERIFIED_COMPLETE"
class GovernanceState(str,Enum): CLEAR="CLEAR"; BLOCKED="BLOCKED"
@dataclass(frozen=True)
class Evidence:
 action_id:str
 outcome:str
 summary:str
 governance_blocked:bool=False
