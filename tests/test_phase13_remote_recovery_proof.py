from agp_cockpit.core.task_controller import TaskController
from agp_cockpit.core.task_models import ExecutionState, GovernanceState, TaskState


def test_fail_recovery():
 c=TaskController(); assert c.accept_remote_action("a1"); c.record_local_result("a1","FAIL","failure")
 assert c.execution_state is ExecutionState.FAILED and c.task_state is TaskState.WAITING_FOR_REMOTE
 assert c.accept_remote_action("a2"); c.record_local_result("a2","PASS","corrected"); c.propose_complete()
 assert c.verify_complete(True) and c.task_state is TaskState.VERIFIED_COMPLETE
def test_blocked_continues():
 c=TaskController(); assert c.accept_remote_action("g1"); c.record_local_result("g1","BLOCKED","Kit",True)
 assert c.governance_state is GovernanceState.BLOCKED and c.task_state is TaskState.WAITING_FOR_REMOTE
 assert c.accept_remote_action("g2")
def test_duplicate_rejected():
 c=TaskController(); assert c.accept_remote_action("x"); c.record_local_result("x","FAIL","e"); assert not c.accept_remote_action("x")
def test_premature_complete_rejected():
 c=TaskController(); c.propose_complete(); assert not c.verify_complete(False); assert c.task_state is TaskState.WAITING_FOR_REMOTE
