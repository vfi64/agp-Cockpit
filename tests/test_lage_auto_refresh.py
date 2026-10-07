"""AGP_LAGE_AUTO_REFRESH_V1 (live 2026-10-03): branch checkouts and Kit upgrades
outside the Cockpit rebuild the Lage without a click."""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from agp_cockpit.core.repo_state import local_fingerprint
from agp_cockpit.ui.standard_tasks_panel import StandardTasksPanel


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@x", *args], cwd=root,
                   check=True, capture_output=True)


def test_fingerprint_follows_head_branch_and_installed_kit(tmp_path):
    assert local_fingerprint(tmp_path) is None            # no git repository
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("a")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-qm", "a")
    first = local_fingerprint(tmp_path)
    assert first == local_fingerprint(tmp_path)          # stable without changes
    _git(tmp_path, "checkout", "-q", "-b", "work")
    switched = local_fingerprint(tmp_path)
    assert switched != first
    (tmp_path / "b.txt").write_text("b")
    _git(tmp_path, "add", "b.txt")
    _git(tmp_path, "commit", "-qm", "b")
    committed = local_fingerprint(tmp_path)
    assert committed != switched
    site = tmp_path / ".venv/lib/python3.14/site-packages"
    (site / "agentic_project_kit-1.0.13.dist-info").mkdir(parents=True)
    old_kit = local_fingerprint(tmp_path)
    (site / "agentic_project_kit-1.0.13.dist-info").rename(site / "agentic_project_kit-1.0.14.dist-info")
    assert local_fingerprint(tmp_path) != old_kit


def _panel(*, running=False, busy=False):
    calls = SimpleNamespace(refreshed=0, scheduled=0)
    panel = SimpleNamespace(
        repository_root=Path("/repo"), _lage_fingerprint=None,
        _lage_result=None if busy else [], _task_running=lambda: running, _watch_lage=None,
    )
    panel.refresh_lage = lambda: setattr(calls, "refreshed", calls.refreshed + 1)
    panel.after = lambda _ms, _fn: setattr(calls, "scheduled", calls.scheduled + 1)
    return panel, calls


def test_watch_refreshes_once_per_change_and_never_during_a_run(monkeypatch):
    import agp_cockpit.core.repo_state as rs
    for running, busy, expected in ((False, False, 1), (True, False, 0), (False, True, 0)):
        panel, calls = _panel(running=running, busy=busy)
        sequence = iter([("a",), ("a",), ("b",), ("b",)])
        monkeypatch.setattr(rs, "local_fingerprint", lambda _root, sequence=sequence: next(sequence))
        for _ in range(4):
            StandardTasksPanel._watch_lage(panel)
        assert calls.refreshed == expected, (running, busy)
        assert calls.scheduled == 4
