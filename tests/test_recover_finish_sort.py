"""Owner 2026-10-07 after PR #272: the interruption memory expires on a clean work branch,
„Abschließen“ never repairs code or tests, and the Kit findings table sorts by column."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import finish_guard as fg
from agp_cockpit.core import kit_findings as kf
from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.verbs import recover_not_needed

ROOT = Path(__file__).resolve().parents[1]


def _state(name, recommended, *, own=2, changes=()):
    return SimpleNamespace(state=name, recommended=recommended,
                           facts=SimpleNamespace(own_commits=own, changes=tuple(changes)))


# --- AGP_RECOVER_OFFER_EXPIRES_V1 ----------------------------------------------------------

def test_a_clean_work_branch_ready_to_finish_needs_no_recovery():
    assert recover_not_needed(_state(rs.IN_ARBEIT, rs.ABSCHLIESSEN))           # PR #272 after the fix
    assert not recover_not_needed(_state(rs.IN_ARBEIT, rs.ABSCHLIESSEN, changes=("tests/x.py",)))
    assert not recover_not_needed(_state(rs.IN_ARBEIT, rs.ABSCHLIESSEN, own=0, changes=("a",)))
    assert not recover_not_needed(_state(rs.STOERUNG, rs.WIEDERHERSTELLEN))
    assert not recover_not_needed(None)
    panel = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
    apply = panel[panel.index("def apply_state"):]
    assert apply.index("recover_not_needed(state)") < apply.index("recommended = WIEDERHERSTELLEN")


# --- AGP_FINISH_PUBLISHES_ONLY_V1 ----------------------------------------------------------

STEP_1839 = '''
from pathlib import Path
p = Path("tests/test_repo_state.py")
p.write_text(p.read_text().replace(".local/agp-cockpit/state/repo-state.json", "repo-state.json"))
'''


def test_a_finish_work_order_may_not_touch_tests_or_src():
    assert fg.violations(STEP_1839, {"dirty": []}, [])                         # the live repair
    assert fg.violations('subprocess.run(["sed", "-i", "s/a/b/", "src/x.py"])', {"dirty": []}, [])
    publishing = 'subprocess.run(["agentic-kit", "transfer", "pr-create-complete", "--title", "T"])'
    assert fg.violations(publishing, {"dirty": []}, ["agentic-kit transfer pr-create-complete"]) == []


def test_a_finish_commits_only_work_that_was_there_at_its_start():
    used = ["agentic-kit transfer commit", "agentic-kit transfer pr-create-complete"]
    clean = fg.violations("x = 1", {"dirty": []}, used)
    assert len(clean) == 1 and "sauber" in clean[0]
    assert fg.violations("x = 1", {"dirty": [" M CHANGELOG.md"]}, used) == []   # Arbeiten left work


def test_the_start_state_is_recorded_once_per_mission(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    runtime = tmp_path / "runtime"
    first = fg.start_state(runtime, "M1", repo)
    (runtime / "finish-start.json").write_text(json.dumps({"mission_id": "M1", "dirty": ["kept"]}))
    assert fg.start_state(runtime, "M1", repo)["dirty"] == ["kept"]           # not re-read
    assert fg.start_state(runtime, "M2", repo)["mission_id"] == "M2"
    assert first["mission_id"] == "M1"
    assert fg.is_finish_mission("Standard · Abschließen") and fg.is_finish_mission("Standard · Abschließen · Entscheidung")
    assert not fg.is_finish_mission("Standard · Release") and not fg.is_finish_mission("Task · x")


def test_the_bridge_checks_finish_work_orders_before_running_them():
    bridge = (ROOT / "src/agp_cockpit/core/bridge_server.py").read_text(encoding="utf-8")
    block = bridge[bridge.index("AGP_FINISH_PUBLISHES_ONLY_V1"):]
    assert block.index("finish_guard.is_finish_mission(") < block.index('raise ValueError("command-file semantic contract rejected: "')
    assert block.index("raise ValueError") < block.index("except ValueError as rejection")


# --- AGP_FINDINGS_SORT_V1 ------------------------------------------------------------------

def _finding(fid, title="t", severity="medium", status="OPEN", first="2026-10-01"):
    return kf.KitFinding(fid, title, severity, status, first)


def test_ids_sort_by_number_and_severities_by_weight():
    items = [_finding("KIT-GF-10"), _finding("KIT-GF-RULE-REGISTRY-BOOTSTRAP"), _finding("KIT-GF-2")]
    assert [f.id for f in sorted(items, key=lambda f: kf.sort_key(f, "id"))] == [
        "KIT-GF-2", "KIT-GF-10", "KIT-GF-RULE-REGISTRY-BOOTSTRAP"]
    weights = [_finding("A", severity="low"), _finding("B", severity="critical"), _finding("C", severity="high")]
    assert [f.id for f in sorted(weights, key=lambda f: kf.sort_key(f, "severity"))] == ["B", "C", "A"]


def test_the_window_opens_sorted_by_id_and_a_click_sorts_and_reverses(tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    try:
        register = tmp_path / kf.REGISTER
        register.parent.mkdir(parents=True)
        register.write_text(json.dumps({"families": [
            {"id": "KIT-GF-10", "title": "b", "severity": "low", "status": "OPEN", "first_observed": "2026-10-02"},
            {"id": "KIT-GF-2", "title": "c", "severity": "critical", "status": "OPEN", "first_observed": "2026-10-03"},
            {"id": "KIT-GF-1", "title": "a", "severity": "high", "status": "OPEN", "first_observed": "2026-10-01"},
        ]}))
        from agp_cockpit.ui.kit_findings_window import KitFindingsWindow
        window = KitFindingsWindow(root, repository_root=tmp_path, installed_version="1.0.13")
        assert window.tree.get_children() == ("KIT-GF-1", "KIT-GF-2", "KIT-GF-10")
        assert window.tree.heading("id")["text"] == "ID ▲"
        window.tree.selection_set("KIT-GF-10")
        window.sort_by("severity")
        assert window.tree.get_children() == ("KIT-GF-2", "KIT-GF-1", "KIT-GF-10")
        assert window.tree.heading("severity")["text"] == "Schwere ▲" and window.tree.heading("id")["text"] == "ID"
        assert window.tree.selection() == ("KIT-GF-10",)                  # the selection stays
        window.sort_by("severity")
        assert window.tree.get_children() == ("KIT-GF-10", "KIT-GF-1", "KIT-GF-2")
        assert window.tree.heading("severity")["text"] == "Schwere ▼"
    finally:
        root.destroy()
