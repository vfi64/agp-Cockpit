from pathlib import Path
C=Path('chrome_extension/content.js').read_text()
def test_reload_does_not_discard_pending_explicit_start():
 b=C[C.index('async function pollExplicitTaskStartRequest()'):C.index('async function refreshStatus()')]
 assert 'if (!AGP_TASK_FIRST_START_REQUEST_PRIMED)' in b
 assert 'AGP_TASK_FIRST_AUTOSTART_GENERATION = generation;\n        AGP_TASK_FIRST_START_REQUEST_PRIMED = true;\n        return;' not in b
 assert 'if (!generation)' in b
 assert 'generation <= AGP_TASK_FIRST_AUTOSTART_GENERATION' in b
def test_existing_identity_and_virtualization_repairs_remain():
 assert 'function selectedAssistantMessageNode()' in C
 assert 'STATE.observedAssistantMessageId' in C
