from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

SRC = (
    Path(__file__).resolve().parents[1]
    / "chrome_extension"
    / "content.js"
).read_text(encoding="utf-8") + "\n" + SEND_JS


def test_r8_only_marks_prompt_sent_after_confirmed_acceptance():
    wait_call = SRC.index("waitForSentUserMessage(")
    accepted = SRC.index(
        "transport.transition(SEND_TRANSPORT.ACCEPTED",
        wait_call,
    )
    prompt_sent = SRC.index(
        'STATE.lastEvent = "PROMPT_SENT"',
        accepted,
    )

    assert wait_call < accepted < prompt_sent


def test_r8_timeout_is_not_unconditionally_treated_as_send_failure():
    unconfirmed = SRC.index("if (!acknowledgement.confirmed)")
    indeterminate = SRC.index(
        "transport.transition(SEND_TRANSPORT.INDETERMINATE",
        unconfirmed,
    )
    hard_failure_guard = SRC.index(
        "positiveUnsentEvidence && transport.retryCount > 0",
        unconfirmed,
    )

    assert unconfirmed < hard_failure_guard < indeterminate


def test_r8_hard_failure_requires_positive_unsent_evidence_after_retry():
    guard = SRC.index(
        "positiveUnsentEvidence && transport.retryCount > 0"
    )
    failure = SRC.index(
        'throw new Error(',
        guard,
    )
    failure_text = SRC[failure : failure + 220]

    assert "positive evidence shows the prompt is still unsent" in failure_text


def test_r8_indeterminate_path_does_not_mark_prompt_sent():
    indeterminate = SRC.index(
        "transport.transition(SEND_TRANSPORT.INDETERMINATE"
    )
    return_after = SRC.index("return;", indeterminate)
    prompt_sent = SRC.index(
        'STATE.lastEvent = "PROMPT_SENT"',
        return_after,
    )

    assert indeterminate < return_after < prompt_sent
