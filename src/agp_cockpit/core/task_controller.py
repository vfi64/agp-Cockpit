from dataclasses import dataclass,field
from .task_models import Evidence,ExecutionState,GovernanceState,TaskState
@dataclass
class TaskController:
 task_state:TaskState=TaskState.ACTIVE
 execution_state:ExecutionState=ExecutionState.IDLE
 governance_state:GovernanceState=GovernanceState.CLEAR
 seen_action_ids:set[str]=field(default_factory=set)
 evidence:list[Evidence]=field(default_factory=list)
 def accept_remote_action(self,a):
  if self.task_state is TaskState.VERIFIED_COMPLETE or a in self.seen_action_ids:return False
  self.seen_action_ids.add(a); self.execution_state=ExecutionState.RUNNING; self.task_state=TaskState.ACTIVE; return True
 def record_local_result(self,a,outcome,summary,governance_blocked=False):
  if a not in self.seen_action_ids:raise ValueError("unknown action_id")
  x=outcome.upper()
  if x not in {"PASS","FAIL","BLOCKED"}:raise ValueError("unsupported outcome")
  self.evidence.append(Evidence(a,x,summary,governance_blocked))
  self.execution_state={"PASS":ExecutionState.SUCCEEDED,"FAIL":ExecutionState.FAILED,"BLOCKED":ExecutionState.BLOCKED}[x]
  self.governance_state=GovernanceState.BLOCKED if governance_blocked or x=="BLOCKED" else GovernanceState.CLEAR
  self.task_state=TaskState.WAITING_FOR_REMOTE
 def propose_complete(self):self.task_state=TaskState.COMPLETE_PROPOSED
 def verify_complete(self,passed):
  if self.task_state is not TaskState.COMPLETE_PROPOSED:return False
  if passed:self.task_state=TaskState.VERIFIED_COMPLETE; return True
  self.task_state=TaskState.WAITING_FOR_REMOTE; return False
