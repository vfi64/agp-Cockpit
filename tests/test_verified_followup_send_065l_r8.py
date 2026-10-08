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
