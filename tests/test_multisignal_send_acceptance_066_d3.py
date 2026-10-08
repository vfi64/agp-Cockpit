from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

SRC = (
    Path(__file__).resolve().parents[1]
    / "chrome_extension"
    / "content.js"
).read_text(encoding="utf-8") + "\n" + SEND_JS


def test_066_d3_wait_contract_receives_pre_send_observations():
    wait_call = SRC.index("waitForSentUserMessage(")
    window = SRC[wait_call : wait_call + 500]

    assert "beforeMessages" in window
    assert "beforeAssistantText" in window
    assert "beforeComposerText" in window
    assert "beforeGenerationActive" in window
