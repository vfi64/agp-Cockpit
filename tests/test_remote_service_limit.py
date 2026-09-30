import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_remote_service_limit_classifier_and_fail_closed_ordering():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required for content-script behavior test")
    result = subprocess.run(
        [node, str(ROOT / "tests/remote_service_limit.cjs")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    source = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    tick = source[source.index("  async function tick()") :]
    service_limit = tick.index("const serviceLimit = classifyRemoteServiceLimit(text);")
    attachment_error = tick.index("K07_FILE_TRANSFER_ATTACHMENT_REQUIRED")
    command_file = tick.index("const directCommandFiles = assistantPythonAttachmentCandidates();")
    assert command_file < service_limit < attachment_error
    assert 'await stop(serviceLimit.message, "REMOTE_SERVICE_LIMIT");' in tick
