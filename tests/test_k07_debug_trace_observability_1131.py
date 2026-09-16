from pathlib import Path
C=Path("chrome_extension/content.js").read_text()
def test_default_off_and_control():
 assert "k07DebugTraceEnabled: false" in C and "__AGP_K07_TRACE__" in C
def test_existing_client_event_path():
 b=C[C.index("function k07DebugTrace"):C.index("async function clientEvent")]
 assert 'clientEvent("K07_DEBUG_TRACE"' in b and "fetch(" not in b and "chrome.storage.local" not in b
def test_sync_parser_not_made_async():
 a=C.index('k07DebugTrace("JSON_PARSE_ATTEMPT"');b=C.index("JSON.parse(candidateText)",a)
 assert "await k07DebugTrace" not in C[a:b]
def test_failure_path_events():
 for x in ("PROMPT_SEND_REQUESTED","PROMPT_SENT","ASSISTANT_OBSERVED","JSON_PARSE_ATTEMPT","JSON_PARSE_SUCCESS","FORMAT_REPAIR_STARTED","FORMAT_REPAIR_EXHAUSTED"):assert f'"{x}"' in C
