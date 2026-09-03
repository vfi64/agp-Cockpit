from pathlib import Path

SRC = (
    Path(__file__).resolve().parents[1]
    / "chrome_extension"
    / "content.js"
).read_text(encoding="utf-8")


def test_066_d3_snapshots_composer_and_generation_after_population():
    populate = SRC.index("setComposerText(composerEl, prompt);")
    composer_snapshot = SRC.index(
        "const beforeComposerText = observedComposerText();",
        populate,
    )
    generation_snapshot = SRC.index(
        "const beforeGenerationActive = chatgptGenerationActive();",
        composer_snapshot,
    )
    wait_call = SRC.index("waitForSentUserMessage(", generation_snapshot)

    assert populate < composer_snapshot < generation_snapshot < wait_call


def test_066_d3_wait_contract_receives_pre_send_observations():
    wait_call = SRC.index("waitForSentUserMessage(")
    window = SRC[wait_call : wait_call + 500]

    assert "beforeMessages" in window
    assert "beforeAssistantText" in window
    assert "beforeComposerText" in window
    assert "beforeGenerationActive" in window
