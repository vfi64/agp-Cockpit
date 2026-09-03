from __future__ import annotations

from agp_cockpit.core.automation_guard import AutomationLimits
from agp_cockpit.core.bridge_engine import BridgeEngine


def test_new_mission_reset_clears_all_automation_guard_budgets(tmp_path):
    engine = BridgeEngine(
        tmp_path,
        limits=AutomationLimits(
            max_turns=40,
            max_runtime_seconds=7200.0,
            max_identical_assistant_messages=2,
            max_identical_prompts=2,
            max_consecutive_errors=3,
        ),
    )

    engine.guard.started_at = -40000.0
    engine.guard.turns = 17
    engine.guard.consecutive_errors = 2
    engine.guard._assistant_counts["old"] = 2
    engine.guard._prompt_counts["old"] = 2

    engine.reset_automation_guard()

    assert engine.guard.started_at is None
    assert engine.guard.turns == 0
    assert engine.guard.consecutive_errors == 0
    assert engine.guard._assistant_counts == {}
    assert engine.guard._prompt_counts == {}


def test_persistent_engine_can_start_fresh_mission_after_long_idle(tmp_path, monkeypatch):
    from agp_cockpit.core import automation_guard as guard_module

    engine = BridgeEngine(
        tmp_path,
        limits=AutomationLimits(max_runtime_seconds=2.0),
    )

    times = iter([50000.0, 50000.1])
    monkeypatch.setattr(guard_module, "monotonic", lambda: next(times))

    engine.reset_automation_guard()
    assert engine.guard.started_at is None

    engine.guard.before_turn()
    engine.guard.record_assistant("bounded work order")

    assert engine.guard.started_at == 50000.0
