from pathlib import Path

B=Path("chrome_extension/background.js").read_text()
C=Path("chrome_extension/content.js").read_text()
def test_sink():
 assert B.count("agpK07NativeTrace1165(")==5
 assert "[AGP_K07_NATIVE_TRACE_1161]" not in B
 assert 'message.type === "AGP_K07_NATIVE_TRACE_1165"' in C
 assert 'clientEvent("K07_NATIVE_TRACE"' in C


def test_trace_is_delivered_to_originating_tab_content_script():
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required for native trace delivery test")
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [node, str(root / "tests/native_trace_delivery.cjs")],
        cwd=root, capture_output=True, text=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
