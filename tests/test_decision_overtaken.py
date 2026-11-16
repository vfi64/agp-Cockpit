"""AGP_DECISION_OVERTAKEN_V1 (workflow-friction plan C7, section 2.4): an „Abschließen“
stopped with a question (NEEDS_HUMAN), the owner published the work outside the mission,
and the question box and the yellow light stayed. The question now closes once the Lage
shows the work published — with the same criterion as AGP_LATE_COMPLETION_CHECK_V1 — also
for a question adopted after a restart."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.human_decision import HumanDecisionStore
from agp_cockpit.core.standard_task_progress import (
    decision_overtaken,
    finish_merged,
    late_completion_verdict,
)
from agp_cockpit.core.standard_tasks import BY_KEY
from agp_cockpit.core.task_start_head import KEEP, TaskStartHeadStore


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


def commit(repo: Path, name: str, text: str) -> str:
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", name)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    """main with origin/main; a work branch feat/x with one commit (the finish start)."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    commit(root, ".gitignore", ".local/\n")
    commit(root, "base.txt", "a\n")
    git(root, "update-ref", "refs/remotes/origin/main", "main")
    git(root, "switch", "-q", "-c", "feat/x")
    commit(root, "work.txt", "w\n")
    return root


def publish_outside(repo: Path) -> None:
    """The owner merged the work by hand (squash) and synchronized main."""
    git(repo, "switch", "-q", "main")
    commit(repo, "work.txt", "w\n")
    git(repo, "update-ref", "refs/remotes/origin/main", "main")
    git(repo, "branch", "-q", "-D", "feat/x")


def lage(name=rs.BEREIT, post_merge="PASS"):
    return rs.RepoState(state=name, summary="s", recommended=rs.ARBEIT_BEGINNEN,
                        offered=(rs.ARBEIT_BEGINNEN,), facts=rs.RepoFacts(root="", post_merge=post_merge))


# --- core: one criterion ------------------------------------------------------------

def test_overtaken_shares_the_late_completion_criterion(repo):
    start = git(repo, "rev-parse", "HEAD")
    assert decision_overtaken("finish", start, lage(), repo) == (False, "")
    assert finish_merged(start, lage(), repo)[1] == [f"Stand {start[:12]} has changes not in origin/main"]
    publish_outside(repo)
    overtaken, text = decision_overtaken("finish", start, lage(), repo)
    assert overtaken and late_completion_verdict("finish", start, lage(), repo)[0]
    assert text.startswith("Rückfrage überholt") and start[:12] in text and "nichts wurde ausgeführt" in text
    assert finish_merged(start, lage(), repo) == (True, [])


def test_overtaken_needs_bereit_green_post_merge_and_a_start_commit(repo):
    start = git(repo, "rev-parse", "HEAD")
    publish_outside(repo)
    assert not decision_overtaken("finish", start, lage(post_merge="NOT_PASS"), repo)[0]
    assert not decision_overtaken("finish", start, lage(rs.STOERUNG), repo)[0]
    assert not decision_overtaken("finish", "", lage(), repo)[0]          # safe failure
    assert not decision_overtaken("finish", start, None, repo)[0]
    assert not decision_overtaken("release", start, lage(), repo)[0]      # other tasks keep asking


def test_late_completion_texts_are_unchanged(repo):
    start = git(repo, "rev-parse", "HEAD")
    done, text = late_completion_verdict("finish", start, lage(post_merge="NOT_PASS"), repo)
    assert not done and text == ("Lokale Prüfung nach der Zeitüberschreitung: nicht abgeschlossen ("
                                 f"post-merge-check NOT_PASS; Stand {start[:12]} has changes not in origin/main). "
                                 "Bitte den Stand prüfen.")
    done, text = late_completion_verdict("recover", start, lage(), repo)
    assert not done and text == "Lokale Prüfung nach der Zeitüberschreitung: Lage BEREIT: s. Bitte den Stand prüfen."


# --- core: durable start commit -----------------------------------------------------

def test_start_head_store_survives_and_is_bounded(tmp_path):
    store = TaskStartHeadStore(tmp_path / "rt")
    assert store.head("t1") == ""
    store.record("t1", task_key="finish", head="abc")
    store.record("", task_key="finish", head="x")
    store.record("t2", task_key="finish", head="")
    assert TaskStartHeadStore(tmp_path / "rt").head("t1", task_key="finish") == "abc"
    assert store.head("t1", task_key="release") == ""
    assert set(json.loads(store.path.read_text())) == {"t1"}
    for number in range(KEEP + 5):
        store.record(f"n{number}", task_key="finish", head=f"h{number}")
    data = json.loads(store.path.read_text())
    assert len(data) == KEEP and "t1" not in data and data[f"n{KEEP + 4}"]["head"] == f"h{KEEP + 4}"
    store.path.write_text("{kaputt")
    assert store.head("n24") == ""


# --- panel ----------------------------------------------------------------------------

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
    monkeypatch.setattr(m, "create_live_full_auto", lambda **kw: {"mission": {"mission_id": "m-1"}})
    monkeypatch.setattr(m, "request_task_start", lambda *a, **kw: None)
    contract = LocalTaskContract(repository_root=repo, allowed_effects=frozenset({"E0", "E1", "E2"}),
                                 allowed_tools=frozenset({"git", "agentic-kit"}), allow_network=False)
    widget = m.StandardTasksPanel(root, repository_root=repo, local_contract=contract,
                                  runtime_root=tmp_path / "rt", confirm=lambda _t: True,
                                  ask_inputs=lambda _t: {})
    monkeypatch.setattr(widget.api, "start_task_from_contract", lambda prepared: {"state": "WAITING_FOR_REMOTE"})
    refreshed = []
    monkeypatch.setattr(widget, "refresh_lage", lambda: refreshed.append(1))
    monkeypatch.setattr(widget, "_track", lambda _mission: None)
    yield widget, repo, tmp_path / "rt", refreshed
    root.destroy()
    del widget, root
    import gc
    gc.collect()


def waiting_finish(widget, start: str) -> None:
    widget._tracked_task = BY_KEY["finish"]
    widget._tracked_task_id = "t"
    widget._tracked_mission_id = "m"
    widget._tracked_head = start
    widget._last_outcome = "HUMAN_REQUIRED"
    widget._show_decision("m", "Soll ich den PR trotz Warnung mergen?")


def test_finish_start_stores_its_start_commit(panel):
    widget, repo, runtime, _refreshed = panel
    from agp_cockpit.core.verbs import BY_KEY as VERBS
    widget.apply_state(rs.RepoState(state=rs.IN_ARBEIT, summary="s", recommended=rs.ABSCHLIESSEN,
                                    offered=(rs.ABSCHLIESSEN,)))
    widget.run_verb(VERBS[rs.ABSCHLIESSEN])
    task_id = widget._tracked_task_id
    assert task_id and TaskStartHeadStore(runtime).head(task_id, task_key="finish") == git(repo, "rev-parse", "HEAD")


def test_open_finish_question_closes_when_the_work_is_published(panel):
    from agp_cockpit.core import ampel as a
    widget, repo, _runtime, _refreshed = panel
    waiting_finish(widget, git(repo, "rev-parse", "HEAD"))
    widget._poll_lage([lage(rs.IN_ARBEIT)])
    assert widget._decision_mission_id == "m" and widget.ampel_state.color == a.GELB
    publish_outside(repo)
    widget.recover_offered = True
    widget._poll_lage([lage()])
    assert widget._decision_mission_id == "" and widget.decision_frame.winfo_manager() == ""
    assert widget.recover_offered is False and widget._last_outcome == "DONE"
    assert widget.ampel_state.color == a.GRUEN
    assert widget.status_var.get().startswith("Abschließen · Rückfrage überholt")


def test_question_stays_without_green_post_merge_or_for_other_tasks(panel):
    widget, repo, _runtime, _refreshed = panel
    start = git(repo, "rev-parse", "HEAD")
    publish_outside(repo)
    waiting_finish(widget, start)
    widget._poll_lage([lage(post_merge="NOT_PASS")])
    assert widget._decision_mission_id == "m"
    widget._tracked_task = BY_KEY["release"]
    widget._poll_lage([lage()])
    assert widget._decision_mission_id == "m"


def adopt(widget, monkeypatch, mission_id="m2", task_id="t2"):
    from agp_cockpit.core import start_request
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": {
        "mission_id": mission_id, "state": "NEEDS_HUMAN", "title": "Standard · Abschließen",
        "last_summary": "Soll ich mergen?"}})
    monkeypatch.setattr(start_request, "resolve_task_binding", lambda _root, _mid: {"task_id": task_id})
    widget.adopt_pending_decision()


def test_adopted_finish_question_closes_after_a_restart(panel, monkeypatch):
    widget, repo, runtime, refreshed = panel
    start = git(repo, "rev-parse", "HEAD")
    TaskStartHeadStore(runtime).record("t2", task_key="finish", head=start)
    publish_outside(repo)
    adopt(widget, monkeypatch)
    assert widget._tracked_head == start and widget._decision_mission_id == "m2" and refreshed
    widget._poll_lage([lage()])
    assert widget._decision_mission_id == "" and "Rückfrage überholt" in widget.status_var.get()


def test_adopted_question_without_start_commit_stays_open(panel, monkeypatch):
    widget, repo, _runtime, refreshed = panel
    publish_outside(repo)
    adopt(widget, monkeypatch)
    assert widget._tracked_head == "" and not refreshed
    widget._poll_lage([lage()])
    assert widget._decision_mission_id == "m2"


def test_rejected_question_is_not_adopted_again(panel, monkeypatch):
    widget, _repo, runtime, _refreshed = panel
    HumanDecisionStore(runtime).record(mission_id="m2", task_id="t2", decision="REJECT", question="q")
    adopt(widget, monkeypatch)
    assert widget._decision_mission_id == "" and widget._tracked_mission_id == ""
    HumanDecisionStore(runtime).record(mission_id="m1", task_id="t2", decision="REJECT", question="q")
    adopt(widget, monkeypatch)
    assert widget._decision_mission_id == "m2"
