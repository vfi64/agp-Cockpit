import pytest

from agp_cockpit.core.automation_guard import (
    AutomationGuard,
    AutomationLimits,
)


def test_turn_budget():
    guard = AutomationGuard(
        AutomationLimits(max_turns=1)
    )
    guard.before_turn()
    guard.success()

    with pytest.raises(RuntimeError):
        guard.before_turn()


def test_identical_assistant_loop():
    guard = AutomationGuard(
        AutomationLimits(
            max_identical_assistant_messages=1
        )
    )
    guard.record_assistant("same")

    with pytest.raises(RuntimeError):
        guard.record_assistant("same")


def test_consecutive_error_budget():
    guard = AutomationGuard(
        AutomationLimits(max_consecutive_errors=2)
    )
    guard.error()

    with pytest.raises(RuntimeError):
        guard.error()

def test_runtime_budget_starts_on_first_guarded_action(monkeypatch):
    from agp_cockpit.core import automation_guard as module

    clock = iter([10000.0, 10000.5])
    monkeypatch.setattr(module, "monotonic", lambda: next(clock))

    guard = AutomationGuard(
        AutomationLimits(max_runtime_seconds=2.0)
    )

    assert guard.started_at is None
    guard.before_turn()
    assert guard.started_at == 10000.0

    guard.record_assistant("first")
