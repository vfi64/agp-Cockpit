from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTENT=(ROOT/"chrome_extension/content.js").read_text(encoding="utf-8")
def test_k07_autorun_waits_for_chatgpt_composer_readiness():
    assert "async function waitForComposer" in CONTENT
    assert "const composerEl = await waitForComposer();" in CONTENT
    assert 'throw new Error("ChatGPT composer not ready after 20s")' in CONTENT
