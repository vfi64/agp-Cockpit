"""AGP_PANEL_LIVE_STATUS_V1: the bridge panel refreshes its counters while a mission runs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8")
EVIDENCE = (ROOT / "chrome_extension" / "native_message_evidence.js").read_text(encoding="utf-8")


def _block(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin)]


def test_live_refresh_runs_in_every_tick_before_the_wait_gate():
    tick = _block(CONTENT, "async function tick()", "if (!STATE.running || !STATE.waitingForAssistant) return;")
    assert "await refreshLiveMissionStatus();" in tick


def test_live_refresh_is_observational_and_throttled():
    fn = _block(CONTENT, "async function refreshLiveMissionStatus()", "async function submitAssistant(text)")
    assert "LIVE_STATUS_INTERVAL_MS" in CONTENT and "const LIVE_STATUS_INTERVAL_MS = 5000;" in CONTENT
    assert "agpMergeLiveMission(STATE.mission, result && result.mission)" in fn
    for forbidden in ("STATE.state =", "STATE.note =", "STATE.nextLocalStep =", "STATE.lastEvent =", "clientEvent("):
        assert forbidden not in fn


def test_merge_takes_only_the_counters_of_the_same_mission():
    fn = _block(EVIDENCE, "function agpMergeLiveMission(", "function agpMissionPhaseText(")
    assert "fresh.mission_id !== current.mission_id) return null" in fn
    assert "turn_count:" in fn and "step_count:" in fn


def test_processing_phase_is_timed_and_always_reset():
    assert "STATE.processingStartedAt = Date.now();" in CONTENT
    block = _block(CONTENT, "STATE.processingStartedAt = Date.now();", "if (directCommandFiles.length > 1)")
    finally_part = block[block.index("} finally {"):]
    assert "STATE.processingStartedAt = 0;" in finally_part
    assert 'STATE.processingFile = "";' in finally_part
    assert "? agpMissionPhaseText(STATE, Date.now()) : \"\"" in CONTENT
