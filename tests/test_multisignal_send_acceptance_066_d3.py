from pathlib import Path

ROOT = Path("/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit")
SRC = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8")

def test_066_d3_has_multisignal_acceptance():
    assert 'via:"user_message"' in SRC
    assert '"composer_cleared"' in SRC
    assert '"composer_changed"' in SRC
    assert 'return {confirmed:true, via:"composer_cleared"}' not in SRC
    assert 'return {confirmed:true, via:"composer_changed"}' not in SRC
    assert 'via:"generation_started"' in SRC
    assert 'via:"assistant_activity"' in SRC

def test_066_d3_snapshots_composer_and_generation_after_population():
    p1 = SRC.index("setComposerText(composerEl, prompt);")
    p2 = SRC.index("const beforeComposerText = observedComposerText();", p1)
    p3 = SRC.index("const beforeGenerationActive = chatgptGenerationActive();", p2)
    p4 = SRC.index("const acknowledgement = await waitForSentUserMessage(", p3)
    assert p1 < p2 < p3 < p4

def test_066_d3_bounded_and_fail_closed():
    assert "for (let i = 0; i < 60; i += 1)" in SRC
    assert "setTimeout(resolve, 250)" in SRC
    assert "confirmed:false" in SRC
    assert 'via:"timeout"' in SRC
    assert 'STATE.lastEvent = "SEND_UNCONFIRMED"' in SRC
    assert 'STATE.lastEvent = "PROMPT_SENT"' in SRC
