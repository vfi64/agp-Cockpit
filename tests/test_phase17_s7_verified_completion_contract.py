from pathlib import Path
from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.task_models import KitResultEvidence

def make(tmp_path: Path):
    return DurableTaskController("t-s7", tmp_path/"runtime.sqlite3")

def kit_pass(c, action="kit-final", revision="rev-1", artifact="artifact-1", raw="raw-1"):
    c.record_kit_result(KitResultEvidence(action_id=action,status="PASS",producer="agentic-project-kit",command=("agentic-kit","check"),revision=revision,artifact_hash=artifact,raw_hash=raw))

def contract(c, human=False):
    c.set_completion_contract("rev-1","artifact-1","kit-final","raw-1",human_checkpoint_required=human)

def test_complete_is_only_proposal_until_contract_verifies(tmp_path):
    c=make(tmp_path); contract(c); kit_pass(c); assert c.propose_complete()
    assert c.snapshot["state"]=="COMPLETE_PROPOSED"; assert c.verify_completion_contract()
    assert c.snapshot["state"]=="VERIFIED_COMPLETE"; assert c.completion_contract()["status"]=="VERIFIED"; c.close()

def test_premature_complete_without_contract_is_rejected(tmp_path):
    c=make(tmp_path); assert c.propose_complete(); assert not c.verify_completion_contract()
    assert c.snapshot["state"]=="WAITING_FOR_REMOTE"; c.close()

def test_stale_revision_or_artifact_kit_pass_rejects_completion(tmp_path):
    for revision,artifact in (("old-rev","artifact-1"),("rev-1","old-artifact")):
        c=make(tmp_path); contract(c); kit_pass(c,revision=revision,artifact=artifact)
        assert c.propose_complete(); assert not c.verify_completion_contract()
        assert c.completion_contract()["rejection_reason"]=="MISSING_OR_STALE_KIT_PASS"; c.close()

def test_governance_block_prevents_verified_complete(tmp_path):
    c=make(tmp_path); contract(c); kit_pass(c); c.store.set_states(c.task_id,governance_state="BLOCKED")
    assert c.propose_complete(); assert not c.verify_completion_contract()
    assert c.completion_contract()["rejection_reason"]=="GOVERNANCE_NOT_CLEAR"; c.close()

def test_required_human_checkpoint_must_match_revision_and_artifact(tmp_path):
    c=make(tmp_path); contract(c,True); kit_pass(c); assert c.propose_complete(); assert not c.verify_completion_contract()
    assert c.completion_contract()["rejection_reason"]=="MISSING_OR_STALE_HUMAN_APPROVAL"
    c.request_human_checkpoint("cp","rev-1","artifact-1"); c.approve_human_checkpoint("cp","rev-1","artifact-1")
    assert c.propose_complete(); assert c.verify_completion_contract(); c.close()

def test_contract_and_rejection_survive_restart(tmp_path):
    db=tmp_path/"runtime.sqlite3"; c=DurableTaskController("t-s7",db); contract(c); c.propose_complete()
    assert not c.verify_completion_contract(); c.close(); c=DurableTaskController("t-s7",db); x=c.completion_contract()
    assert x["revision"]=="rev-1" and x["status"]=="REJECTED" and x["rejection_reason"]=="MISSING_OR_STALE_KIT_PASS"; c.close()
