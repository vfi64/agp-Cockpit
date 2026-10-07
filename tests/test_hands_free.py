"""Package „Ohne Handarbeit“ (owner 2026-10-07): branch switch through the Kit, „Abschließen“
after a ticked „Arbeiten“ task, and an approval scope the bridge enforces."""
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest

from agp_cockpit.core import branch_switch
from agp_cockpit.core.human_decision import (
    PUSH_PR_SCOPE,
    SCOPES,
    HumanDecisionStore,
    decision_mission_text,
)

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
SIMPLE = (ROOT / "src/agp_cockpit/ui/simple_task_panel.py").read_text(encoding="utf-8")
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, env=ENV)


# --- approval scope (AGP_APPROVAL_SCOPE_CHOICE_V1) ------------------------------------------

def test_a_push_and_pr_approval_never_covers_a_merging_command(tmp_path):
    store = HumanDecisionStore(tmp_path)
    store.record(mission_id="M", task_id="T", decision="APPROVE", question="Push?", scope=SCOPES["push_pr"])
    assert store.permits("T", ["agentic-kit transfer push-current"], ci_gate_active=False)
    assert store.permits("T", list(PUSH_PR_SCOPE), ci_gate_active=False)
    for merging in ("agentic-kit transfer pr-create-complete", "agentic-kit transfer pr-complete",
                    "agentic-kit work finish", "agentic-kit pr merge-if-green"):
        assert not store.permits("T", [merging], ci_gate_active=True), merging
    full = HumanDecisionStore(tmp_path / "full")
    full.record(mission_id="M", task_id="T", decision="APPROVE", question="Push?", scope=SCOPES["full"])
    assert full.permits("T", ["agentic-kit transfer pr-create-complete"], ci_gate_active=False)


def test_the_continuation_names_the_limited_scope():
    text = decision_mission_text(goal_text="G", decision="APPROVE", question="Q?", note="", scope="push_pr")
    assert "NO merge" in text and "agentic-kit transfer pr-create`" in text and "pr-create-complete" in text
    assert "merge with its post-merge" not in text
    assert "merge with its post-merge" in decision_mission_text(goal_text="G", decision="APPROVE",
                                                                question="Q?", note="")


def test_the_decision_endpoint_stores_the_scope_and_refuses_unknown_ones(tmp_path):
    sys.path.insert(0, str(ROOT / "tests"))
    import test_human_decision as h
    gen = h._bridge(tmp_path)
    root, runtime, call = next(gen)
    try:
        first = h.mission(call, runtime)
        asked = call("/v1/file-loop/command", {"filename": "1480_push.py",
                                               "content": h.work_order(["transfer", "push-current"])})
        assert asked["state"] == "NEEDS_HUMAN"
        with pytest.raises(HTTPError):
            call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE", "scope": "alles"})
        record = call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE", "scope": "push_pr"})
        assert record["scope_choice"] == "push_pr"
        assert HumanDecisionStore(runtime).current()["grant"]["scope"] == sorted(PUSH_PR_SCOPE)
    finally:
        gen.close()


def test_the_work_tab_decision_box_offers_the_scope_and_passes_it_on():
    assert 'self.decision_scope_var = tk.StringVar(value="push_pr")' in SIMPLE
    assert "record_decision(mission_id=mission_id, decision=decision, note=note, scope=scope)" in SIMPLE
    assert "scope=scope," in SIMPLE[SIMPLE.index("mission_text=decision_mission_text("):][:400]


# --- branch switch (AGP_BRANCH_SWITCH_V1) ---------------------------------------------------

@pytest.fixture
def repo(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("1\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "branch", "feat/x")
    return tmp_path


def _fake_kit(tmp_path, *, fail=False):
    kit = tmp_path / "fake-kit"
    body = ("import json,subprocess,sys\n"
            "assert sys.argv[1:3]==['transfer','branch-switch'] and sys.argv[4]=='--json'\n"
            + ("print(json.dumps({'result_status':'FAIL','stderr':'kaputt'}));sys.exit(2)\n" if fail else
               "subprocess.run(['git','switch','-q',sys.argv[3]],check=True)\n"
               "print(json.dumps({'result_status':'PASS'}))\n"))
    kit.write_text(f"#!{sys.executable}\n" + body)
    kit.chmod(0o755)
    return kit


def test_branch_switch_runs_the_kit_route_and_verifies_with_git(repo, tmp_path):
    names = [b.name for b in branch_switch.local_branches(repo)]
    assert set(names) == {"main", "feat/x"}
    assert branch_switch.block_reason(repo, "feat/x", task_running=False) == ""
    ok, message = branch_switch.switch(repo, _fake_kit(tmp_path), "feat/x", env=ENV)
    assert ok and "feat/x" in message
    assert next(b for b in branch_switch.local_branches(repo) if b.current).name == "feat/x"
    failed, detail = branch_switch.switch(repo, _fake_kit(tmp_path / "f" if (tmp_path / "f").mkdir() is None
                                                         else tmp_path, fail=True), "main", env=ENV)
    assert not failed and "kaputt" in detail


def test_branch_switch_refuses_running_tasks_unknown_current_and_dirty(repo):
    assert "R5" in branch_switch.block_reason(repo, "feat/x", task_running=True)
    assert "kein lokaler Branch" in branch_switch.block_reason(repo, "nope", task_running=False)
    assert "schon aktiv" in branch_switch.block_reason(repo, "main", task_running=False)
    (repo / "a.txt").write_text("changed\n")
    assert "nicht committete" in branch_switch.block_reason(repo, "feat/x", task_running=False)


def test_the_header_offers_branch_switch_beside_repo_switch():
    assert 'text="Branch wechseln …", command=self.open_branch_switch' in MAIN
    handler = MAIN[MAIN.index("def open_branch_switch"):MAIN.index("def open_repo_switch")]
    assert "branch_switch.block_reason(" in handler and "self.refresh_build_freshness()" in handler
    assert handler.index("block_reason(") < handler.index("branch_switch.switch(")


# --- auto finish (AGP_AUTO_FINISH_V1) -------------------------------------------------------

class _State:
    def __init__(self, state, recommended=None):
        self.state, self.recommended = state, recommended


def test_a_ticked_work_task_starts_abschliessen_once_the_lage_agrees(monkeypatch, tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    from agp_cockpit.core import repo_state as rs
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
    try:
        panel = m.StandardTasksPanel(root, repository_root=tmp_path, on_open_work=lambda: None)
        started, refreshed = [], []
        # plain instance attributes: a monkeypatch would keep the Tk panel alive until its
        # teardown, and a later collection in a bridge thread aborts Tcl (Tcl_AsyncDelete)
        panel.start_standard_task = lambda task, inputs: started.append(task.key) or True
        panel.refresh_lage = lambda: refreshed.append(1)
        monkeypatch.setattr(m, "availability", lambda verb, state, recover_offered=False: (True, ""))
        panel.request_auto_finish()
        panel._maybe_auto_finish(_State(rs.LAEUFT))        # the ended task still counts: wait
        assert started == [] and panel._auto_finish_pending > 0
        panel._maybe_auto_finish(_State(rs.IN_ARBEIT, rs.ABSCHLIESSEN))
        assert started == ["finish"] and panel._auto_finish_pending == 0
        panel._maybe_auto_finish(_State(rs.IN_ARBEIT, rs.ABSCHLIESSEN))   # only once
        assert started == ["finish"]
        panel.request_auto_finish()
        panel._maybe_auto_finish(_State(rs.BEREIT, rs.ARBEIT_BEGINNEN))     # nothing to publish
        assert started == ["finish"] and "nicht automatisch gestartet" in panel.status_var.get()
    finally:
        root.destroy()
        del panel, root
        import gc
        gc.collect()


def test_the_tick_is_part_of_the_start_and_the_main_window_hands_over():
    assert 'text="danach Push, PR und Merge bei grüner CI"' in SIMPLE
    start = SIMPLE[SIMPLE.index("def start_task("):]
    assert start.index("auto_finish = bool(self.auto_finish_var.get())") < start.index("messagebox.askyesno(")
    assert "Dieser Start ist deine Freigabe dafür." in start
    handover = MAIN[MAIN.index("def _work_task_event"):MAIN.index("def open_branch_switch")]
    assert "if work.auto_finish_armed:" in handover and "panel.request_auto_finish()" in handover
