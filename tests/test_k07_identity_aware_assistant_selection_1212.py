from pathlib import Path

C=Path("chrome_extension/content.js").read_text()
B=Path("chrome_extension/background.js").read_text()
def test_identity_aware_selection():
 assert "function selectedAssistantMessageNode()" in C
 assert "STATE.observedAssistantMessageId" in C
 assert "const baselineIds = assistantBaselineIds()" in C
 assert '!baselineIds.has(id) && !id.startsWith("request-placeholder")' in C
 assert "STATE.observedAssistantMessageId = newestMessageId;" in C
def test_temporary_diagnostics_removed():
 assert "AGP_K07_ASSISTANT_ATTACHMENT_DOM_DIAGNOSTIC_TRIGGER_1207" not in C
 assert "AGP_K07_ASSISTANT_ATTACHMENT_DOM_DIAGNOSTIC_1203" not in B
