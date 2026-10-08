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
    assert {t.key for t in standard_tasks()} == {"chat-switch", "finish", "work-start", "recover", "release",
                                                 "maintain"}
    for key in (rs.ABSCHLIESSEN, rs.ARBEIT_BEGINNEN, rs.WIEDERHERSTELLEN, rs.CHAT_WECHSELN, rs.RELEASE,
                rs.PFLEGE):
        verb = VERBS[key]
        assert verb.slice is None and verb.task_key in BY_KEY
    assert VERBS[rs.REPO_UEBERNEHMEN].slice == "P9"


@pytest.mark.parametrize("branch", ["feat/demo", "main"])
def test_new_goal_texts_name_no_kit_command(monkeypatch, branch):
    """The finish prompt depends on the checked-out branch; CI on a push to main
    runs on branch main (live 2026-10-04: main CI red after #190, PR CI green on
    a detached merge ref). Both variants are checked independently of the runner."""
    import agp_cockpit.core.standard_tasks as st
    real = st._git_value
    monkeypatch.setattr(st, "_git_value", lambda root, *args: branch
                        if args == ("branch", "--show-current") else real(root, *args))
    inputs = {"work-start": {"kind": "feat", "name": "demo"}, "release": {"version": "9.9.9"}}
    for key in ("finish", "work-start", "recover", "release"):
        task = BY_KEY[key]
        prompt = task.prompt(ROOT, inputs.get(key))
        for command in ("pr-create", "pr-closeout", "work finish", "remote-work-start", "work recover",
                        "post-merge-complete", "sync-main", "release-publish", "release prepare",
                        "release-prep", "work start"):
            assert command not in prompt, (key, branch, command)
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
                                        "commands": ["agentic-kit transfer pr-create-complete"],
                                        "source": "start"}]
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
    def fake(state, recommended=None, **facts):
        return lambda _root: SimpleNamespace(state=state, summary="s", recommended=recommended,
                                             facts=rs.RepoFacts(root="", branch="feat/x", **facts))
    assert sv.verify(Path("."), {"verifier": "recovered"}, lagebericht=fake(rs.BEREIT))[0]
    assert sv.verify(Path("."), {"verifier": "recovered"}, lagebericht=fake(rs.IN_ARBEIT, own_commits=1))[0]
    assert sv.verify(Path("."), {"verifier": "recovered"}, lagebericht=fake(rs.IN_ARBEIT, changes=("a",)))[0]
    assert not sv.verify(Path("."), {"verifier": "recovered"}, lagebericht=fake(rs.STOERUNG))[0]
    # AGP_GUIDED_RECOVERY_V1 (live 2026-10-06): an empty leftover branch is not recovered;
    # main with only the Kit's follow-up open is.
    leftover = sv.verify(Path("."), {"verifier": "recovered"}, lagebericht=fake(rs.IN_ARBEIT, own_commits=0))
    assert not leftover[0] and "holds no work" in leftover[1]
    assert sv.verify(Path("."), {"verifier": "recovered"},
                     lagebericht=fake(rs.STOERUNG, recommended=rs.ABSCHLIESSEN))[0]
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
    monkeypatch.setattr(build_freshness, "start_block_reason", lambda _root, **_kw: None)
    monkeypatch.setattr(build_freshness, "stale_block_reason", lambda _root, **_kw: "")
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
    # Collect the panel's reference cycles here, in the main thread: a later
    # collection in a server thread of another test aborts Tcl
    # ("Tcl_AsyncDelete: async handler deleted by the wrong thread").
    del widget, root
    import gc
    gc.collect()


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
    widget.refresh_progress()            # no effect executed yet: nothing to recover
    assert not widget.recover_offered and "erneut starten" in widget.status_var.get()
    store = HumanDecisionStore(widget.runtime_root())
    store.pre_approve(task_id="t", label="Abschließen", scope=BY_KEY["finish"].approved_scope)
    store.grant_for_mission("t", "m", mission_ended=False)
    store.consume("t", "sha", ["agentic-kit transfer pr-create-complete"], step=1)
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
    widget.recover_offered = True        # AGP_RECOVER_OFFER_CLEARS_V1: a DONE clears an old R6 offer
    widget.refresh_progress()
    assert "Als Nächstes empfohlen" not in widget.status_var.get()
    assert widget.follow_up_key is None
    assert not widget.recover_offered


def test_recover_offer_clears_once_main_is_ready(panel):
    """AGP_RECOVER_OFFER_CLEARS_V1 (live 2026-10-03): BEREIT recommended
    „Wiederherstellen (nach dem letzten Task)“ after an interrupted Abschließen."""
    _root, widget, _created, _answers, _repo, _runtime = panel
    widget.recover_offered = True
    widget.apply_state(rs.RepoState(state=rs.BEREIT, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                                    offered=rs.OFFERED[rs.BEREIT]))
    assert not widget.recover_offered
    assert widget.verb_badges[rs.ARBEIT_BEGINNEN].cget("text").startswith("★ empfohlen")
    assert str(widget.verb_buttons[rs.WIEDERHERSTELLEN].cget("state")) == "disabled"


def test_release_policy_allows_the_private_tag_push():
    policy = json.loads((ROOT / "docs/planning/release_policy.json").read_text(encoding="utf-8"))
    # P11c (2026-10-05) switched on 2026-10-08 with Kit 1.0.20.
    assert policy["publication"] == "github" and policy["tag_push"]["allowed"] is True


# --- T5b (live 2026-10-02) ----------------------------------------------------------------------

def test_follow_up_is_the_only_recommendation_after_a_finished_task(panel, monkeypatch):
    _root, widget, _created, _answers, _repo, _runtime = panel
    import dataclasses

    from agp_cockpit.core.standard_task_progress import StandardTaskProgress
    from agp_cockpit.ui import standard_tasks_panel as m
    # The mechanism stays generic; no shipped task uses it (AGP_NO_CHAT_SWITCH_FOLLOW_UP_V1).
    widget._tracked_task = dataclasses.replace(BY_KEY["finish"], follow_up="Chat wechseln")
    widget._tracked_task_id = "t"
    widget._tracked_mission_id = "m"
    monkeypatch.setattr(m, "describe_standard_task_progress",
                        lambda **_kw: StandardTaskProgress("Fertig ✓", True, "DONE"))
    monkeypatch.setattr(widget.api, "status", dict)
    widget.refresh_progress()
    ready = rs.RepoState(state=rs.BEREIT, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                         offered=(rs.ARBEIT_BEGINNEN, rs.CHAT_WECHSELN))
    widget.apply_state(ready)
    assert widget.verb_badges[rs.CHAT_WECHSELN].cget("text").startswith("★ empfohlen")
    assert not widget.verb_badges[rs.ARBEIT_BEGINNEN].cget("text").startswith("★")
    assert widget.detail_var.get().startswith("Empfohlen: Chat wechseln")
    widget.follow_up_key = None
    widget.apply_state(ready)
    assert widget.verb_badges[rs.ARBEIT_BEGINNEN].cget("text").startswith("★ empfohlen")


def test_verified_done_shows_the_cockpit_verdict():
    from agp_cockpit.core.standard_task_progress import describe_standard_task_progress
    mission = {"mission_id": "m", "state": "DONE", "turn_count": 1, "step_count": 1,
               "last_summary": "Fertig (Remote): CI grün geprüft (PR #152 gemergt, main 0b07a8baeba0) · Step 1588"}
    progress = describe_standard_task_progress(mission_id="m", task_status={"state": "VERIFIED_COMPLETE"},
                                               bridge_status={"mission": mission})
    assert progress.text.startswith("Fertig ✓ — CI grün geprüft (PR #152") and progress.outcome == "DONE"


def test_send_control_waits_for_an_uploading_attachment():
    background = (ROOT / "chrome_extension/background.js").read_text(encoding="utf-8")
    assert "AGP_SEND_READY_AFTER_UPLOAD_V1" in background and "readiness_wait_ms:30000" in background


def test_digest_is_remembered_only_after_the_send():
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    block = content[content.index("const digestPath = String(status.kit_command_digest_path"):]
    block = block[:block.index("} catch (err) {")]
    send = block.index("await sendPrompt(bootstrapText);")
    assert block.index("await rememberDigest(manifestSha, digestAttached)") > send
    assert block.count("rememberDigest(") == 1


def test_composer_is_cleaned_before_every_cockpit_send():
    background = (ROOT / "chrome_extension/background.js").read_text(encoding="utf-8")
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    assert "AGP_COMPOSER_CLEAN_START_V1" in background and "AGP_K07_CLEAN_COMPOSER" in background
    native = background[background.index("async function agpNativeTransportV1("):]
    assert native.index("agpComposerCleanup(") < native.index('"Input.insertText"')
    assert "{files:false}" in native[:native.index('"Input.insertText"')]
    continuation = background[background.index("async function agpSubmitFileLoopContinuation("):]
    assert continuation.index("agpCleanComposer(tabId)") < continuation.index("attachResultFiles(chrome")
    start = content[content.index("const digestPath = String(status.kit_command_digest_path"):]
    assert start.index('type:"AGP_K07_CLEAN_COMPOSER"') < start.index("AGP_K07_ATTACH_FILES")
    assert (ROOT / "tests/e2e/test_composer_clean.spec.js").is_file()


def test_no_shipped_task_recommends_chat_switch():
    """AGP_NO_CHAT_SWITCH_FOLLOW_UP_V1 (owner 2026-10-02): after Abschließen the
    star follows the repository state (BEREIT → Arbeit beginnen)."""
    assert [t.key for t in BY_KEY.values() if t.follow_up] == []



# --- AGP_KIT_GATED_VERBS_V1 (owner 2026-10-02) ------------------------------------------------

def test_release_is_a_standard_task_now():
    """KIT-GF-032 verified fixed with Kit 1.0.15; P11 built on Kit 1.0.16 (KIT-GF-037/038)."""
    from agp_cockpit.core.verbs import availability
    assert VERBS[rs.RELEASE].kit_gate is None and VERBS[rs.RELEASE].task_key == "release"
    assert availability(VERBS[rs.RELEASE], None) == (False, "Lagebericht läuft noch.")


def test_recover_uses_kit_routes_only():
    """P8 full (owner 2026-10-03): Kit routes only, including the rescue of main."""
    prompt = BY_KEY["recover"].prompt(Path("/r"))
    assert "KIT-GF-033" in prompt and "Never run raw git" in prompt
    assert "dry run first" in prompt and "only behind origin/main" in prompt
    assert "KIT-GF-033" in VERBS[rs.WIEDERHERSTELLEN].tooltip()


def test_cockpit_runs_no_repository_changing_git():
    """The Cockpit steers; repository changes run only inside work orders through
    the Kit. Allowed exception: the Kit findings cache clone (not the repository)."""
    import re
    mutating = re.compile(r'"(reset|checkout|switch|clean|commit|push|merge|rebase|restore|stash|pull|'
                          r'cherry-pick|tag)"')
    allowed = {"kit_findings_sync.py", "kit_command_catalog.py"}
    offenders = [f"{path.name}:{n}" for path in (ROOT / "src").rglob("*.py") if path.name not in allowed
                 for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
                 if mutating.search(line)]
    assert offenders == []


# --- AGP_CONVERSATION_BINDING_V1 (P4) ---------------------------------------------------------

def test_chat_bound_to_another_repository_blocks_before_anything_is_recorded(panel):
    _root, widget, created, _answers, _repo, runtime = panel
    from agp_cockpit.core.conversation_binding import ConversationBindingStore
    ConversationBindingStore(runtime).bind("https://chatgpt.com/c/x", Path("/elsewhere/repo"))
    widget.apply_state(rs.RepoState(state=rs.BEREIT, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                                    offered=(rs.ARBEIT_BEGINNEN,)))
    widget.run_verb(VERBS[rs.ARBEIT_BEGINNEN])
    assert created == [] and "neuen Chat" in widget.status_var.get()
    assert not (runtime / "human-decision.json").exists()


def test_first_start_binds_the_chat_to_the_repository(panel):
    _root, widget, created, _answers, repo, runtime = panel
    from agp_cockpit.core.conversation_binding import ConversationBindingStore
    widget.apply_state(rs.RepoState(state=rs.BEREIT, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                                    offered=(rs.ARBEIT_BEGINNEN,)))
    widget.run_verb(VERBS[rs.ARBEIT_BEGINNEN])
    assert created and ConversationBindingStore(runtime).owner("https://chatgpt.com/c/x") == str(repo.resolve())


# --- AGP_STANDARD_TASK_DECISION_V1 (P8 live test 2026-10-03) ---------------------------------------

def _needs_human(monkeypatch, widget, summary="Rescue dry-run passed; approve the signed execute?"):
    from agp_cockpit.core.standard_task_progress import StandardTaskProgress
    from agp_cockpit.ui import standard_tasks_panel as m
    widget._tracked_task = BY_KEY["recover"]
    widget._tracked_task_id = "t"
    widget._tracked_mission_id = "m"
    monkeypatch.setattr(m, "describe_standard_task_progress",
                        lambda **_kw: StandardTaskProgress("Mensch muss eingreifen", True, "HUMAN_REQUIRED"))
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": {
        "mission_id": "m", "state": "NEEDS_HUMAN", "title": "Standard · Wiederherstellen",
        "last_summary": summary}})
    monkeypatch.setattr(widget.api, "status", dict)
    decisions = []
    monkeypatch.setattr(m, "record_decision", lambda **kw: decisions.append(kw) or {})
    return decisions


def test_needs_human_of_a_standard_task_is_answered_in_the_panel(panel, monkeypatch):
    _root, widget, created, _answers, _repo, _runtime = panel
    decisions = _needs_human(monkeypatch, widget)
    widget.refresh_progress()
    assert widget.decision_frame.winfo_manager() == "grid"
    assert "signed execute" in widget.decision_question_var.get()
    widget.decision_note.insert("1.0", "ja, retten")
    assert widget.decide("APPROVE")
    assert decisions == [{"mission_id": "m", "decision": "APPROVE", "note": "ja, retten"}]
    continuation = created[-1]
    assert continuation["title"] == "Standard · Wiederherstellen · Entscheidung"
    assert "APPROVED" in continuation["mission_text"] and "signed execute" in continuation["mission_text"]
    assert widget.decision_frame.winfo_manager() == ""
    assert "läuft im selben Chat weiter" in widget.status_var.get()


def test_rejecting_ends_the_task_without_a_remote_turn(panel, monkeypatch):
    """AGP_REJECT_ENDS_TASK_V1 (live 2026-10-04, steps 1679/1680): a rejection used
    to start a continuation whose only possible answer was another question."""
    _root, widget, created, _answers, _repo, _runtime = panel
    decisions = _needs_human(monkeypatch, widget)
    widget.refresh_progress()
    before = len(created)
    widget.decision_note.insert("1.0", "nein")
    assert widget.decide("REJECT")
    assert decisions == [{"mission_id": "m", "decision": "REJECT", "note": "nein"}]
    assert len(created) == before   # no continuation mission
    assert widget.decision_frame.winfo_manager() == ""
    assert "Abgelehnt — Wiederherstellen ist beendet" in widget.status_var.get()
    assert widget.recover_offered is False


def test_rejecting_after_executed_effects_offers_recover(panel, monkeypatch):
    _root, widget, _created, _answers, _repo, _runtime = panel
    _needs_human(monkeypatch, widget)
    widget.refresh_progress()
    import dataclasses
    widget._tracked_task = dataclasses.replace(widget._tracked_task, offers_recover_on_interrupt=True)
    monkeypatch.setattr(widget, "_effects_executed", lambda: True)
    assert widget.decide("REJECT")
    assert widget.recover_offered is True
    assert "„Wiederherstellen“ ist freigeschaltet" in widget.status_var.get()


def test_pending_decision_is_adopted_after_a_restart(panel, monkeypatch):
    _root, widget, _created, _answers, _repo, _runtime = panel
    from agp_cockpit.core import start_request
    from agp_cockpit.ui import standard_tasks_panel as m
    assert m.pending_standard_decision({"state": "NEEDS_HUMAN", "title": "Task · x"}, widget.tasks)[0] is None
    assert m.pending_standard_decision({"state": "DONE", "title": "Standard · Wiederherstellen"},
                                       widget.tasks)[0] is None
    task, mid = m.pending_standard_decision(
        {"state": "NEEDS_HUMAN", "title": "Standard · Wiederherstellen · Entscheidung", "mission_id": "m2"},
        widget.tasks)
    assert task is BY_KEY["recover"] and mid == "m2"
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": {
        "mission_id": "m2", "state": "NEEDS_HUMAN", "title": "Standard · Wiederherstellen",
        "last_summary": "approve?"}})
    monkeypatch.setattr(start_request, "resolve_task_binding", lambda _root, _mid: {"task_id": "t2"})
    widget.adopt_pending_decision()
    assert widget._tracked_task_id == "t2" and widget._tracked_mission_id == "m2"
    assert widget.decision_frame.winfo_manager() == "grid" and widget.decision_question_var.get() == "approve?"


def test_assistant_timeout_after_a_merged_finish_is_confirmed_locally(panel, monkeypatch):
    """AGP_LATE_COMPLETION_CHECK_V1 (live 2026-10-04, step 1689): PR #194 was merged
    and main green, but the remote answer came after the deadline; the panel offered
    „Wiederherstellen“. Now the Lagebericht confirms the merged work."""
    from agp_cockpit.core.standard_task_progress import StandardTaskProgress
    from agp_cockpit.ui import standard_tasks_panel as m
    _root, widget, _created, _answers, repo, _runtime = panel
    git(repo, "switch", "-q", "-c", "chore/kit")
    commit(repo, "kit.txt", "1.0.16\n")
    widget._tracked_task = BY_KEY["finish"]
    widget._tracked_task_id = "t"
    widget._tracked_mission_id = "m"
    widget._tracked_head = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-q", "main")
    commit(repo, "kit.txt", "1.0.16\n")              # the squash merge
    git(repo, "update-ref", "refs/remotes/origin/main", "main")
    monkeypatch.setattr(m, "describe_standard_task_progress",
                        lambda **_kw: StandardTaskProgress("Gestoppt — Mission: STOPPED", True, "STOPPED"))
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": {
        "mission_id": "m", "state": "STOPPED", "title": "Standard · Abschließen",
        "last_summary": "K07_ASSISTANT_RESPONSE_TIMEOUT after 181s (180s without visible activity)"}})
    monkeypatch.setattr(widget.api, "status", dict)
    monkeypatch.setattr(widget, "_effects_executed", lambda: True)
    widget.refresh_progress()
    assert widget.recover_offered is True          # R6 until the repository says otherwise
    assert "prüft den Stand lokal" in widget.status_var.get()
    facts = rs.RepoFacts(root=str(repo), post_merge="PASS")
    widget._poll_lage([rs.RepoState(state=rs.BEREIT, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                                    offered=(rs.ARBEIT_BEGINNEN,), facts=facts)])
    assert widget.recover_offered is False
    assert "vom Cockpit geprüft nach der Zeitüberschreitung" in widget.status_var.get()
    assert "ist freigeschaltet und empfohlen" not in widget.status_var.get()   # AGP_RECOVER_HINT_FOLLOWS_OFFER_V1
    assert widget._late_check is False


def test_release_asks_its_version_then_approves_only_the_branch_lifecycle(panel):
    """P11 (owner 2026-10-04): the start click approves branch and merge; the tag
    push is outside the scope and always asks."""
    _root, widget, created, answers, repo, runtime = panel
    (repo / ".agentic").mkdir()
    (repo / ".agentic/config.yaml").write_text("publication: none\n")
    git(repo, "add", ".agentic/config.yaml")
    commit(repo, "pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n')
    git(repo, "update-ref", "refs/remotes/origin/main", "main")
    widget.apply_state(_offered(rs.RELEASE))
    answers["inputs"] = {"version": "0.1.1"}
    widget.run_verb(VERBS[rs.RELEASE])
    assert created and created[0]["title"] == "Standard · Release"
    assert "RELEASE 0.1.1" in created[0]["mission_text"]
    record = json.loads((runtime / "human-decision.json").read_text())
    scope = set(record["grant"]["scope"])
    assert "agentic-kit transfer pr-create-complete" in scope
    assert "agentic-kit release-publish" not in scope
    gate = json.loads((runtime / "ci-gate.json").read_text())
    assert gate[record["task_id"]]["merge_expected"]


def test_ampel_follows_state_decision_and_outcome(panel, monkeypatch):
    """AGP_AMPEL_V1: one light in the Lage frame, recomputed on every change."""
    _root, widget, _created, _answers, _repo, _runtime = panel
    from agp_cockpit.core import ampel as a
    from agp_cockpit.core.standard_task_progress import StandardTaskProgress
    from agp_cockpit.ui import standard_tasks_panel as m
    ready = rs.RepoState(state=rs.BEREIT, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                         offered=rs.OFFERED[rs.BEREIT])
    widget.apply_state(ready)
    assert widget.ampel_state.color == a.GRUEN and widget.ampel_var.get().startswith("Grün")
    assert str(widget.ampel_dot.cget("foreground")) == a.COLORS[a.GRUEN]
    widget._show_decision("m", "Tag v1 setzen?")
    assert widget.ampel_state.color == a.GELB
    widget._hide_decision()
    working = rs.RepoState(state=rs.IN_ARBEIT, summary="s", recommended=rs.ABSCHLIESSEN,
                           offered=rs.OFFERED[rs.IN_ARBEIT], facts=rs.RepoFacts(root="", branch="feat/x"))
    widget.apply_state(working)
    widget._tracked_task = BY_KEY["finish"]
    widget._tracked_task_id = "t"
    widget._tracked_mission_id = "m"
    monkeypatch.setattr(m, "describe_standard_task_progress",
                        lambda **_kw: StandardTaskProgress("Mensch muss eingreifen", True, "HUMAN_REQUIRED", "x"))
    monkeypatch.setattr(widget.api, "status", dict)
    widget.refresh_progress()
    assert widget.ampel_state.color == a.ROT and widget._status_detail == "x"


def test_unklar_state_does_not_break_the_panel(panel):
    """AGP_UNKLAR_HINT_V1: UNKLAR recommends the Lagebericht, which has no button."""
    _root, widget, *_rest = panel
    unclear = rs.classify(rs.RepoFacts(root="", is_git=True, branch="main", head="a", origin_main=None,
                                       kit_version="1.0.18", workspace=True, gh_ok=True))
    assert unclear.state == rs.UNKLAR and unclear.recommended == rs.LAGEBERICHT
    widget.apply_state(unclear)
    assert "Aktualisieren" in widget.detail_var.get()
    assert widget.ampel_var.get().startswith("Rot")


def test_guidance_and_details_in_the_panel(panel):
    """AGP_GUIDED_RECOVERY_V1 / AGP_COMPACT_LAGE_V1."""
    _root, widget, *_rest = panel
    s = rs.RepoState(state=rs.STOERUNG, summary="s", recommended=rs.ABSCHLIESSEN,
                     offered=rs.OFFERED[rs.STOERUNG] + (rs.ABSCHLIESSEN,),
                     facts=rs.RepoFacts(root="", is_git=True, branch="main", head="a", origin_main="a",
                                        post_merge="NOT_PASS", followup_pr=243, followup_ci="RUNNER"))
    widget.apply_state(s)
    assert widget.guidance_var.get().startswith("Lösungsweg:\n1. Auf GitHub PR #243")
    assert widget.guidance_label.winfo_manager() == "grid"
    assert "Folge-PR #243" in widget.facts_var.get()
    assert widget.lage_label.winfo_manager() == ""
    widget.toggle_details()
    assert widget.lage_label.winfo_manager() == "grid" and widget.details_button.cget("text") == "Details ▾"
    widget.apply_state(rs.RepoState(state=rs.BEREIT, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                                    offered=rs.OFFERED[rs.BEREIT]))
    assert widget.guidance_var.get() == "" and widget.guidance_label.winfo_manager() == ""
