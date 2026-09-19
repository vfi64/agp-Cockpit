from pathlib import Path


def test_protocol_authority_complete_baseline():
    text=Path('docs/planning/COMMUNICATION_PROTOCOL.md').read_text()
    sections=['## Participants and interfaces','## Event catalogue and layer state','## Cross-layer transition table','## Temporal sequence','## Identity and lifetime table','## Authorization matrix','## Retry, replay and idempotency','## Timeout ownership','## Error taxonomy','## Trace-to-spec conformance procedure','## Current acceptance baseline','## Documentation completion status']
    assert all(x in text for x in sections)
    assert 'detailed reconstruction is mandatory and ongoing' not in text
    assert 'No older Phase-7/8/9 E2E substitutes' in text
