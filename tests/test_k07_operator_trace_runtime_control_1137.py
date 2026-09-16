from pathlib import Path
S=Path("chrome_extension/content.js").read_text(encoding="utf-8")
B=S[S.index("/* AGP_K07_OPERATOR_TRACE_RUNTIME_CONTROL_1137 */"):]
def test_default_off_and_existing_authority():
    assert "k07DebugTraceEnabled: false" in S
    assert "globalThis.__AGP_K07_TRACE__ = {" in S
def test_overlay_control_same_runtime_state():
    assert 'setK07DebugTraceEnabled(!STATE.k07DebugTraceEnabled, "overlay");' in B
    assert '"Trace aus" : "Trace an"' in B
def test_existing_client_event_logging():
    assert 'clientEvent("K07_DEBUG_TRACE_CONTROL"' in S
    assert 'void clientEvent("K07_DEBUG_TRACE", {' in S
    assert '"/v1/client-event"' in S
def test_no_second_store_or_page_world_bridge():
    for x in ("K07_TRACE_MAX_EVENTS","agp_k07_debug_trace_events","agp_k07_debug_trace_enabled","window.postMessage(","CustomEvent("):
        assert x not in B
    assert "chrome.storage.local.set" not in B
