"""AGP_TK_FIRST_ROOT_IDLE_V1: no test inherits Tk's pending showRootWindow task (macOS SIGTRAP).

The crash reports of the owner's Mac (order 2311, seven of 2026-11-15) all abort on the main thread in
`root.update()` → TclServiceIdle → showRootWindow → Tk_MacOSXGetTkWindow. tests/tk_first_root.py
explains the one-time idle task of Tk 9 on macOS; the session fixture of tests/conftest.py runs it on a
throwaway root before any test window exists.
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "tests" / "tk_first_root_probe.py"


def test_the_session_consumes_the_first_root_idle_task_before_any_test_window():
    tree = ast.parse((ROOT / "tests" / "conftest.py").read_text(encoding="utf-8"))
    fixture = next(node for node in tree.body
                   if isinstance(node, ast.FunctionDef) and node.name == "_invisible_test_windows")
    calls = [node for node in ast.walk(fixture) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == "consume_first_root_idle"]
    assert len(calls) == 1
    wrapped = next(node for node in ast.walk(fixture) if isinstance(node, ast.FunctionDef) and node.name == "wrap")
    assert calls[0].lineno < wrapped.lineno   # before the first test window can exist


def test_consuming_needs_no_display_and_no_tkinter(monkeypatch):
    sys.path.insert(0, str(ROOT / "tests"))
    try:
        import tk_first_root
    finally:
        sys.path.remove(str(ROOT / "tests"))
    monkeypatch.setitem(sys.modules, "tkinter", None)
    assert tk_first_root.consume_first_root_idle() is False


@pytest.mark.skipif(sys.platform != "darwin", reason="macOS only: showRootWindow is part of Tk's Aqua port")
def test_a_prewarmed_process_survives_a_stale_first_root(tmp_path):
    """Without the consumed task this sequence aborts with SIGTRAP on macOS (probe mode stale)."""
    tk = pytest.importorskip("tkinter")
    try:
        tk.Tk().destroy()
    except tk.TclError:
        pytest.skip("no display")
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT / "src"), env.get("PYTHONPATH", "")]))
    done = subprocess.run([sys.executable, str(PROBE), "prewarmed"], cwd=ROOT, env=env, text=True,
                          capture_output=True, timeout=120, check=False)
    assert done.returncode == 0 and "survived" in done.stdout, (
        f"rc={done.returncode}\n{done.stdout[-1500:]}\n{done.stderr[-3000:]}")
