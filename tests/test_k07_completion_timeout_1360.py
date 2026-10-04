from pathlib import Path


def test_gui_authority_forwarded_at_all_legacy_calls():
    s=Path("src/agp_cockpit/app_bootstrap.py").read_text()
    assert "run_legacy_gui(root)" not in s
    assert s.count("run_legacy_gui(root, local_contract=local_contract)") == 3
def test_k07_assistant_wait_is_bounded_and_accounting_remains_transition_derived():
    s=Path("chrome_extension/content.js").read_text()
    assert "AGP_K07_ASSISTANT_WAIT_TIMEOUT_1360" in s
    assert "K07_ASSISTANT_RESPONSE_TIMEOUT after ${waitExpiry.waitedSeconds}s" in s
    assert "AGP_K07_ASSISTANT_ACTIVITY_WAIT_V1" in s   # 180 s without activity, 900 s maximum
    assert "assistantWaitStartedAt" in s
    assert "STATE.turns += 1;" in s


def test_k07_tick_scheduler_observes_async_failures():
    s=Path("chrome_extension/content.js").read_text()
    assert "function scheduleTick()" in s
    assert "void tick().catch(error =>" in s
    assert 'clientEvent("TICK_UNHANDLED_ERROR"' in s
    assert "setInterval(tick, LIMITS.pollMs)" not in s
    assert "scheduleTick();" in s


def test_k07_tick_captures_generation_before_polling_can_fail():
    s=Path("chrome_extension/content.js").read_text()
    tick=s[s.index("async function tick()"):s.index("const LIVE_PROBE")]
    assert tick.index("const runGeneration = STATE.runGeneration;") < tick.index("try {")
    assert tick.index("try {") < tick.index("await pollOperatorControl();")
