from pathlib import Path

import pytest

from agp_cockpit.core.run_next_guard import (
    SELF_TEST_SIDE_EFFECT_GUARD,
    SelfTestSideEffectError,
    canonical_response_artifacts,
    require_self_test_no_canonical_artifacts,
)


def test_run_next_fails_closed_when_self_test_creates_bundle(tmp_path: Path):
    assert SELF_TEST_SIDE_EFFECT_GUARD == "SELF_TEST_SIDE_EFFECT_GUARD"

    download = tmp_path / "Download"
    download.mkdir()
    existing = download / "001_existing_return_bundle.json"
    existing.write_text("{}", encoding="utf-8")

    before = canonical_response_artifacts(download)
    created = download / "002_created_by_self_test_return_bundle.json"
    created.write_text("{}", encoding="utf-8")

    with pytest.raises(SelfTestSideEffectError) as exc_info:
        require_self_test_no_canonical_artifacts(before, download)

    message = str(exc_info.value)
    assert "created_by_self_test" in message
    assert "real run suppressed to prevent duplicate execution" in message
    assert str(created.resolve()) in message
    assert str(existing.resolve()) not in message
