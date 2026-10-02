"""T5: standard-task framework (P5), Abschließen (P6), Arbeit beginnen (P7),
Wiederherstellen as the R6 fallback, start-click approval, local verifiers."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core import standard_verifier as sv
from agp_cockpit.core.human_decision import HumanDecisionStore
from agp_cockpit.core.kit_command_catalog import (
    KitCommandCatalog,
    command_catalog_violations,
)
from agp_cockpit.core.merged_branch_guard import force_violations
from agp_cockpit.core.standard_tasks import BY_KEY, WORK_START_SCOPE, standard_tasks
from agp_cockpit.core.verbs import BY_KEY as VERBS
from agp_cockpit.core.verbs import availability

ROOT = Path(__file__).resolve().parents[1]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


def commit(repo: Path, name: str, text: str) -> None:
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"           # conftest puts HOME into tmp_path
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    commit(root, ".gitignore", ".local/\n")   # as in the real repository
    commit(root, "base.txt", "a\n")
    git(root, "update-ref", "refs/remotes/origin/main", "main")
    return root


# --- P5 definitions -------------------------------------------------------------

def test_every_standard_verb_has_a_task_and_later_slices_stay_disabled():
    assert {t.key for t in standard_tasks()} == {"chat-switch", "finish", "work-start", "recover"}
    for key in (rs.ABSCHLIESSEN, rs.ARBEIT_BEGINNEN, rs.WIEDERHERSTELLEN, rs.CHAT_WECHSELN):
        verb = VERBS[key]
        assert verb.slice is None and verb.task_key in BY_KEY
    assert {VERBS[k].slice for k in (rs.REPO_UEBERNEHMEN, rs.RELEASE, rs.PFLEGE)} == {"P9", "P11", "P10"}


def test_new_goal_texts_name_no_kit_command():
    for key in ("finish", "work-start", "recover"):
        task = BY_KEY[key]
        prompt = task.prompt(ROOT, {"kind": "feat", "name": "demo"} if task.inputs else None)
        for command in ("pr-create", "pr-closeout", "work finish", "remote-work-start", "work recover",
                        "post-merge-complete", "sync-main"):
            assert command not in prompt, (key, command)
        assert "command digest" in prompt


def test_finish_scope_is_the_lifecycle_and_nothing_else():
    scope = BY_KEY["finish"].approved_scope
    assert "agentic-kit transfer pr-create-complete" in scope and "agentic-kit transfer pr-closeout-complete" in scope
    assert not any("release" in c or "workspace" in c for c in scope)
    assert BY_KEY["finish"].ci_gate_merge and BY_KEY["finish"].confirm
    assert BY_KEY["work-start"].approved_scope == WORK_START_SCOPE
    assert BY_KEY["recover"].approved_scope is None and BY_KEY["chat-switch"].approved_scope is None


# --- prechecks ----------------------------------------------------------------------

def test_finish_precheck_never_from_main_and_only_with_own_changes(repo):
    finish = BY_KEY["finish"]
    assert "nie von main" in finish.check(repo)
    git(repo, "switch", "-q", "-c", "feat/x")
    assert "nichts" in finish.check(repo)                 # no own commits, clean
    (repo / "wip.txt").write_text("w\n")
    assert finish.check(repo) is None                     # uncommitted work may be finished
    git(repo, "add", "wip.txt")
    git(repo, "commit", "-q", "-m", "wip")
    assert finish.check(repo) is None
    commit_main = git(repo, "rev-parse", "HEAD")
    git(repo, "update-ref", "refs/remotes/origin/main", commit_main)   # merged as is
    assert "bereits gemergt" in finish.check(repo)


def test_work_start_precheck_validates_inputs_and_existing_branches(repo):
    start = BY_KEY["work-start"]
    assert "Art" in start.check(repo, {"kind": "x", "name": "demo"})
    assert "Name" in start.check(repo, {"kind": "feat", "name": "Bad Name"})
    assert start.check(repo, {"kind": "feat", "name": "demo"}) is None
    git(repo, "branch", "feat/demo")
    assert "existiert schon" in start.check(repo, {"kind": "feat", "name": "demo"})
    (repo / "dirty.txt").write_text("d\n")
    assert "ungesicherte" in start.check(repo, {"kind": "feat", "name": "other"})
    contract = start.contract(repo, {"kind": "fix", "name": "other"})
    assert contract["completion_contract"] == {"kind": sv.KIND, "verifier": "work-started",
                                               "params": {"branch": "fix/other"}}


# --- start-click approval (R4) ----------------------------------------------------------

def test_pre_approval_is_claimed_by_the_first_mission_and_limited_to_its_scope(tmp_path):
    store = HumanDecisionStore(tmp_path)
    scope = BY_KEY["finish"].approved_scope
    store.pre_approve(task_id="t1", label="Abschließen", scope=scope)
    grant = store.grant_for_mission("t1", "m1", mission_ended=False)
    assert grant is not None and "agentic-kit transfer pr-create-complete" in grant["scope"]
    assert store.permits("t1", ["agentic-kit transfer pr-create-complete"], ci_gate_active=True)
    assert not store.permits("t1", ["agentic-kit release-publish"], ci_gate_active=True)
    assert not store.permits("t1", ["agentic-kit transfer pr-create-complete", "agentic-kit workspace upgrade"],
                             ci_gate_active=True)
    store.consume("t1", "sha-a", ["agentic-kit transfer pr-create-complete"], step=1586, now=5.0)
    assert store.permits("t1", ["agentic-kit transfer pr-closeout-complete"], ci_gate_active=True)
    assert store.effects_log("t1") == [{"at": 5.0, "step": 1586, "command_sha256": "sha-a",
                                        "commands": ["agentic-kit transfer pr-create-complete"]}]
    assert store.effects_log("other") == []
    with pytest.raises(ValueError):
        store.pre_approve(task_id="t2", label="x", scope=())


def test_a_normal_approval_keeps_its_unscoped_first_order(tmp_path):
    store = HumanDecisionStore(tmp_path)
    store.record(mission_id="m0", task_id="t", decision="APPROVE", question="q")
    store.grant_for_mission("t", "m1", mission_ended=False)
    assert store.permits("t", ["agentic-kit workspace upgrade"], ci_gate_active=False)


# --- local verifiers ------------------------------------------------------------------------

def test_work_started_verifier(repo):
    ok, finding = sv.verify(repo, {"verifier": "work-started", "params": {"branch": "feat/demo"}})
    assert not ok and "current branch is main" in finding
    git(repo, "switch", "-q", "-c", "feat/demo")
    assert sv.verify(repo, {"verifier": "work-started", "params": {"branch": "feat/demo"}})[0]
    (repo / "x.txt").write_text("x\n")
    assert "not clean" in sv.verify(repo, {"verifier": "work-started", "params": {"branch": "feat/demo"}})[1]
    commit(repo, "x.txt", "x\n")
    git(repo, "switch", "-q", "main")
    commit(repo, "y.txt", "y\n")
    git(repo, "update-ref", "refs/remotes/origin/main", "main")
    git(repo, "switch", "-q", "feat/demo")
    assert "does not contain" in sv.verify(repo, {"verifier": "work-started", "params": {"branch": "feat/demo"}})[1]


def test_recovered_verifier_reads_the_lagebericht():
    def fake(state):
        return lambda _root: SimpleNamespace(state=state, summary="s")
    assert sv.verify(Path("."), {"verifier": "recovered"}, lagebericht=fake(rs.BEREIT))[0]
    assert sv.verify(Path("."), {"verifier": "recovered"}, lagebericht=fake(rs.IN_ARBEIT))[0]
    assert not sv.verify(Path("."), {"verifier": "recovered"}, lagebericht=fake(rs.STOERUNG))[0]
    assert "unknown" in sv.verify(Path("."), {"verifier": "nope"})[1]


def test_contract_of_reads_the_durable_scope(tmp_path):
    contract = {"kind": sv.KIND, "verifier": "recovered", "params": {}}
    store = SimpleNamespace(runtime_contract=lambda _t: {"scope_json": json.dumps({"completion_contract": contract})})
    assert sv.contract_of(store, "t") == contract
    other = SimpleNamespace(runtime_contract=lambda _t: {"scope_json": json.dumps(
        {"completion_contract": {"kind": "verified-successor-handoff-v1"}})})
    assert sv.contract_of(other, "t") is None
    assert sv.VerifierChecks(tmp_path).bump("t") == 1 and sv.VerifierChecks(tmp_path).bump("t") == 2


def test_bridge_checks_the_verifier_before_accepting_done():
    source = (ROOT / "src/agp_cockpit/core/bridge_server.py").read_text(encoding="utf-8")
    hook = source.index("AGP_STANDARD_VERIFIER_V1 (plan P5)")
    assert source.index("AGP_CI_GREEN_COMPLETION_V1: once the task pushed") < hook
    assert hook < source.index("_approval_grant(runtime_root, engine)  # expires an unused approval")
    assert 'verified=authority in {"ci-verified", "verifier-checked"}' in source
    assert "step=outcome.run.step" in source


# --- command contract fixes ---------------------------------------------------------------------

LIVE_1568_BUNDLE = '''
import sys
STEP = 1568
def main():
    if "--self-test" in sys.argv:
        return 0
    kit = ["agentic-kit", "work", "recover", "--json"]
    bundle = {"authority": {"allowed_effects": ["E2"], "allowed_tools": ["agentic-kit", "git"]}}
'''


def test_a_tool_list_is_not_an_invocation():
    catalog = KitCommandCatalog.load(ROOT)
    violations = command_catalog_violations(LIVE_1568_BUNDLE, catalog)
    assert not any("agentic-kit git" in v for v in violations)


def test_force_is_never_allowed_on_publishing_commands():
    order = 'argv = ["agentic-kit", "transfer", "push-current", "--force-with-lease"]\n'
    assert force_violations(order) and "AGP_NO_FORCE_V1" in force_violations(order)[0]
    assert force_violations('argv = ["agentic-kit", "artifact-gc", "--force"]\n') == []


# --- panel -----------------------------------------------------------------------------------------

@pytest.fixture
def panel(monkeypatch, tmp_path, repo):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    from agp_cockpit.core import build_freshness
    from agp_cockpit.core.task_contract import LocalTaskContract
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
    monkeypatch.setattr(build_freshness, "start_block_reason", lambda _root: None)
    monkeypatch.setattr(m, "require_allowed_active_chat", lambda: SimpleNamespace(url="https://chatgpt.com/c/x"))
    created = []
    monkeypatch.setattr(m, "create_live_full_auto", lambda **kw: created.append(kw) or {"mission": {"mission_id": "m-1"}})
    monkeypatch.setattr(m, "request_task_start", lambda *a, **kw: None)
    contract = LocalTaskContract(repository_root=repo, allowed_effects=frozenset({"E0", "E1", "E2"}),
                                 allowed_tools=frozenset({"git", "agentic-kit"}), allow_network=False)
    answers = {"confirm": True, "inputs": {"kind": "feat", "name": "demo"}}
    widget = m.StandardTasksPanel(root, repository_root=repo, local_contract=contract,
                                  runtime_root=tmp_path / "rt",
                                  confirm=lambda _t: answers["confirm"], ask_inputs=lambda _t: answers["inputs"])
    monkeypatch.setattr(widget.api, "start_task_from_contract", lambda prepared: {"state": "WAITING_FOR_REMOTE"})
    monkeypatch.setattr(widget, "refresh_lage", lambda: None)
    monkeypatch.setattr(widget, "_track", lambda _mission: None)
    yield root, widget, created, answers, repo, tmp_path / "rt"
    root.destroy()


def _offered(*keys):
    return rs.RepoState(state=rs.IN_ARBEIT, summary="s", recommended=keys[0], offered=keys)


def test_finish_asks_then_approves_its_scope_and_arms_the_ci_gate(panel):
    _root, widget, created, answers, repo, runtime = panel
    git(repo, "switch", "-q", "-c", "feat/x")
    commit(repo, "w.txt", "w\n")
    widget.apply_state(_offered(rs.ABSCHLIESSEN))
    answers["confirm"] = False
    widget.run_verb(VERBS[rs.ABSCHLIESSEN])
    assert created == [] and "nicht gestartet" in widget.status_var.get()
    answers["confirm"] = True
    widget.run_verb(VERBS[rs.ABSCHLIESSEN])
    assert created and created[0]["title"] == "Standard · Abschließen"
    record = json.loads((runtime / "human-decision.json").read_text())
    assert record["mission_id"].startswith("pre-approval:") and record["grant"]["scope"]
    gate = json.loads((runtime / "ci-gate.json").read_text())
    assert gate[record["task_id"]]["required"] and gate[record["task_id"]]["merge_expected"]
    assert widget.effects_text() == "Freigegebene Wirkungen (Start-Klick): noch keine ausgeführt."


def test_finish_from_main_is_blocked_before_anything_is_recorded(panel):
    _root, widget, created, _answers, _repo, runtime = panel
    widget.apply_state(_offered(rs.ABSCHLIESSEN))
    widget.run_verb(VERBS[rs.ABSCHLIESSEN])
    assert created == [] and "nie von main" in widget.status_var.get()
    assert not (runtime / "human-decision.json").exists()


def test_work_start_uses_the_dialog_inputs(panel):
    _root, widget, created, answers, _repo, _runtime = panel
    widget.apply_state(rs.RepoState(state=rs.BEREIT, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                                    offered=(rs.ARBEIT_BEGINNEN,)))
    answers["inputs"] = None
    widget.run_verb(VERBS[rs.ARBEIT_BEGINNEN])
    assert created == [] and "abgebrochen" in widget.status_var.get()
    answers["inputs"] = {"kind": "feat", "name": "demo"}
    widget.run_verb(VERBS[rs.ARBEIT_BEGINNEN])
    assert created and "feat/demo" in created[0]["mission_text"]


def test_running_task_blocks_every_start(panel, monkeypatch):
    _root, widget, created, _answers, _repo, _runtime = panel
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": {"state": "RUNNING"}})
    assert widget.start_standard_task(BY_KEY["recover"]) is False
    assert "R5" in widget.status_var.get() and created == []


def test_interrupted_finish_offers_recover(panel, monkeypatch):
    _root, widget, _created, _answers, _repo, _runtime = panel
    from agp_cockpit.core.standard_task_progress import StandardTaskProgress
    from agp_cockpit.ui import standard_tasks_panel as m
    widget._tracked_task = BY_KEY["finish"]
    widget._tracked_task_id = "t"
    widget._tracked_mission_id = "m"
    monkeypatch.setattr(m, "describe_standard_task_progress",
                        lambda **_kw: StandardTaskProgress("Gestoppt", True, "STOPPED"))
    monkeypatch.setattr(widget.api, "status", dict)
    state = rs.RepoState(state=rs.IN_ARBEIT, summary="s", recommended=rs.ABSCHLIESSEN,
                         offered=(rs.ABSCHLIESSEN, rs.CHAT_WECHSELN))
    assert not availability(VERBS[rs.WIEDERHERSTELLEN], state)[0]
    widget.refresh_progress()
    assert widget.recover_offered and "Wiederherstellen" in widget.status_var.get()
    widget.apply_state(state)
    assert str(widget.verb_buttons[rs.WIEDERHERSTELLEN].cget("state")) == "normal"
    assert widget.verb_badges[rs.WIEDERHERSTELLEN].cget("text").startswith("★ empfohlen")


def test_done_finish_recommends_chat_switch(panel, monkeypatch):
    _root, widget, _created, _answers, _repo, _runtime = panel
    from agp_cockpit.core.standard_task_progress import StandardTaskProgress
    from agp_cockpit.ui import standard_tasks_panel as m
    widget._tracked_task = BY_KEY["finish"]
    widget._tracked_task_id = "t"
    widget._tracked_mission_id = "m"
    monkeypatch.setattr(m, "describe_standard_task_progress",
                        lambda **_kw: StandardTaskProgress("Fertig ✓", True, "DONE"))
    monkeypatch.setattr(widget.api, "status", dict)
    widget.refresh_progress()
    assert "Als Nächstes empfohlen: „Chat wechseln“" in widget.status_var.get()
    assert not widget.recover_offered


def test_release_policy_allows_the_private_tag_push():
    policy = json.loads((ROOT / "docs/planning/release_policy.json").read_text(encoding="utf-8"))
    assert policy["publication"] == "none" and policy["tag_push"]["allowed"] is True
