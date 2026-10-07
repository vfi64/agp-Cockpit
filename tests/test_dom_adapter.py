"""AGP_DOM_ADAPTER_V1 (DOM hardening step 3, slice 3a, owner 2026-10-07): ChatGPT's page
structure is named in chrome_extension/chatgpt_dom.js, loaded by the manifest before
content.js. This slice moves the file-card and assistant-turn touchpoints; the selector
count of content.js may only fall (ratchet). Real-Chromium checks:
tests/e2e/test_k07_expected_step_attachment.spec.js and test_composer_resolver.spec.js."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "chrome_extension"
CONTENT = (EXT / "content.js").read_text(encoding="utf-8")
ADAPTER = (EXT / "chatgpt_dom.js").read_text(encoding="utf-8")

# Ratchet: lower it whenever a slice moves selectors out of content.js; never raise it.
CONTENT_SELECTOR_CALLS = 10


def test_the_manifest_loads_the_adapter_right_before_content_js():
    js = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))["content_scripts"][0]["js"]
    assert js.index("chatgpt_dom.js") == js.index("content.js") - 1


def test_the_adapter_is_one_frozen_namespace_with_the_contracted_touchpoints():
    assert ADAPTER.lstrip().startswith("// AGP_DOM_ADAPTER_V1")
    exported = ADAPTER[ADAPTER.index("globalThis.AGP_DOM = Object.freeze({"):]
    exported = exported[:exported.index("});")]
    for name in ("SELECTORS", "assistantTurns", "fileCardRow", "stepFileCards", "alertNotices",
                 "composerFallback", "isUsableSendControl", "sendButton", "generationActive",
                 "stopLikeButtonVisible", "previewTextbox", "previewContainer", "previewDownloadButton",
                 "openDialog", "dialogCloseControl"):
        assert name in exported, name
    assert "const SELECTORS = Object.freeze({" in ADAPTER
    assert ADAPTER.count("globalThis.") == 1                  # nothing else leaks into the page


def test_content_js_delegates_the_moved_touchpoints():
    for wrapper, call in (("function assistantMessageNodes()", "AGP_DOM.assistantTurns()"),
                          ("function pythonAttachmentRow(anchor)", "AGP_DOM.fileCardRow(anchor)"),
                          ('function expectedStepAttachmentCandidates(expectedStep, kind="command")',
                           "AGP_DOM.stepFileCards(expectedStep, kind)"),
                          ("function isUsableSendControl(el)", "AGP_DOM.isUsableSendControl(el)"),
                          ("function sendButton(anchor=null)", "AGP_DOM.sendButton(anchor)"),
                          ("function chatgptGenerationActive()", "AGP_DOM.generationActive()"),
                          ("function stopLikeComposerButtonVisible()", "AGP_DOM.stopLikeButtonVisible()"),
                          ("function readableAttachmentPreview(filename)", "AGP_DOM.previewTextbox(filename)"),
                          ("function attachmentPreviewContainer(preview)", "AGP_DOM.previewContainer(preview)"),
                          ("function attachmentPreviewDownloadButton(preview)",
                           "AGP_DOM.previewDownloadButton(preview)")):
        body = CONTENT[CONTENT.index(wrapper):]
        body = body[:body.index("\n  }\n")]
        assert call in body and "querySelector" not in body, wrapper
    for moved in ('button[aria-label="Datei herunterladen"]', 'a[href], button, [role="button"]',
                  'button[data-testid="send-button"]', 'button[aria-label*="Generierung stoppen"]',
                  "'#prompt-textarea'", "form button, [data-testid*='composer'] button",
                  "Vollbildmodus beenden", ".cm-content[role=\"textbox\"]"):
        assert moved not in CONTENT and moved in ADAPTER, moved


def test_content_js_selector_count_only_falls():
    calls = len(re.findall(r"querySelector(?:All)?\(", CONTENT))
    assert calls <= CONTENT_SELECTOR_CALLS, (
        f"content.js has {calls} querySelector calls (limit {CONTENT_SELECTOR_CALLS}); "
        "new page lookups belong in chrome_extension/chatgpt_dom.js (AGP_DOM_ADAPTER_V1)")
