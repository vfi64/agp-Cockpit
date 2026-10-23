"""AGP_CI_CONFIG_GUARD_V1 (live 2026-10-22, Kit repository step 65): a work order changed
`.github/workflows/ci.yml` to make a red test pass. A CI configuration change the mission does not
name stops the mission; the change stays in the worktree for the owner."""
import subprocess
from pathlib import Path

from agp_cockpit.core import ci_config_guard as guard

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "src/agp_cockpit/core/bridge_server.py").read_text(encoding="utf-8")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True,
                   capture_output=True)


def test_new_ci_paths_stop_unless_the_mission_names_them(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / ".github/workflows").mkdir(parents=True)
    (repo / ".github/workflows/ci.yml").write_text("on: push\n")
    (repo / "a.py").write_text("x = 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-q", "-u", "origin", "main")
    git(repo, "switch", "-q", "-c", "feat/x")
    before = guard.changed_ci_paths(repo)
    assert before == set()
    (repo / "a.py").write_text("x = 2\n")                               # ordinary work: no CI path
    assert guard.changed_ci_paths(repo) == set()
    (repo / ".github/workflows/ci.yml").write_text("on: push\n# fetch-depth: 0\n")
    (repo / ".agentic/ci").mkdir(parents=True)
    (repo / ".agentic/ci/agentic-gate.yaml").write_text("x\n")          # untracked counts as well
    after = guard.changed_ci_paths(repo)
    assert after == {".github/workflows/ci.yml", ".agentic/ci/agentic-gate.yaml"}
    stop = guard.violation(before, after, "Fix the failing test in tests/test_a.py")
    assert stop.startswith("CI-Konfiguration geändert") and ".github/workflows/ci.yml" in stop
    assert "nicht in der CI umgangen" in stop
    named = "Raise the browser job timeout in .github/workflows/ci.yml and .agentic/ci/agentic-gate.yaml"
    assert guard.violation(before, after, named) == ""
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "ci")                                      # committed on the branch
    assert guard.changed_ci_paths(repo) == after
    assert guard.violation(after, after, "") == ""                        # changed earlier: not this order


def test_an_unreadable_repository_is_no_evidence(tmp_path):
    assert guard.changed_ci_paths(tmp_path) == set()


def test_the_bridge_stops_the_mission_after_the_work_order():
    assert "ci_before = changed_ci_paths(repo_root)" in BRIDGE
    assert BRIDGE.index("ci_before = changed_ci_paths(repo_root)") < BRIDGE.index("consume_command_file(")
    block = BRIDGE[BRIDGE.index("ci_before = changed_ci_paths(repo_root)"):]
    assert 'engine.runtime.final("BLOCKED", ci_stop)' in block
    assert '"CI_CONFIG_CHANGE_BLOCKED"' in block
    assert "mission_now.mission_text" in block


def test_the_work_order_rule_names_the_guard_in_both_copies():
    from agp_cockpit.core.command_file_contract import WORK_ORDER_KIT_RULE
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    sentence = "do not change .github/workflows/ or .agentic/ci/ unless the task names the file"
    assert sentence in WORK_ORDER_KIT_RULE and sentence in content


CI_EDITING_RUNNER = (
    "import sys, json\nfrom pathlib import Path\n"
    "n=int(sys.argv[1]);d=Path(__file__).parent\n"
    "w=d.parent/'.github'/'workflows';w.mkdir(parents=True,exist_ok=True)\n"
    "(w/'ci.yml').write_text('on: push\\n# fetch-depth: 0\\n')\n"
    "(d/f'{n:03d}_ok_return_bundle.json').write_text(json.dumps({'status':'PASS'}))\n"
)


def _guarded_bridge(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    import test_human_decision as h
    git(tmp_path, "init", "-q", "-b", "main")
    monkeypatch.setattr(h, "RUNNER", CI_EDITING_RUNNER)
    return h, h._bridge(tmp_path)


def test_a_work_order_that_edits_the_ci_blocks_the_mission(tmp_path, monkeypatch):
    h, gen = _guarded_bridge(tmp_path, monkeypatch)
    root, runtime, call = next(gen)
    try:
        h.mission(call, runtime)
        answer = call("/v1/file-loop/command", {"filename": "1480_status.py",
                                                "content": h.work_order(["transfer", "divergence-status"])})
        assert answer["state"] == "BLOCKED" and answer["terminal"] is True
        assert ".github/workflows/ci.yml" in answer["human_reason"]
        assert call("/v1/status")["mission"]["state"] == "BLOCKED"
        assert (root / ".github/workflows/ci.yml").exists()          # left for the owner to inspect
    finally:
        gen.close()


def test_a_mission_that_names_the_ci_file_may_change_it(tmp_path, monkeypatch):
    from agp_cockpit.core.start_request import StartRequestStore
    h, gen = _guarded_bridge(tmp_path, monkeypatch)
    _root, runtime, call = next(gen)
    try:
        created = call("/v1/mission", {"title": "Task · ci", "execution_mode": "LIVE", "run_mode": "FULL_AUTO",
                                       "mission_text": "Raise the timeout in .github/workflows/ci.yml"})["mission"]
        StartRequestStore(runtime).request(created["mission_id"], task_id="T")
        answer = call("/v1/file-loop/command", {"filename": "1480_status.py",
                                                "content": h.work_order(["transfer", "divergence-status"])})
        assert answer["state"] != "BLOCKED" and answer.get("terminal") is not True
    finally:
        gen.close()
