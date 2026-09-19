from pathlib import Path


def test_consumer_decision_events_use_canonical_client_event():
 s=Path('chrome_extension/content.js').read_text();b=s[s.index('async function pollExplicitTaskStartRequest()'):s.index('async function refreshStatus()')];assert 'clientEvent("TASK_START_REQUEST_SUPPRESSED"' in b;assert 'clientEvent("TASK_START_REQUEST_ACCEPTED"' in b;assert 'reason:"generation"' in b and 'reason:"mission_identity"' in b
