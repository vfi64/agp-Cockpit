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
