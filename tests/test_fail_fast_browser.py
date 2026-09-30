import shutil
import subprocess
from pathlib import Path

import pytest


def test_rejection_fail_fast_build_gate_and_stop_reason_in_actual_content_script():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required for actual content-script behavior test")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([node, str(root / "tests/fail_fast_browser.cjs")],
                            cwd=root, capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
