"""AGP_TK_WORKER_PLAIN_VALUES_V1: a worker thread never holds a Tk object.

A worker that holds `self` (a window or panel) keeps it alive past the end of its owner. When the
worker ends, the old window is cyclic garbage that the next automatic collection frees on whatever
thread runs it; Tcl then aborts the process (the SIGTRAP of the Mac test runs 2299–2303, where the
Lage worker waits for `git ls-remote origin`). Workers get plain values; the UI thread reads their
answer (AGP_TK_GC_ON_MAIN_THREAD_V1).
"""
from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src" / "agp_cockpit"
PROBE = ROOT / "tests" / "tk_worker_probe.py"


def _imports_tkinter(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(alias.name.split(".")[0] == "tkinter" for alias in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tkinter":
            return True
    return False


def _is_thread_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    return (isinstance(func, ast.Name) and func.id == "Thread") or (
        isinstance(func, ast.Attribute) and func.attr == "Thread")


def worker_violations(source: str, label: str = "<source>") -> tuple[int, list[str]]:
    """Every Thread start in `source`: (count, problems). A target is a nested function or a lambda
    of the same scope and never names `self`."""
    tree = ast.parse(source)
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    count, problems = 0, []
    for call in [node for node in ast.walk(tree) if _is_thread_call(node)]:
        count += 1
        where = f"{label}:{call.lineno}"
        targets = [keyword.value for keyword in call.keywords if keyword.arg == "target"]
        if len(targets) != 1 or len(call.args) > 1:
            problems.append(f"{where}: Thread without exactly one target= keyword")
            continue
        target = targets[0]
        if isinstance(target, ast.Lambda):
            function: ast.AST | None = target
        elif isinstance(target, ast.Name):
            scope = parents.get(call)
            while scope is not None and not isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                scope = parents.get(scope)
            function = next((node for node in ast.walk(scope) if isinstance(node, ast.FunctionDef)
                             and node.name == target.id and parents.get(node) is scope), None) if scope else None
            if function is None and isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
                problems.append(f"{where}: target {target.id} is not a function of the same scope")
                continue
        else:
            problems.append(f"{where}: target {ast.unparse(target)} is not a plain function (bound method?)")
            continue
        if function is not None and any(isinstance(node, ast.Name) and node.id == "self"
                                        for node in ast.walk(function)):
            problems.append(f"{where}: worker {ast.unparse(target)[:40]} uses self (a Tk object)")
    return count, problems


def test_no_worker_of_a_tk_module_holds_self():
    total, problems = 0, []
    for path in sorted(SOURCE.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if not _imports_tkinter(ast.parse(source)):
            continue
        count, found = worker_violations(source, str(path.relative_to(ROOT)))
        total += count
        problems += found
    assert problems == []
    assert total >= 7   # the known workers of the UI (Lage, Branch, Systemcheck, Kit-Befunde x2, Release x2)


def test_the_guard_finds_a_worker_that_holds_self():
    source = '''
import threading
class W:
    def a(self):
        threading.Thread(target=lambda: self.go(), daemon=True).start()
    def b(self):
        def work():
            return self.root
        threading.Thread(target=work, daemon=True).start()
    def c(self):
        threading.Thread(target=self.go, daemon=True).start()
    def d(self):
        root = self.root
        def work():
            return root
        threading.Thread(target=work, daemon=True).start()
'''
    count, problems = worker_violations(source)
    assert count == 4 and len(problems) == 3
    assert ":5:" in problems[0] and ":9:" in problems[1] and ":11:" in problems[2]


def test_the_four_workers_get_plain_values():
    panel = (SOURCE / "ui" / "standard_tasks_panel.py").read_text(encoding="utf-8")
    assert "holder.append(lagebericht(root, task_running=running))" in panel
    main = (SOURCE / "ui" / "main_window.py").read_text(encoding="utf-8")
    assert "branch_switch.switch(root, binary, name, env=tool_env(root))" in main
    check = (SOURCE / "ui" / "system_check_window.py").read_text(encoding="utf-8")
    assert "run, root = self._run, self._root_path" in check and "holder.append(run(root))" in check
    findings = (SOURCE / "ui" / "kit_findings_window.py").read_text(encoding="utf-8")
    assert "holder.append(sync(root))" in findings


def test_a_slow_lage_worker_does_not_abort_a_later_collection(tmp_path):
    """The probe as a process: on the previous code Tcl aborts it (rc 134 on Linux, SIGTRAP on the Mac)."""
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    root.destroy()
    root = None
    repository = tmp_path / "repo"
    repository.mkdir()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT / "src"), env.get("PYTHONPATH", "")]))
    done = subprocess.run([sys.executable, str(PROBE), str(repository)], cwd=ROOT, env=env,
                          text=True, capture_output=True, timeout=120, check=False)
    assert done.returncode == 0 and "survived" in done.stdout, (
        f"rc={done.returncode}\n{done.stdout[-1500:]}\n{done.stderr[-3000:]}")
