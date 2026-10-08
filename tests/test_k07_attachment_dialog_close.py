from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8") + (ROOT / "chrome_extension" / "cockpit_ingress.js").read_text(encoding="utf-8")   # AGP_INGRESS_MODULE_V1: content.js + its ingress module


def test_attachment_preview_closes_generic_ok_dialog_before_continuation():
    start = CONTENT.index("async function readAssistantButtonAttachment")
    end = CONTENT.index("async function fetchSingleAssistantPythonAttachment", start)
    function = CONTENT[start:end]

    assert 'label === "ok"' in function
    assert 'key:"Escape"' in function
    assert "K07 assistant attachment preview did not close" in function
    assert "K07_ATTACHMENT_PREVIEW_CLOSED" in function


def test_attachment_preview_supports_chatgpt_artifact_side_panel():
    preview_start = CONTENT.index("function readableAttachmentPreview")
    preview_end = CONTENT.index("async function readAssistantButtonAttachment", preview_start)
    helpers = CONTENT[preview_start:preview_end]
    assert "function attachmentPreviewContainer" in helpers
    assert "AGP_DOM.previewTextbox(filename)" in helpers
    # AGP_DOM_ADAPTER_V1 (slice 3c): the preview contract lives in the page adapter.
    adapter = (ROOT / "chrome_extension" / "chatgpt_dom.js").read_text(encoding="utf-8")
    adapter += (ROOT / "chrome_extension" / "chatgpt_selectors.js").read_text(encoding="utf-8")   # AGP_SELECTOR_TABLE_V1
    assert "[role=\"textbox\"][aria-label]" in adapter
    assert "label === expectedName" in adapter
    assert 'label === "herunterladen"' in adapter


def test_attachment_is_committed_only_after_successful_processing():
    tick_start = CONTENT.index("async function tick()")
    tick_end = CONTENT.index("// AGP_LEGACY_PATHS_REMOVED_V1", tick_start)
    tick = CONTENT[tick_start:tick_end]

    direct_process = tick.index("await processCompletedAssistant(lastAssistantText(), runGeneration);")
    direct_commit = tick.index("STATE.lastProcessedAssistantAttachmentKey = attachmentKey;", direct_process)
    stable_process = tick.index("await processCompletedAssistant(completed, runGeneration);")
    stable_commit = tick.index("STATE.lastProcessedAssistantAttachmentKey = attachmentKey;", stable_process)

    assert direct_process < direct_commit
    assert stable_process < stable_commit


def test_attachment_preview_close_is_verified_before_fetch_returns():
    start = CONTENT.index("async function readAssistantButtonAttachment")
    end = CONTENT.index("return downloadedContent;", start)
    function = CONTENT[start:end]

    assert function.index("if (stillOpen)") < function.index("K07_ATTACHMENT_PREVIEW_CLOSED")
    assert function.index("K07_ATTACHMENT_PREVIEW_CLOSED") < function.index("if (downloadError) throw downloadError;")


def test_attachment_preview_restores_composer_focus_before_continuation():
    start = CONTENT.index("async function readAssistantButtonAttachment")
    end = CONTENT.index("async function fetchSingleAssistantPythonAttachment", start)
    function = CONTENT[start:end]

    assert "K07 composer focus could not be restored after attachment preview" in function
    assert "composer_focus:focusEvidence" in function
    assert function.index("target.focus()") < function.index("K07_ATTACHMENT_PREVIEW_CLOSED")
