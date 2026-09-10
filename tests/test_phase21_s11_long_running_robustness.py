from pathlib import Path
import pytest
from agp_cockpit.core.task_controller import DurableTaskController

def ctl(tmp_path,name="t27"):
    return DurableTaskController(name,tmp_path/"runtime.sqlite3")

def test_t27_restart_after_dispatch_intent_becomes_unknown_and_never_blind_replays(tmp_path):
    c=ctl(tmp_path); c.set_limits(max_remote_rounds=20,max_local_actions=20,max_no_progress_rounds=3)
    c.accept_remote_action("a1",{"effect":"E2"}); assert c.begin_attempt("a1")==1; c.close()
    c=ctl(tmp_path); assert c.recover_interrupted_dispatches()==["a1"]
    assert c.snapshot["state"]=="RECONCILING" and c.snapshot["execution_state"]=="OUTCOME_UNKNOWN"
    with pytest.raises(RuntimeError,match="unresolved outcome blocks dispatch"): c.begin_attempt("a1")
    c.reconcile("a1","CONFIRMED_NOT_APPLIED"); assert c.snapshot["state"]=="WAITING_FOR_REMOTE"

def test_t27_result_persisted_before_restart_is_resent_without_reexecution(tmp_path):
    c=ctl(tmp_path); c.set_limits(max_remote_rounds=20,max_local_actions=20)
    c.accept_remote_action("a1",{"effect":"E2"}); n=c.begin_attempt("a1"); c.record_local_result("a1",n,"PASS","done")
    pending=c.pending_results(); assert len(pending)==1; mid=pending[0]["message_id"]; c.close()
    c=ctl(tmp_path); assert c.recover_interrupted_dispatches()==[]
    assert [x["message_id"] for x in c.pending_results()]==[mid]
    assert c.accept_remote_action("a1",{"effect":"E2"})=="DUPLICATE"
    assert c.snapshot["local_actions_used"]==1

def test_t27_service_outage_is_durable_and_requires_explicit_service_recovery(tmp_path):
    c=ctl(tmp_path); c.wait_for_service("provider outage")
    assert c.snapshot["state"]=="SUSPENDED" and c.snapshot["suspension_reason"]=="WAITING_FOR_SERVICE"
    c.close(); c=ctl(tmp_path); assert c.snapshot["suspension_reason"]=="WAITING_FOR_SERVICE"
    with pytest.raises(RuntimeError,match="WAITING_FOR_SERVICE"): c.accept_remote_action("a1",{"effect":"E0"})
    c.service_recovered(); assert c.snapshot["state"]=="WAITING_FOR_REMOTE" and c.snapshot["suspension_reason"] is None

def test_t27_long_active_execution_is_not_false_stalled(tmp_path):
    c=ctl(tmp_path); c.set_limits(max_remote_rounds=20,max_local_actions=20,max_no_progress_rounds=1)
    c.accept_remote_action("a1",{"effect":"E0"}); c.begin_attempt("a1")
    for _ in range(5): assert c.observe_progress("same-chat-fingerprint")=="ACTIVE_EXECUTION"
    assert c.snapshot["no_progress_rounds"]==0 and c.snapshot["suspension_reason"] is None

def test_t27_duplicate_stale_binding_budget_and_false_complete_remain_fail_closed(tmp_path):
    c=ctl(tmp_path); c.set_limits(max_remote_rounds=2,max_local_actions=10,max_no_progress_rounds=1)
    old=c.bind_remote_context("chat-a"); new=c.bind_remote_context("chat-b")
    assert not c.binding_has_execution_authority(old) and c.binding_has_execution_authority(new)
    assert c.accept_remote_action("a1",{"effect":"E0"})=="NEW"
    assert c.accept_remote_action("a1",{"effect":"E0"})=="DUPLICATE"
    with pytest.raises(ValueError,match="changed payload"): c.accept_remote_action("a1",{"effect":"E2"})
    c.propose_complete(); assert c.verify_completion_contract() is False
    assert c.snapshot["state"]=="WAITING_FOR_REMOTE"
    assert c.accept_remote_action("a2",{"effect":"E0"})=="NEW"
    with pytest.raises(RuntimeError,match="budget exhausted"): c.accept_remote_action("a3",{"effect":"E0"})
    assert c.snapshot["suspension_reason"]=="BUDGET_EXHAUSTED"

def test_t27_unknown_outcome_and_stall_survive_restart(tmp_path):
    c=ctl(tmp_path); c.set_limits(max_remote_rounds=20,max_local_actions=20,max_no_progress_rounds=1)
    c.accept_remote_action("a1",{"effect":"E2"}); n=c.begin_attempt("a1"); c.mark_outcome_unknown("a1",n,"network lost after effect"); c.close()
    c=ctl(tmp_path); assert c.snapshot["execution_state"]=="OUTCOME_UNKNOWN"
    c.reconcile("a1","CONFIRMED_NOT_APPLIED")
    assert c.observe_progress("semantic-a")=="PROGRESS"; assert c.observe_progress("semantic-a")=="STALLED"; c.close()
    c=ctl(tmp_path); assert c.snapshot["suspension_reason"]=="STALLED"
