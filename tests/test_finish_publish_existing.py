"""AGP_FINISH_PUBLISH_EXISTING_V1 (workflow-friction plan C3, V8): the work is already committed and
the branch is clean. „Abschließen“ knows this state, its prompt says that the Kit publishes the
existing commits without a path selection (K1, Kit 1.4.0), and the finish guard stays: on a clean
start it rejects a commit and now also a finish call that selects paths, naming call and line."""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import finish_guard as fg
from agp_cockpit.core import kit_installation
from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.standard_tasks import BY_KEY

FINISH = "agentic-kit work finish"
CLEAN = {"dirty": []}


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=repo, text=True, capture_output=True, check=True)
    return done.stdout.strip()


@pytest.fixture
def branch(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / ".gitignore").write_text("/Download/*\n")
    (root / "a.txt").write_text("a\n")
    git(root, "add", ".")
    git(root, "commit", "-qm", "base")
    git(root, "update-ref", "refs/remotes/origin/main", "main")
    git(root, "switch", "-q", "-c", "feat/x")
    (root / "b.txt").write_text("b\n")
    git(root, "add", "b.txt")
    git(root, "commit", "-qm", "work")
    return root


# --- the guard -----------------------------------------------------------------------------------

def test_a_finish_call_with_a_path_is_rejected_on_a_clean_start_with_call_and_line():
    order = 'import subprocess\nsubprocess.run(["agentic-kit", "work", "finish", "--branch", "feat/x",\n' \
            '                "--path", "b.txt", "--execute", "--json"])\n'
    found = fg.violations(order, CLEAN, [FINISH])
    assert len(found) == 1
    assert "line 2: agentic-kit work finish --branch feat/x --path b.txt" in found[0]
    assert "K1" in found[0] and "AGP_FINISH_PUBLISH_EXISTING_V1" in found[0]


def test_a_finish_call_without_a_path_passes_on_a_clean_start():
    order = 'subprocess.run(["agentic-kit", "work", "finish", "--branch", "feat/x", "--title", "T",\n' \
            '                "--message", "T", "--execute", "--json"])\n'
    assert fg.violations(order, CLEAN, [FINISH]) == []


def test_a_path_appended_at_run_time_counts_and_is_named():
    order = ('ARGS = ["agentic-kit", "work", "finish", "--branch", "feat/x", "--execute", "--json"]\n'
             'for p in ["b.txt"]:\n'
             '    ARGS += ["--path", p]\n'
             'subprocess.run(ARGS)\n')
    found = fg.violations(order, CLEAN, [FINISH])
    assert len(found) == 1 and "line 1: agentic-kit work finish" in found[0] and "frei in line 3" in found[0]


def test_a_path_in_a_docstring_does_not_count():
    order = ('"""Later: agentic-kit work finish --path b.txt --execute"""\n'
             'subprocess.run(["agentic-kit", "work", "finish", "--branch", "feat/x", "--execute", "--json"])\n')
    assert fg.violations(order, CLEAN, [FINISH]) == []


def test_paths_stay_allowed_when_arbeiten_left_uncommitted_work():
    order = 'subprocess.run(["agentic-kit", "work", "finish", "--branch", "feat/x", "--path", "b.txt"])\n'
    assert fg.violations(order, {"dirty": [" M b.txt"]}, [FINISH]) == []


def test_the_commit_rule_of_the_guard_is_unchanged():
    used = ["agentic-kit transfer commit"]
    assert len(fg.violations("x = 1", CLEAN, used)) == 1
    assert fg.violations("x = 1", {"dirty": [" M b.txt"]}, used) == []


# --- the state -----------------------------------------------------------------------------------

def test_existing_commits_names_count_and_publication(branch):
    assert fg.existing_commits(branch) == {"branch": "feat/x", "commits": 1, "published": "none"}
    git(branch, "update-ref", "refs/remotes/origin/feat/x", "HEAD")
    assert fg.existing_commits(branch)["published"] == "head"
    (branch / "c.txt").write_text("c\n")
    git(branch, "add", "c.txt")
    git(branch, "commit", "-qm", "more")
    assert fg.existing_commits(branch) == {"branch": "feat/x", "commits": 2, "published": "older"}


def test_no_existing_commits_state_for_open_work_main_or_an_empty_branch(branch):
    (branch / "Download").mkdir()
    (branch / "Download/2299_x.py").write_text("x\n")             # ignored, and Download/ never counts
    assert fg.existing_commits(branch) is not None
    (branch / "b.txt").write_text("changed\n")
    assert fg.existing_commits(branch) is None                   # uncommitted work: Arbeiten left it
    git(branch, "checkout", "-q", "--", "b.txt")
    git(branch, "switch", "-q", "main")
    assert fg.existing_commits(branch) is None
    git(branch, "switch", "-q", "-c", "feat/empty")
    assert fg.existing_commits(branch) is None


@pytest.mark.parametrize("version, expected", [("1.4.0", True), ("1.10.2", True), ("2.0.0rc1", True),
                                               ("1.3.0", False), ("0.9.9", False), ("", None), ("x", None)])
def test_k1_is_in_the_kit_from_1_4_0(version, expected):
    assert fg.kit_publishes_existing(version) is expected


# --- the prompt ----------------------------------------------------------------------------------

def _kit(monkeypatch, version):
    monkeypatch.setattr(kit_installation, "discover",
                        lambda root: SimpleNamespace(version=version) if version is not None else None)


def test_the_finish_prompt_states_the_committed_work_and_names_no_kit_command(branch, monkeypatch):
    _kit(monkeypatch, "1.4.0")
    prompt = BY_KEY["finish"].prompt(branch, {})
    assert "AGP_FINISH_PUBLISH_EXISTING_V1" in prompt
    assert "carries 1 commit(s) that origin/main lacks (not published yet)" in prompt
    assert "publishes existing commits when it gets no path option (K1" in prompt
    for command in ("work finish", "transfer commit", "pr-create", "agentic-kit work"):
        assert command not in prompt, command
    _kit(monkeypatch, None)                                       # Kit not found: the K1 text stays
    assert "no path option (K1" in BY_KEY["finish"].prompt(branch, {})


def test_an_old_kit_gets_no_k1_promise(branch, monkeypatch):
    _kit(monkeypatch, "1.3.0")
    prompt = BY_KEY["finish"].prompt(branch, {})
    assert "The installed Kit 1.3.0 cannot publish existing commits" in prompt
    assert "NEEDS_HUMAN" in prompt and "„Kit übernehmen“" in prompt
    assert "no path option (K1" not in prompt


def test_no_situation_text_while_work_is_uncommitted(branch, monkeypatch):
    _kit(monkeypatch, "1.4.0")
    (branch / "b.txt").write_text("changed\n")
    assert "AGP_FINISH_PUBLISH_EXISTING_V1" not in BY_KEY["finish"].prompt(branch, {})


# --- the Lage ------------------------------------------------------------------------------------

HEAD = "b" * 40


@pytest.mark.parametrize("remote, where", [("", "noch nicht veröffentlicht"), (HEAD, "veröffentlicht;"),
                                           ("c" * 40, "lokal neuer als origin")])
def test_the_lage_names_whether_the_commits_are_on_github(remote, where):
    facts = rs.RepoFacts(root="/r", is_git=True, branch="feat/x", head=HEAD, origin_main="a" * 40,
                         tracking_main="a" * 40, own_commits=2, kit_version="1.4.0", workspace=True,
                         gh_ok=True, branch_published=bool(remote), published_head=remote,
                         published_remote=remote, branch_relation=rs.AHEAD if remote else "")
    state = rs.classify(facts)
    assert state.recommended == rs.ABSCHLIESSEN
    assert f"2 Commit(s), sauber, {where}" in state.summary
