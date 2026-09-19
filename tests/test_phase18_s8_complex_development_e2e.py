from pathlib import Path

import pytest

from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.task_models import KitResultEvidence


def controller(tmp_path: Path):
    c = DurableTaskController("s8-real-feature", tmp_path / "runtime.sqlite3")
    c.set_limits(max_remote_rounds=20, max_local_actions=20, max_no_progress_rounds=5)
    c.bind_remote_context("chat-s8")
    return c

def execute(c, action_id, payload, outcome, summary, *, governance_blocked=False, predecessor=None):
    assert c.accept_remote_action(action_id, payload, predecessor) == "NEW"
    attempt = c.begin_attempt(action_id)
    c.record_local_result(action_id, attempt, outcome, summary, governance_blocked)
    for row in c.pending_results():
        c.mark_result_delivered(row["message_id"])
    return attempt


def test_t26_bounded_feature_survives_script_test_and_recoverable_kit_blocked(tmp_path):
    c = controller(tmp_path)

    execute(c, "a1-script", {"kind":"work_order","feature":"bounded-real-feature"}, "FAIL", "generated work script failed")
    assert c.snapshot["state"] == "WAITING_FOR_REMOTE"
    assert c.snapshot["execution_state"] == "FAILED"

    execute(c, "a2-script-fix", {"kind":"work_order_fix"}, "PASS", "remote correction produced valid work order", predecessor="a1-script")
    execute(c, "a3-test", {"kind":"test","target":"feature"}, "FAIL", "feature test exposed defect", predecessor="a2-script-fix")
    assert c.snapshot["state"] == "WAITING_FOR_REMOTE"

    execute(c, "a4-code-fix", {"kind":"code_fix"}, "PASS", "remote correction fixed defect", predecessor="a3-test")
    execute(c, "a5-kit", {"kind":"kit","command":["agentic-kit","check"]}, "BLOCKED", "Kit requires governed recovery", governance_blocked=True, predecessor="a4-code-fix")
    c.record_kit_result(KitResultEvidence(
        action_id="a5-kit", status="BLOCKED", producer="agentic-project-kit",
        command=("agentic-kit","check"), revision="rev-1", artifact_hash="artifact-1", raw_hash="blocked-raw",
        recoverable=True, recovery_command=("agentic-kit","work","recover"),
    ))
    assert c.authorize_kit_recovery("a5-kit", ("agentic-kit","work","recover")) == ("agentic-kit","work","recover")
    with pytest.raises(PermissionError):
        c.authorize_kit_recovery("a5-kit", ("git","commit","-am","bypass"))

    execute(c, "a6-kit-recovery", {"kind":"kit_recovery","command":["agentic-kit","work","recover"]}, "PASS", "governed recovery completed", predecessor="a5-kit")
    execute(c, "a7-final-kit", {"kind":"kit","command":["agentic-kit","check"]}, "PASS", "final governed Kit verification", predecessor="a6-kit-recovery")
    c.record_verified_kit_result(KitResultEvidence(
        action_id="a7-final-kit", status="PASS", producer="agentic-project-kit",
        command=("agentic-kit","check"), revision="rev-1", artifact_hash="artifact-1", raw_hash="final-pass",
    ), acquisition_source="local-executor")
    c.store.set_states(c.task_id, governance_state="CLEAR", execution_state="SUCCEEDED")

    c.set_completion_contract("rev-1","artifact-1","a7-final-kit","final-pass")
    assert c.propose_complete()
    assert c.verify_completion_contract()
    assert c.snapshot["state"] == "VERIFIED_COMPLETE"

    rows = c.store.db.execute("SELECT outcome FROM evidence WHERE task_id=? ORDER BY evidence_id", (c.task_id,)).fetchall()
    assert [r["outcome"] for r in rows] == ["FAIL","PASS","FAIL","PASS","BLOCKED","PASS","PASS"]
    assert c.snapshot["remote_rounds_used"] == 7
    assert c.snapshot["local_actions_used"] == 7
    c.close()

def test_t26_restart_mid_recovery_keeps_same_task_and_binding(tmp_path):
    db=tmp_path/"runtime.sqlite3"
    c=DurableTaskController("s8-restart",db); c.set_limits(max_remote_rounds=10,max_local_actions=10); epoch=c.bind_remote_context("chat-a")
    execute(c,"a1",{"kind":"script"},"FAIL","script failed")
    execute(c,"a2",{"kind":"fix"},"PASS","fixed",predecessor="a1")
    before=c.snapshot.copy(); c.close()
    c=DurableTaskController("s8-restart",db)
    assert c.active_remote_binding()["binding_epoch"] == epoch
    assert c.snapshot["remote_rounds_used"] == before["remote_rounds_used"]
    assert c.snapshot["local_actions_used"] == before["local_actions_used"]
    execute(c,"a3",{"kind":"test"},"PASS","continued after restart",predecessor="a2")
    c.close()

def test_t26_duplicate_and_old_binding_never_duplicate_effect(tmp_path):
    c=controller(tmp_path); old=c.active_remote_binding()["binding_epoch"]
    execute(c,"mutate-1",{"kind":"mutation","value":1},"PASS","applied")
    assert c.accept_remote_action("mutate-1",{"kind":"mutation","value":1}) == "DUPLICATE"
    assert c.snapshot["local_actions_used"] == 1
    new=c.bind_remote_context("chat-b")
    assert new > old and not c.binding_has_execution_authority(old) and c.binding_has_execution_authority(new)
    c.close()
