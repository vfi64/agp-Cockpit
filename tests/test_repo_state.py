"""Plan P2 (AGP_REPO_STATE_V1): repository state model and Lagebericht."""
from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import build_freshness
from agp_cockpit.core import repo_state as rs

MAIN = "a" * 40


def facts(**kw):
    base = {"root": "/r", "is_git": True, "branch": "main", "head": MAIN, "origin_main": MAIN, "tracking_main": MAIN,
                "own_commits": 0, "kit_version": "1.0.13", "workspace": True, "gh_ok": True, "post_merge": "PASS"}
    base.update(kw)
    return rs.RepoFacts(**base)


@pytest.mark.parametrize("kw, state, recommended", [
    ({"task_running": True}, rs.LAEUFT, None),
    ({"is_git": False}, rs.UNKLAR, rs.LAGEBERICHT),
    ({"kit_version": None}, rs.UNKLAR, rs.LAGEBERICHT),
    ({"workspace": False}, rs.KEIN_KIT, rs.REPO_UEBERNEHMEN),
    ({"origin_main": None}, rs.UNKLAR, rs.LAGEBERICHT),
    ({"gh_ok": False}, rs.UNKLAR, rs.LAGEBERICHT),
    ({}, rs.BEREIT, rs.ARBEIT_BEGINNEN),
    ({"head": "b" * 40}, rs.STOERUNG, rs.WIEDERHERSTELLEN),
    ({"changes": ("src/x.py",)}, rs.STOERUNG, rs.WIEDERHERSTELLEN),
    ({"post_merge": "NOT_PASS"}, rs.STOERUNG, rs.WIEDERHERSTELLEN),
    ({"branch": ""}, rs.STOERUNG, rs.WIEDERHERSTELLEN),
    ({"branch": "feat/x", "own_commits": 2}, rs.IN_ARBEIT, rs.ABSCHLIESSEN),
    ({"branch": "feat/x", "own_commits": 2, "changes": ("a.py",)}, rs.IN_ARBEIT, rs.ARBEITEN),
    ({"branch": "feat/x", "own_commits": 0}, rs.IN_ARBEIT, rs.ARBEITEN),
    # live 2026-10-01: leftover admin-refresh branch at origin/main with a Kit status.md edit
    ({"branch": "docs/post-pr139-handoff-refresh", "own_commits": 0, "changes": (".agentic/state/status.md",)},
     rs.STOERUNG, rs.WIEDERHERSTELLEN),
])
def test_classify(kw, state, recommended):
    result = rs.classify(facts(**kw))
    assert (result.state, result.recommended) == (state, recommended)
    assert result.offered == rs.OFFERED[state]
    if recommended and state != rs.UNKLAR:
        assert recommended in result.offered


def test_volatile_kit_files_do_not_count_as_changes_but_are_reported():
    text = rs.describe(rs.classify(facts(volatile_changes=(".agentic/rule_ack/current.json",))))
    assert text.startswith("Zustand: BEREIT") and "Empfohlen: Arbeit beginnen" in text
    assert "1 Kit-intern" in text and "Kit: 1.0.13" in text


@pytest.fixture
def repo(tmp_path, monkeypatch):
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    root = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
    (root / ".agentic").mkdir()
    (root / ".agentic/config.yaml").write_text("x: 1\n")
    (root / "README").write_text("x")
    (root / ".gitignore").write_text(".venv/\n")
    subprocess.run([*git, "-C", str(root), "add", "-A"], check=True)
    subprocess.run([*git, "-C", str(root), "commit", "-qm", "c"], check=True)
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "-C", str(root), "remote", "add", "origin", str(origin)], check=True)
    subprocess.run(["git", "-C", str(root), "push", "-q", "origin", "main"], check=True)
    subprocess.run(["git", "-C", str(root), "fetch", "-q", "origin"], check=True)
    kit = root / ".venv/bin/agentic-kit"
    kit.parent.mkdir(parents=True)
    kit.write_text("#!/bin/sh\necho '{\"result_status\": \"PASS\"}'\n")
    kit.chmod(kit.stat().st_mode | stat.S_IEXEC)
    gh = root / ".venv/bin/gh"
    gh.write_text("#!/bin/sh\nexit 0\n")
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("AGP_COCKPIT_GH_BINARY", str(gh))
    return root, SimpleNamespace(binary=kit, version="9.9.9")


def test_observe_reads_a_real_repository(repo):
    root, kit = repo
    (root / ".agentic/rule_ack").mkdir()
    (root / ".agentic/rule_ack/current.json").write_text("{}")
    result = rs.classify(rs.observe(root, kit=kit))
    assert result.state == rs.BEREIT, rs.describe(result)
    assert result.facts.volatile_changes == (".agentic/rule_ack/current.json",)
    assert result.facts.post_merge == "PASS"
    subprocess.run(["git", "-C", str(root), "switch", "-q", "-c", "feat/x"], check=True)
    (root / "a.py").write_text("x")
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "add", "a.py"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "w"], check=True)
    working = rs.classify(rs.observe(root, kit=kit))
    assert (working.state, working.recommended, working.facts.own_commits) == (rs.IN_ARBEIT, rs.ABSCHLIESSEN, 1)


def test_lagebericht_writes_the_report_for_later_reading(repo, monkeypatch):
    root, kit = repo
    monkeypatch.setattr("agp_cockpit.core.kit_installation.discover", lambda r: kit)
    state = rs.lagebericht(root)
    report = json.loads((root / ".local/agp-cockpit/state/repo-state.json").read_text())
    assert report["state"] == state.state == rs.BEREIT
    assert report["facts"]["kit_version"] == "9.9.9"


def test_no_installed_kit_blocks_task_start(tmp_path):
    reason = build_freshness.start_block_reason(tmp_path)   # conftest: no Kit discovery
    assert reason.startswith("Blockiert — Agentic Project Kit ist nicht installiert")


def test_standard_tasks_tab_shows_the_lagebericht(monkeypatch, tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
    state = rs.classify(facts())
    monkeypatch.setattr("agp_cockpit.core.repo_state.lagebericht", lambda *a, **k: state)
    try:
        panel = m.StandardTasksPanel(root, repository_root=Path(tmp_path))
        panel.refresh_lage()
        for _ in range(50):
            root.update()
            if panel.repo_state is not None:
                break
            root.after(20)
        assert panel.repo_state is state
        assert panel.lage_var.get().startswith("Zustand: BEREIT")
    finally:
        root.destroy()


def test_first_porcelain_line_keeps_its_path():
    """A leading space in the status column must not shift the first path."""
    out = " M .agentic/state/status.md\n M Download/1_x.py\n?? src/new.py\n"

    def runner(argv, **_):
        if "--is-inside-work-tree" in argv:
            text = "true"
        else:
            text = {"status": out, "rev-parse": "a" * 40, "rev-list": "0"}.get(argv[1], "")
        return SimpleNamespace(returncode=0, stdout=text, stderr="")

    facts = rs.observe(Path("/r"), runner=runner, kit=SimpleNamespace(binary=Path("/k"), version="1"),
                       network=False)
    assert facts.changes == (".agentic/state/status.md", "src/new.py")
    assert facts.volatile_changes == ("Download/1_x.py",)


def test_without_gh_the_login_is_unknown_not_failed(repo, monkeypatch):
    root, kit = repo
    monkeypatch.setenv("AGP_COCKPIT_GH_BINARY", "none")
    assert rs.observe(root, kit=kit, network=False).gh_ok is None
