"""Slice A1 (live 2026-10-06, P4 run in the Kit repository and release 0.2.1).

AGP_LAGE_ALL_TABS_V1, AGP_WORK_TAB_HANDOFF_V1, AGP_RESULT_NAMES_TASK_V1, AGP_EFFECTS_BY_APPROVAL_V1,
AGP_FINDINGS_FROM_COCKPIT_V1, AGP_CHAT_BINDING_HINT_V1, AGP_FRESHNESS_WRAP_V1.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import agp_cockpit.ui.standard_tasks_panel as m
from agp_cockpit.core.human_decision import HumanDecisionStore
from agp_cockpit.ui.main_window import MainWindow
from agp_cockpit.ui.simple_task_panel import SimpleTaskPanel
from agp_cockpit.ui.standard_tasks_panel import StandardTasksPanel

ROOT = Path(__file__).resolve().parents[1]


def test_a_task_of_the_work_tab_counts_as_running_in_the_lage(monkeypatch):
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": {"mission_id": "m", "state": "DONE"}})
    panel = SimpleNamespace(_task_active=False, external_task_active=lambda: True)
    assert StandardTasksPanel._task_running(panel)
    panel.external_task_active = lambda: False
    assert not StandardTasksPanel._task_running(panel)


def test_the_work_tab_reports_start_and_end():
    events = []
    panel = SimpleNamespace(workflow_phase="STARTED", on_task_event=lambda e, t="": events.append((e, t)))
    assert SimpleTaskPanel.task_active(panel)
    SimpleTaskPanel._emit(panel, "finished_done", "Fertig ✓ — x")
    assert events == [("finished_done", "Fertig ✓ — x")]
    panel.on_task_event = lambda *_a: 1 / 0          # a broken listener never breaks the tab
    SimpleTaskPanel._emit(panel, "started")
    assert not SimpleTaskPanel.task_active(SimpleNamespace(workflow_phase="LOADED"))


def test_a_finished_work_task_leads_back_to_the_guided_path_only_when_done():
    calls = []
    standard = SimpleNamespace(note_external_result=lambda t: calls.append(("note", t)),
                               refresh_lage=lambda: calls.append(("lage",)))
    work = SimpleNamespace(auto_finish_armed=False)
    window = SimpleNamespace(standard_tasks_panel=standard, simple_task_panel=work,
                             tabs=SimpleNamespace(select=lambda tab: calls.append(("select", tab))))
    MainWindow._work_task_event(window, "finished_done", "TAB", "Fertig ✓ — PR #1")
    assert calls == [("note", "Fertig ✓ — PR #1"), ("select", "TAB"), ("lage",)]
    calls.clear()
    MainWindow._work_task_event(window, "finished", "TAB", "Gestoppt")    # a failure stays in its tab
    MainWindow._work_task_event(window, "started", "TAB")
    assert calls == [("lage",), ("lage",)]
    # AGP_AUTO_FINISH_V1: a ticked task hands „Abschließen“ over instead of a plain Lage refresh
    calls.clear()
    standard.request_auto_finish = lambda: calls.append(("auto",))
    work.auto_finish_armed = True
    MainWindow._work_task_event(window, "finished_done", "TAB", "Fertig ✓")
    assert calls == [("note", "Fertig ✓"), ("select", "TAB"), ("auto",)] and not work.auto_finish_armed
    work.auto_finish_armed = True
    MainWindow._work_task_event(window, "finished", "TAB", "Gestoppt")    # no finish after a failure
    assert not work.auto_finish_armed
    # AGP_AUTO_FINISH_THROUGH_DECISION_V1: a stop for an approval is not the end of the task
    work.auto_finish_armed = True
    calls.clear()
    MainWindow._work_task_event(window, "finished_human", "TAB", "Mensch muss eingreifen")
    assert work.auto_finish_armed and calls == [("lage",)]
    MainWindow._work_task_event(window, "finished_done", "TAB", "Fertig ✓")   # after the approval
    assert calls[-1] == ("auto",) and not work.auto_finish_armed


def test_an_approval_keeps_the_ticked_finish_and_a_rejection_ends_it():
    """AGP_AUTO_FINISH_THROUGH_DECISION_V1 (owner 2026-10-23)."""
    from pathlib import Path
    simple = (Path(__file__).resolve().parents[1] / "src/agp_cockpit/ui/simple_task_panel.py").read_text(encoding="utf-8")
    emit = simple[simple.index("if progress.terminal:"):][:1200]
    assert '"finished_human" if progress.outcome == "HUMAN_REQUIRED"' in emit
    assert "and self._decision_mission_id" in emit
    decide = simple[simple.index("def decide("):simple.index("def new_task(")]
    assert ('self.auto_finish_armed = bool(self.auto_finish_armed and decision == "APPROVE"\n'
            '                                      and self.auto_finish_var.get())') in decide
    assert decide.index("self.auto_finish_armed = bool(") > decide.index("request_task_start(")


def test_the_external_result_names_its_tab():
    status = SimpleNamespace(value="", set=lambda v: setattr(status, "value", v))
    panel = SimpleNamespace(status_var=status, _tracked_task=object())
    StandardTasksPanel.note_external_result(panel, "Fertig ✓ — PR #2409 gemergt")
    assert status.value == "Arbeiten · Fertig ✓ — PR #2409 gemergt"
    assert panel._tracked_task is None and panel._last_outcome == "DONE"


def test_effects_are_listed_by_the_approval_that_allowed_them(tmp_path):
    store = HumanDecisionStore(tmp_path)
    store.pre_approve(task_id="t", label="Release", scope={"agentic-kit transfer pr-create-complete"})
    store.consume("t", "a", ["agentic-kit transfer pr-create-complete"], step=1799, now=1.0)
    store.record(mission_id="m2", task_id="t", decision="APPROVE", question="Tag?", now=2.0)
    store.consume("t", "b", ["agentic-kit release-publish"], step=1807, now=3.0)
    panel = SimpleNamespace(_tracked_task=SimpleNamespace(approved_scope={"x"}), _tracked_task_id="t",
                            runtime_root=lambda: tmp_path)
    text = StandardTasksPanel.effects_text(panel)
    assert text == ("Freigegebene Wirkungen (Start-Klick): Schritt 1799: transfer pr-create-complete; "
                    "(Freigabe): Schritt 1807: release-publish.")


def test_the_kit_findings_come_from_the_cockpit_checkout(monkeypatch, tmp_path):
    import agp_cockpit.core.build_freshness as bf
    import agp_cockpit.core.kit_installation as ki
    import agp_cockpit.ui.kit_findings_window as kw
    opened = {}
    monkeypatch.setattr(bf, "cockpit_home", lambda: tmp_path / "cockpit")
    monkeypatch.setattr(ki, "discover", lambda root: SimpleNamespace(version=f"kit@{Path(root).name}"))
    monkeypatch.setattr(kw, "KitFindingsWindow", lambda master, **kw_: opened.update(kw_))
    MainWindow.open_kit_findings(SimpleNamespace(repository_root=tmp_path / "agentic-project-kit"))
    assert opened == {"repository_root": tmp_path / "cockpit", "installed_version": "kit@cockpit"}


def test_wiring_in_the_sources():
    window = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert "AGP_FRESHNESS_WRAP_V1" in window and "wraplength=max(240, event.width - 300)" in window
    assert "external_task_active = self.simple_task_panel.task_active" in window
    panel = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
    assert "AGP_CHAT_BINDING_HINT_V1" in panel and "„Neuer Chat“" in panel
    assert 'text = f"{self._tracked_task.label} · {text}"' in panel          # AGP_RESULT_NAMES_TASK_V1
    simple = (ROOT / "src/agp_cockpit/ui/simple_task_panel.py").read_text(encoding="utf-8")
    assert 'self._emit("started")' in simple and '"finished_done" if progress.outcome == "DONE"' in simple
