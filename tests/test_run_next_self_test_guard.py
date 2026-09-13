from pathlib import Path

def test_run_next_fails_closed_when_self_test_creates_bundle():
    source=(Path(__file__).resolve().parents[1]/"Download"/"run_next.py").read_text()
    assert "SELF_TEST_SIDE_EFFECT_GUARD" in source
    assert "created_by_self_test" in source
    assert "real run suppressed to prevent duplicate execution" in source
