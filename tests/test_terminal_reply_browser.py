import shutil
import subprocess
from pathlib import Path

import pytest


def test_actual_content_script_consumes_terminal_reply_file():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required for actual content-script behavior test")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([node, str(root / "tests/terminal_reply_browser.cjs")],
                            cwd=root, capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
