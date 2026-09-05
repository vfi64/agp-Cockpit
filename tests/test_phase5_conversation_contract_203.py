import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_phase5_contract_is_loaded_before_legacy_content_script():
    manifest = json.loads(
        (ROOT / "chrome_extension" / "manifest.json").read_text(encoding="utf-8")
    )
    scripts = manifest["content_scripts"][0]["js"]
    assert "conversation_contract.js" in scripts
    assert "content.js" in scripts
    assert scripts.index("conversation_contract.js") < scripts.index("content.js")

def test_phase5_options_expose_configured_conversation_url():
    html = (ROOT / "chrome_extension" / "options.html").read_text(encoding="utf-8")
    js = (ROOT / "chrome_extension" / "options.js").read_text(encoding="utf-8")
    assert 'id="conversationUrl"' in html
    assert "conversationUrl" in js

def test_phase5_ui_is_separate_from_legacy_auto_send():
    content = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8")
    assert "AGP_PHASE5_CONVERSATION_UI_203" in content
    assert "phase5StageDraft" in content
    assert "phase5ConfirmAndSend" in content
    assert "window.confirm" in content
    assert "sendApprovedDraft" in content

def test_phase5_contract_remains_transport_only():
    contract = (
        ROOT / "chrome_extension" / "conversation_contract.js"
    ).read_text(encoding="utf-8").lower()
    forbidden = (
        "agentic-kit",
        "work order",
        "work_order",
        "mission_bootstrap",
        "git ",
        "github",
        "file_transfer",
        "/v1/turn",
        "/v1/client-event",
    )
    for token in forbidden:
        assert token not in contract

def test_phase5_contract_marker_is_hardened_204():
    contract = (
        ROOT / "chrome_extension" / "conversation_contract.js"
    ).read_text(encoding="utf-8")
    content = (
        ROOT / "chrome_extension" / "content.js"
    ).read_text(encoding="utf-8")
    marker = "AGP_PHASE5_CONVERSATION_CONTRACT_204"
    assert marker in contract
    assert marker in content

def test_phase5_explicit_confirmation_is_bound_to_draft_and_conversation():
    contract = (
        ROOT / "chrome_extension" / "conversation_contract.js"
    ).read_text(encoding="utf-8")
    assert "pendingApproval = null;" in contract
    assert "PHASE5_APPROVAL_DRAFT_CHANGED" in contract
    assert "PHASE5_APPROVAL_CONVERSATION_CHANGED" in contract
    assert "bindConfiguredConversation()" in contract

