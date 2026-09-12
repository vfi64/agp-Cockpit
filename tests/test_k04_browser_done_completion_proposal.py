from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")


def _phase8_block() -> str:
    start = CONTENT.index("async function phase8RunMultiRound()")
    end = CONTENT.index("function phase8Pause()", start)
    return CONTENT[start:end]


def test_browser_done_submits_durable_completion_proposal_only():
    block = _phase8_block()
    assert 'out.state === "DONE"' in block
    assert '"/v1/task/complete-proposal"' in block
    assert '"session_id":sessionId' in block or 'session_id:sessionId' in block
    assert '"COMPLETE_PROPOSED"' in block
    assert "verify_completion_contract" not in block
    assert "VERIFIED_COMPLETE" not in block


def test_non_done_round_does_not_submit_completion_proposal():
    block = _phase8_block()
    done_if = block.index('out.state === "DONE"')
    proposal = block.index('"/v1/task/complete-proposal"')
    assert done_if < proposal
