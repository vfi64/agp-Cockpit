import pytest

from agp_cockpit.core.task_controller import DurableTaskController


def controller(tmp_path, task_id="t"):
    return DurableTaskController(task_id, tmp_path / "tasks.sqlite3")


def test_t13_human_checkpoint_blocks_followup_and_resumes_same_task(tmp_path):
    c = controller(tmp_path)
    c.request_human_checkpoint("visual-1", "rev-a", "artifact-a")
    assert c.snapshot["state"] == "SUSPENDED"
    assert c.snapshot["suspension_reason"] == "WAITING_FOR_HUMAN"
    with pytest.raises(RuntimeError, match="WAITING_FOR_HUMAN"):
        c.accept_remote_action("a1", {"kind": "read"})
    c.approve_human_checkpoint("visual-1", "rev-a", "artifact-a")
    assert c.snapshot["state"] == "WAITING_FOR_REMOTE"
    assert c.accept_remote_action("a1", {"kind": "read"}) == "NEW"
    c.close()


def test_t14_revision_or_artifact_change_invalidates_human_approval(tmp_path):
    c = controller(tmp_path)
    c.request_human_checkpoint("cp", "rev-a", "artifact-a")
    with pytest.raises(ValueError, match="stale or mismatched"):
        c.approve_human_checkpoint("cp", "rev-b", "artifact-a")
    with pytest.raises(ValueError, match="stale or mismatched"):
        c.approve_human_checkpoint("cp", "rev-a", "artifact-b")
    assert c.snapshot["suspension_reason"] == "WAITING_FOR_HUMAN"
    c.approve_human_checkpoint("cp", "rev-a", "artifact-a")
    assert c.checkpoint_approved_for("rev-a", "artifact-a")
    assert not c.checkpoint_approved_for("rev-b", "artifact-a")
    c.request_human_checkpoint("cp", "rev-b", "artifact-b")
    assert not c.checkpoint_approved_for("rev-a", "artifact-a")
    c.close()


def test_t15_pause_and_cancel_do_not_claim_completion(tmp_path):
    c = controller(tmp_path)
    c.pause()
    assert c.snapshot["state"] == "SUSPENDED"
    assert c.snapshot["suspension_reason"] == "USER_PAUSED"
    assert c.propose_complete() is False
    with pytest.raises(RuntimeError, match="USER_PAUSED"):
        c.accept_remote_action("a1", {"kind": "read"})
    c.resume()
    assert c.snapshot["state"] == "WAITING_FOR_REMOTE"
    c.cancel()
    assert c.snapshot["state"] == "CANCELLED"
    assert c.propose_complete() is False
    assert c.verify_complete(True) is False
    c.close()


def test_t16_budgets_survive_restart_and_cosmetic_activity_stalls(tmp_path):
    path = tmp_path / "tasks.sqlite3"
    c = DurableTaskController("t", path)
    c.set_limits(max_remote_rounds=1, max_no_progress_rounds=2)
    assert c.accept_remote_action("a1", {"kind": "read"}) == "NEW"
    c.close()

    c = DurableTaskController("t", path)
    assert c.snapshot["remote_rounds_used"] == 1
    with pytest.raises(RuntimeError, match="budget exhausted"):
        c.accept_remote_action("a2", {"kind": "read"})
    assert c.snapshot["suspension_reason"] == "BUDGET_EXHAUSTED"
    c.close()

    s = DurableTaskController("stall", path)
    s.set_limits(max_no_progress_rounds=2)
    assert s.observe_progress("semantic-state-a") == "PROGRESS"
    assert s.observe_progress("semantic-state-a") == "NO_PROGRESS"
    assert s.observe_progress("semantic-state-a") == "STALLED"
    assert s.snapshot["suspension_reason"] == "STALLED"
    s.close()


def test_t17_active_execution_is_not_stalled_due_to_chat_silence(tmp_path):
    c = controller(tmp_path)
    c.set_limits(max_no_progress_rounds=1)
    assert c.accept_remote_action("a1", {"kind": "test"}) == "NEW"
    attempt = c.begin_attempt("a1")
    for _ in range(5):
        assert c.observe_progress("same-chat-view") == "ACTIVE_EXECUTION"
    assert c.snapshot["no_progress_rounds"] == 0
    assert c.snapshot["suspension_reason"] is None
    c.record_local_result("a1", attempt, "PASS", "test completed")
    assert c.snapshot["state"] == "WAITING_FOR_REMOTE"
    c.close()
