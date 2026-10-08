from pathlib import Path

SOURCE = Path(
    "chrome_extension/content.js"
).read_text(encoding="utf-8")


def test_live_bootstrap_is_mode_aware():
    assert 'mission.execution_mode === "LIVE"' in SOURCE
    assert "This mission is LIVE." in SOURCE


def test_existing_loop_and_completion_guards_remain():
    assert "ASSISTANT_RESPONSE_COMPLETE" in SOURCE
    assert "stablePollsRequired: 3" in SOURCE
    assert "maxTurns: 40" in SOURCE
    assert "maxErrors: 3" in SOURCE
