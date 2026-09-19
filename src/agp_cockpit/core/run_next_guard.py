from __future__ import annotations

from pathlib import Path

SELF_TEST_SIDE_EFFECT_GUARD = "SELF_TEST_SIDE_EFFECT_GUARD"


class SelfTestSideEffectError(RuntimeError):
    """Raised when a work-script self-test creates canonical response artifacts."""

    def __init__(self, created_artifacts: list[Path]) -> None:
        self.created_artifacts = created_artifacts
        super().__init__(format_self_test_side_effect_message(created_artifacts))


def canonical_response_artifacts(download_dir: Path) -> set[Path]:
    return {
        path.resolve()
        for path in download_dir.glob("*_return_bundle.json")
        if path.is_file()
    }


def format_self_test_side_effect_message(created_artifacts: list[Path]) -> str:
    names = "\n  ".join(str(path) for path in created_artifacts)
    return (
        "Self-test produced canonical response artifact(s); "
        "real run suppressed to prevent duplicate execution:\n  " + names
    )


def require_self_test_no_canonical_artifacts(
    before_artifacts: set[Path],
    download_dir: Path,
) -> None:
    created_by_self_test = sorted(
        canonical_response_artifacts(download_dir) - {path.resolve() for path in before_artifacts}
    )
    if created_by_self_test:
        raise SelfTestSideEffectError(created_by_self_test)
