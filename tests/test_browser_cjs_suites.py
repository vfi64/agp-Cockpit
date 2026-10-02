"""Run the Node content-script suites that had no Python wrapper (the
orphan guard of T3 ran only by hand) and the T5d retry suite."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("suite", ["orphan_guard_browser.cjs", "send_not_ready_retry.cjs"])
def test_content_script_suite(suite):
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required")
    result = subprocess.run([node, str(ROOT / "tests" / suite)], cwd=ROOT, capture_output=True,
                            text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
