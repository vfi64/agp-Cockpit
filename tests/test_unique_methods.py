"""AGP_UNIQUE_METHODS_V1 (live 2026-10-06, P4 Repo wechseln): MainWindow defined ``_relaunch``
twice; the later definition (rebuild button) silently replaced the repository switch's one,
and „Wechseln und neu starten“ failed with a TypeError. No class or module may define the
same name twice."""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"


def _duplicates(body, where: str) -> list[str]:
    seen: dict[str, int] = {}
    found = []
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            decorators = {getattr(d, "attr", getattr(d, "id", "")) for d in node.decorator_list}
            if decorators & {"setter", "deleter", "overload", "register"}:
                continue
            if node.name in seen:
                found.append(f"{where}: {node.name} (lines {seen[node.name]} and {node.lineno})")
            seen[node.name] = node.lineno
        if isinstance(node, ast.ClassDef):
            found += _duplicates(node.body, f"{where}.{node.name}")
    return found


def test_no_name_is_defined_twice_in_a_class_or_module():
    found = []
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        found += _duplicates(tree.body, str(path.relative_to(SRC)))
    assert found == []


def test_the_check_sees_a_duplicate_method():
    tree = ast.parse("class W:\n    def a(self): pass\n    def a(self, home): pass\n")
    assert _duplicates(tree.body, "m") == ["m.W: a (lines 2 and 3)"]
