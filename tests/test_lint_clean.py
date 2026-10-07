"""AGP_LINT_CLEAN_V1 (release 0.2.2, step 1852): the Kit's local feature gate runs
`ruff check src tests` and failed on 40 findings the CI never looked at. The suite keeps
both trees clean wherever ruff is installed (the CI image installs only pytest)."""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(importlib.util.find_spec("ruff") is None, reason="ruff not installed")
def test_src_and_tests_pass_ruff_like_the_kit_gate():
    result = subprocess.run([sys.executable, "-m", "ruff", "check", "--no-cache", "src", "tests"],
                            cwd=ROOT, capture_output=True, text=True, timeout=120, check=False)
    assert result.returncode == 0, result.stdout[-3000:]


def test_test_windows_are_invisible_unless_asked():
    """AGP_INVISIBLE_TEST_WINDOWS_V1: every Tk and Toplevel of the suite is made transparent;
    macOS reports the alpha back, the X server of the CI may ignore it."""
    import tkinter
    assert tkinter.Tk.__init__.__qualname__.startswith("_invisible_test_windows")
    assert tkinter.Toplevel.__init__.__qualname__.startswith("_invisible_test_windows")
    if sys.platform != "darwin":
        return
    try:
        root = tkinter.Tk()
    except tkinter.TclError:
        pytest.skip("no display")
    try:
        assert float(root.attributes("-alpha")) == 0.0
    finally:
        root.destroy()
