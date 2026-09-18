from agp_cockpit.core.bridge_runtime import BridgeRuntime


def test_correlated_transport_failure_survives_restart_without_failing_task(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    mission = runtime.create_mission(title="Fixture", mission_text="test")
    assert runtime.record_browser_transport("MISSION_BOOTSTRAP_SEND_FAILED", {
        "mission_id": mission.mission_id, "reason": "No confirmation",
    })
    restored = BridgeRuntime(tmp_path).require_state()
    assert restored.browser_transport_event == "MISSION_BOOTSTRAP_SEND_FAILED"
    assert restored.browser_transport_note == "No confirmation"
    assert restored.browser_transport_blocked is True
    assert restored.browser_transport_block_reason == "No confirmation"
    assert restored.browser_transport_recovery_attempts == 0
    assert restored.state == "READY"
    assert restored.turn_count == 0


def test_stale_or_unscoped_event_cannot_change_current_transport(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    mission = runtime.create_mission(title="Fixture", mission_text="test")
    for details in ({}, {"mission_id": "old-mission"}):
        assert not runtime.record_browser_transport("NATIVE_TRANSPORT_FAILED", details)
    assert not runtime.record_browser_transport("COMPLETE", {"mission_id": mission.mission_id})
    assert runtime.require_state().browser_transport_event == ""
    assert runtime.record_browser_transport("NATIVE_SEND_ACCEPTED", {"mission_id": mission.mission_id})
    assert runtime.require_state().browser_transport_event == "NATIVE_SEND_ACCEPTED"


def test_fresh_extension_handshake_clears_transport_block(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    mission = runtime.create_mission(title="Fixture", mission_text="test")
    runtime.record_browser_transport("NATIVE_TRANSPORT_FAILED", {
        "mission_id": mission.mission_id, "reason": "INSERT_NOT_VERIFIED",
    })
    assert runtime.require_state().browser_transport_blocked is True
    assert runtime.record_browser_transport("EXTENSION_HANDSHAKE", {
        "version": "0.3.1", "handled_refresh_generation": 7,
    })
    restored = BridgeRuntime(tmp_path).require_state()
    assert restored.browser_transport_blocked is False
    assert restored.browser_transport_block_reason == ""


def test_new_mission_does_not_inherit_previous_transport_failure(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    old = runtime.create_mission(title="Old", mission_text="test")
    runtime.record_browser_transport("NATIVE_TRANSPORT_FAILED", {"mission_id": old.mission_id})
    new = runtime.create_mission(title="New", mission_text="test")
    assert new.browser_transport_event == ""
