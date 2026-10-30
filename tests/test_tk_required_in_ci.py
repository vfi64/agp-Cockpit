"""AGP_TK_TESTS_IN_CI_V1: CI runs the Tk tests for real; a missing tkinter or display is a failure."""
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agentic/ci/agentic-gate.yaml"


def test_ci_runs_the_suite_under_xvfb_and_requires_tk():
    steps = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["jobs"]["python"]["steps"]
    pytest_step = next(step for step in steps if "pytest" in str(step.get("run", "")))
    assert "xvfb-run -a python -m pytest" in pytest_step["run"]
    assert pytest_step.get("env", {}).get("AGP_REQUIRE_TK") == "1"
    assert "import tkinter" in pytest_step["run"]          # fails early and readable without Tk


def test_a_tk_skip_fails_when_tk_is_required(tmp_path):
    (tmp_path / "conftest.py").write_text((ROOT / "tests/conftest.py").read_text(encoding="utf-8"),
                                          encoding="utf-8")
    (tmp_path / "test_probe.py").write_text(textwrap.dedent("""
        import pytest

        def test_tk_skip():
            pytest.skip("no display")

        def test_other_skip():
            pytest.skip("Node required")
    """), encoding="utf-8")

    def run(required: str) -> str:
        env = dict(os.environ, AGP_REQUIRE_TK=required)
        done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(tmp_path)],
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120, check=False)
        return done.stdout
    assert "2 skipped" in run("0")
    required = run("1")
    assert "1 failed" in required and "1 skipped" in required and "AGP_REQUIRE_TK=1" in required
