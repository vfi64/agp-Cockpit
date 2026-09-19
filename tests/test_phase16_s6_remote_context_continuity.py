from pathlib import Path

from agp_cockpit.core.task_controller import DurableTaskController


def make(tmp_path: Path):
    return DurableTaskController("t-s6", tmp_path / "runtime.sqlite3")

def test_t23_chat_switch_preserves_budgets_and_old_binding_loses_authority(tmp_path):
    c=make(tmp_path)
    c.set_limits(max_remote_rounds=7,max_local_actions=9,max_no_progress_rounds=3)
    old=c.bind_remote_context("chat-A")
    c.accept_remote_action("a1",{"cmd":"observe"})
    before=c.snapshot.copy()
    new=c.bind_remote_context("chat-B")
    after=c.snapshot
    assert new==old+1
    for key in ("remote_rounds_used","local_actions_used","retries_used","no_progress_rounds","controller_generation"):
        assert after[key]==before[key]
    assert not c.binding_has_execution_authority(old)
    assert c.binding_has_execution_authority(new)
    c.close()

def test_t24_context_refresh_preserves_current_task_control_and_valid_binding(tmp_path):
    c=make(tmp_path)
    epoch=c.bind_remote_context("chat-A")
    c.request_human_checkpoint("cp-1","rev-1","artifact-1")
    refresh=c.remote_context_refresh()
    assert refresh["task_id"]=="t-s6"
    assert refresh["binding_epoch"]==epoch
    assert refresh["conversation_ref"]=="chat-A"
    assert refresh["state"]=="SUSPENDED"
    assert refresh["suspension_reason"]=="WAITING_FOR_HUMAN"
    assert refresh["checkpoint_id"]=="cp-1"
    assert refresh["checkpoint_revision"]=="rev-1"
    assert refresh["checkpoint_artifact_hash"]=="artifact-1"
    c.close()

def test_binding_epoch_and_refresh_survive_restart(tmp_path):
    db=tmp_path/"runtime.sqlite3"
    c=DurableTaskController("t-s6",db)
    assert c.bind_remote_context("chat-A")==1
    c.close()
    c=DurableTaskController("t-s6",db)
    assert c.active_remote_binding()["conversation_ref"]=="chat-A"
    assert c.bind_remote_context("chat-B")==2
    c.close()
    c=DurableTaskController("t-s6",db)
    assert c.active_remote_binding()["binding_epoch"]==2
    assert not c.binding_has_execution_authority(1)
    assert c.remote_context_refresh()["conversation_ref"]=="chat-B"
    c.close()

def test_empty_binding_is_rejected(tmp_path):
    c=make(tmp_path)
    try:
        c.bind_remote_context("")
        assert False, "empty binding accepted"
    except ValueError:
        pass
    c.close()

def test_t25_remote_context_capability_rules():
    assert DurableTaskController.negotiate_remote_context_version([1,2]) == 2
    assert DurableTaskController.negotiate_remote_context_version([2,3]) == 2
    for offered in ([1], [3], []):
        try:
            DurableTaskController.negotiate_remote_context_version(offered)
            assert False, "incompatible context schema accepted"
        except RuntimeError as exc:
            assert "CAPABILITY_MISMATCH" in str(exc)

