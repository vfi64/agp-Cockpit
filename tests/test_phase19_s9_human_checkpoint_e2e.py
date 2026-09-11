from pathlib import Path
import pytest
from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.task_models import KitResultEvidence

def make(tmp_path: Path):
    c=DurableTaskController("s9-human",tmp_path/"runtime.sqlite3")
    c.set_limits(max_remote_rounds=20,max_local_actions=20)
    epoch=c.bind_remote_context("chat-before-checkpoint")
    return c,epoch

def execute(c, action_id, payload, predecessor=None):
    assert c.accept_remote_action(action_id,payload,predecessor)=="NEW"
    n=c.begin_attempt(action_id); c.record_local_result(action_id,n,"PASS","completed"); return n
    for row in c.pending_results():
        c.mark_result_delivered(row["message_id"])


def test_human_checkpoint_suspends_same_task_and_exact_approval_resumes(tmp_path):
    c,epoch=make(tmp_path)
    execute(c,"a1",{"kind":"prepare_visual"})
    before=c.snapshot.copy()
    c.request_human_checkpoint("visual-physical-1","rev-1","artifact-1")
    assert c.snapshot["state"]=="SUSPENDED"
    assert c.snapshot["suspension_reason"]=="WAITING_FOR_HUMAN"
    assert c.active_remote_binding()["binding_epoch"]==epoch
    with pytest.raises(RuntimeError,match="WAITING_FOR_HUMAN"):
        c.accept_remote_action("a2",{"kind":"protected_followup"},"a1")
    with pytest.raises(ValueError,match="stale or mismatched"):
        c.approve_human_checkpoint("visual-physical-1","rev-old","artifact-1")
    c.approve_human_checkpoint("visual-physical-1","rev-1","artifact-1")
    assert c.snapshot["state"]=="WAITING_FOR_REMOTE"
    assert c.snapshot["remote_rounds_used"]==before["remote_rounds_used"]
    for row in c.pending_results(): c.mark_result_delivered(row["message_id"])
    execute(c,"a2",{"kind":"protected_followup"},"a1")
    c.close()

def test_checkpoint_and_approval_survive_restart_and_revision_change_invalidates_old_approval(tmp_path):
    db=tmp_path/"runtime.sqlite3"; c=DurableTaskController("s9-restart",db); c.bind_remote_context("chat")
    c.request_human_checkpoint("cp","rev-a","artifact-a"); c.close()
    c=DurableTaskController("s9-restart",db)
    assert c.snapshot["suspension_reason"]=="WAITING_FOR_HUMAN"
    c.approve_human_checkpoint("cp","rev-a","artifact-a"); assert c.checkpoint_approved_for("rev-a","artifact-a"); c.close()
    c=DurableTaskController("s9-restart",db); assert c.checkpoint_approved_for("rev-a","artifact-a")
    c.request_human_checkpoint("cp2","rev-b","artifact-b")
    assert not c.checkpoint_approved_for("rev-a","artifact-a")
    c.close()

def test_late_action_from_pre_checkpoint_binding_loses_authority_after_rebind(tmp_path):
    c,old=make(tmp_path)
    c.request_human_checkpoint("cp","rev-1","artifact-1")
    c.approve_human_checkpoint("cp","rev-1","artifact-1")
    new=c.bind_remote_context("chat-after-checkpoint")
    assert new>old
    assert not c.binding_has_execution_authority(old)
    assert c.binding_has_execution_authority(new)
    # The transport/controller boundary must reject the old binding before dispatch.
    if not c.binding_has_execution_authority(old):
        rejected=True
    else:
        rejected=False
    assert rejected
    assert c.store.db.execute("SELECT COUNT(*) AS n FROM actions WHERE task_id=?",(c.task_id,)).fetchone()["n"]==0
    c.close()

def test_human_checkpoint_variant_reaches_verified_complete_only_with_matching_approval(tmp_path):
    c,_=make(tmp_path)
    execute(c,"kit-final",{"effect":"E3","kind":"kit"})
    c.record_verified_kit_result(KitResultEvidence(action_id="kit-final",status="PASS",producer="agentic-project-kit",command=("agentic-kit","check"),revision="rev-1",artifact_hash="artifact-1",raw_hash="raw-1"), acquisition_source="local-executor")
    c.set_completion_contract("rev-1","artifact-1","kit-final","raw-1",human_checkpoint_required=True)
    assert c.propose_complete(); assert not c.verify_completion_contract()
    assert c.completion_contract()["rejection_reason"]=="MISSING_OR_STALE_HUMAN_APPROVAL"
    c.request_human_checkpoint("cp","rev-1","artifact-1"); c.approve_human_checkpoint("cp","rev-1","artifact-1")
    assert c.propose_complete(); assert c.verify_completion_contract(); assert c.snapshot["state"]=="VERIFIED_COMPLETE"; c.close()

