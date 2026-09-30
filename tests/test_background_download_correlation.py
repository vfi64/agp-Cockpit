import shutil
import subprocess
from pathlib import Path

import pytest


def test_background_download_correlation_survives_worker_restart():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required for background download correlation test")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [node, str(root / "tests/background_download_correlation.cjs")],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
