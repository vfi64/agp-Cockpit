from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT=Path(__file__).resolve().parents[1]
CONTENT=(ROOT/"chrome_extension/content.js").read_text(encoding="utf-8") + "\n" + SEND_JS
def test_k07_autorun_waits_for_chatgpt_composer_readiness():
    assert "async function waitForComposer" in CONTENT
    assert "    await waitForComposer();" in CONTENT   # AGP_DEGRADED_DOM_PATH_REMOVED_V1: the native send waits
    assert 'throw new Error("ChatGPT composer not ready after 20s")' in CONTENT
