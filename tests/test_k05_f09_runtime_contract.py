import json
import pytest

from agp_cockpit.core.task_controller import DurableTaskController
from agp_cockpit.core.task_store import TaskStore


def make_controller(tmp_path, *, remote=2, local=2):
    controller = DurableTaskController("task-k05", tmp_path / "tasks.sqlite3")
    controller.set_limits(max_remote_rounds=remote, max_local_actions=local)
    return controller


def test_admission_reserves_and_dispatch_consumes_local_budget(tmp_path):
    c = make_controller(tmp_path, remote=2, local=1)
    epoch = c.bind_remote_context("chat-a")
    assert c.accept_remote_action("a1", {"binding_epoch": epoch, "effect": "read"}) == "NEW"
    reservation = c.store.reservation_for(c.task_id, "a1")
    assert reservation["remote_round_state"] == "CONSUMED"
    assert reservation["local_action_state"] == "RESERVED"
    assert c.snapshot["remote_rounds_used"] == 1
    assert c.snapshot["local_actions_used"] == 0
    with pytest.raises(RuntimeError, match="max_local_actions"):
        c.accept_remote_action("a2", {"binding_epoch": epoch, "effect": "read"})
    c.begin_attempt("a1")
    reservation = c.store.reservation_for(c.task_id, "a1")
    assert reservation["local_action_state"] == "CONSUMED"
    assert c.snapshot["local_actions_used"] == 1


def test_binding_epoch_is_rechecked_at_dispatch(tmp_path):
    c = make_controller(tmp_path)
    old_epoch = c.bind_remote_context("chat-a")
    c.accept_remote_action("a1", {"binding_epoch": old_epoch, "effect": "read"})
    c.bind_remote_context("chat-b")
    with pytest.raises(PermissionError, match="stale remote binding at dispatch"):
        c.begin_attempt("a1")


def test_acceptance_binds_implicit_epoch_and_rejects_explicit_stale_epoch(tmp_path):
    c = make_controller(tmp_path)
    old_epoch = c.bind_remote_context("chat-a")
    new_epoch = c.bind_remote_context("chat-b")
    assert c.accept_remote_action("a1", {"effect": "read"}) == "NEW"
    assert c.store.reservation_for(c.task_id, "a1")["binding_epoch"] == new_epoch
    with pytest.raises(PermissionError, match="stale remote binding"):
        c.accept_remote_action("a2", {"binding_epoch": old_epoch, "effect": "read"})


def test_deadline_checked_at_acceptance_and_dispatch(tmp_path):
    c = make_controller(tmp_path)
    epoch = c.bind_remote_context("chat-a")
    c.store.set_runtime_contract(c.task_id, goal="finish K05", scope=["repo"], deadline_utc="2999-01-01T00:00:00+00:00")
    c.accept_remote_action("a1", {"binding_epoch": epoch, "effect": "read"})
    c.store.set_runtime_contract(c.task_id, goal="finish K05", scope=["repo"], deadline_utc="2000-01-01T00:00:00+00:00")
    with pytest.raises(RuntimeError, match="deadline"):
        c.begin_attempt("a1")


def test_canonical_resume_context_contains_f09_contract_fields(tmp_path):
    c = make_controller(tmp_path)
    epoch = c.bind_remote_context("chat-a")
    c.store.set_runtime_contract(c.task_id, goal="finish K05", scope=["repository", "current task"], deadline_utc="2999-01-01T00:00:00+00:00")
    c.set_task_authority(repository_root=tmp_path, allowed_effects=["read"], allowed_tools=["python"])
    c.accept_remote_action("a1", {"binding_epoch": epoch, "effect": "read"})
    ctx = c.remote_context_refresh()
    assert ctx["goal_scope_deadline"]["goal"] == "finish K05"
    assert json.loads(ctx["goal_scope_deadline"]["scope_json"]) == ["repository", "current task"]
    assert ctx["authority"] is not None
    assert "evidence" in ctx
    assert "open_effects" in ctx
    assert "approvals" in ctx
    assert "budgets" in ctx
    assert "completion_contract" in ctx
