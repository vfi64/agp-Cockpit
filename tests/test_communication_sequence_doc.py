from pathlib import Path


def test_communication_sequence_is_versioned_and_observable():
    text = Path("docs/engineering/COMMUNICATION_SEQUENCE.md").read_text(encoding="utf-8")
    for event in (
        "K07_ASSISTANT_ATTACHMENT_OBSERVED",
        "K07_COMMAND_ACCEPTED",
        "K07_RESULT_BUNDLE_CREATED",
        "CONTINUATION_SENT",
        "K07_ASSISTANT_WAIT_TIMEOUT",
    ):
        assert event in text
    assert "application version" in text
    assert "bridge build" in text
