from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8") + "\n" + SEND_JS
ADAPTER = (ROOT / "chrome_extension" / "chatgpt_dom.js").read_text(encoding="utf-8")   # AGP_DOM_ADAPTER_V1

def test_066_d4_scopes_send_control_to_active_composer_form():
    assert "function sendButton(anchor=null)" in SRC
    assert "const button = sendButton(composerEl);" in SRC
    assert "function isUsableSendControl(el)" in SRC
    assert 'const form = anchor && anchor.closest ? anchor.closest("form") : null;' in ADAPTER
    assert "if (isUsableSendControl(candidate)) return candidate;" in ADAPTER
    assert "!el.isConnected" in ADAPTER
    assert "r.width > 0 && r.height > 0" in ADAPTER

def test_066_d4_composer_mutation_is_provisional_not_decisive():
    assert 'provisionalComposerEvidence = !composerNow' in SRC
    assert '"composer_cleared"' in SRC
    assert '"composer_changed"' in SRC
    assert 'return {confirmed:true, via:"composer_cleared"}' not in SRC
    assert 'return {confirmed:true, via:"composer_changed"}' not in SRC
    assert "provisional:provisionalComposerEvidence" in SRC

def test_066_d4_keeps_decisive_positive_signals():
    assert 'via:"user_message"' in SRC
    assert "generation_started_observed" in SRC
    assert 'via:"generation_active"' not in SRC
    assert "SEND_ASSISTANT_ACTIVITY_OBSERVED" in SRC
    assert "authoritative_acceptance:false" in SRC

def test_066_d4_remains_bounded_and_fail_closed():
    assert "for (let i = 0; i < 60; i += 1)" in SRC
    assert "setTimeout(resolve, 250)" in SRC
    assert 'confirmed:false' in SRC
    assert 'via:"timeout"' in SRC
    assert 'STATE.lastEvent = "SEND_UNCONFIRMED"' in SRC
