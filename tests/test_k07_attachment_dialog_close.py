from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8")


def test_attachment_preview_closes_generic_ok_dialog_before_continuation():
    start = CONTENT.index("async function readAssistantButtonAttachment")
    end = CONTENT.index("async function fetchSingleAssistantPythonAttachment", start)
    function = CONTENT[start:end]

    assert 'label === "ok"' in function
    assert 'key:"Escape"' in function
    assert "K07 assistant attachment preview did not close" in function
    assert "K07_ATTACHMENT_PREVIEW_CLOSED" in function


def test_attachment_preview_close_is_verified_before_fetch_returns():
    start = CONTENT.index("async function readAssistantButtonAttachment")
    end = CONTENT.index("return {\n      ok: true,", start)
    function = CONTENT[start:end]

    assert function.index("if (stillOpen)") < function.index("K07_ATTACHMENT_PREVIEW_CLOSED")


def test_attachment_preview_restores_composer_focus_before_continuation():
    start = CONTENT.index("async function readAssistantButtonAttachment")
    end = CONTENT.index("async function fetchSingleAssistantPythonAttachment", start)
    function = CONTENT[start:end]

    assert "K07 composer focus could not be restored after attachment preview" in function
    assert "composer_focus:focusEvidence" in function
    assert function.index("target.focus()") < function.index("K07_ATTACHMENT_PREVIEW_CLOSED")
