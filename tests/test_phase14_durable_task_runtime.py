from pathlib import Path

import pytest

from agp_cockpit.core.task_controller import DurableTaskController


def make(tmp_path:Path,task='t1'):return DurableTaskController(task,tmp_path/'runtime.sqlite3')

def test_restart_preserves_state_budgets_and_pending_result(tmp_path):
    c=make(tmp_path); assert c.accept_remote_action('a1',{'cmd':'false'})=='NEW'; n=c.begin_attempt('a1'); c.record_local_result('a1',n,'FAIL','failure'); before=c.snapshot; assert len(c.pending_results())==1; c.close()
    c=make(tmp_path); assert c.snapshot['state']=='WAITING_FOR_REMOTE'; assert c.snapshot['execution_state']=='FAILED'; assert c.snapshot['remote_rounds_used']==before['remote_rounds_used']==1; assert c.snapshot['local_actions_used']==before['local_actions_used']==1; assert len(c.pending_results())==1; c.close()

def test_durable_duplicate_and_payload_hash_guard(tmp_path):
    c=make(tmp_path); assert c.accept_remote_action('a1',{'x':1})=='NEW'; c.close(); c=make(tmp_path); assert c.accept_remote_action('a1',{'x':1})=='DUPLICATE'; assert c.snapshot['remote_rounds_used']==1
    with pytest.raises(ValueError,match='changed payload'):c.accept_remote_action('a1',{'x':2})
    c.close()

def test_outcome_unknown_survives_restart_and_blocks_retry(tmp_path):
    c=make(tmp_path); c.accept_remote_action('a1',{'mutating':True}); n=c.begin_attempt('a1'); c.mark_outcome_unknown('a1',n,'crash after dispatch'); assert c.snapshot['state']=='RECONCILING'
    with pytest.raises(RuntimeError,match='unresolved outcome blocks dispatch'):c.begin_attempt('a1')
    c.close(); c=make(tmp_path); assert c.snapshot['execution_state']=='OUTCOME_UNKNOWN'
    with pytest.raises(RuntimeError,match='unresolved outcome blocks dispatch'):c.begin_attempt('a1')
    c.close()

def test_unknown_predecessor_cannot_be_bypassed_by_new_action(tmp_path):
    c=make(tmp_path); c.accept_remote_action('a1',{'mutating':True}); n=c.begin_attempt('a1'); c.mark_outcome_unknown('a1',n,'uncertain')
    with pytest.raises(RuntimeError,match='unresolved outcome blocks dispatch'):c.accept_remote_action('a2',{'repair':True},'a1')
    c.close()

def test_reconcile_not_applied_allows_corrective_successor(tmp_path):
    c=make(tmp_path); c.accept_remote_action('a1',{'mutating':True}); n=c.begin_attempt('a1'); c.mark_outcome_unknown('a1',n,'uncertain'); c.reconcile('a1','CONFIRMED_NOT_APPLIED'); assert c.snapshot['state']=='WAITING_FOR_REMOTE'; assert c.accept_remote_action('a2',{'repair':True},'a1')=='NEW'; c.close()

def test_still_unknown_suspends(tmp_path):
    c=make(tmp_path); c.accept_remote_action('a1',{'mutating':True}); n=c.begin_attempt('a1'); c.mark_outcome_unknown('a1',n,'uncertain'); c.reconcile('a1','STILL_UNKNOWN'); assert c.snapshot['state']=='SUSPENDED'; c.close()

def test_outbox_delivery_is_restart_safe_and_does_not_reexecute(tmp_path):
    c=make(tmp_path); c.accept_remote_action('a1',{'cmd':'false'}); n=c.begin_attempt('a1'); c.record_local_result('a1',n,'FAIL','evidence'); msg=c.pending_results()[0]; c.close(); c=make(tmp_path); c.mark_result_delivered(msg['message_id']); assert c.pending_results()==[]; c.close(); c=make(tmp_path); assert c.pending_results()==[]; assert c.accept_remote_action('a1',{'cmd':'false'})=='DUPLICATE'; c.close()

def test_completion_proposal_is_restart_safe(tmp_path):
    c=make(tmp_path); c.propose_complete(); c.close(); c=make(tmp_path); assert c.snapshot['state']=='COMPLETE_PROPOSED'; assert not c.verify_complete(False); assert c.snapshot['state']=='WAITING_FOR_REMOTE'; c.propose_complete(); assert not c.verify_complete(True); assert c.snapshot['state']=='WAITING_FOR_REMOTE'; c.close()
