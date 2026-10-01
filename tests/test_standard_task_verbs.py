"""Plan P3 (AGP_STANDARD_TASK_VERBS_V1): verbs, enabling by state, tooltips, tab order."""
from __future__ import annotations

from pathlib import Path

import pytest

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.verbs import BY_KEY, VERBS, availability

ROOT = Path(__file__).resolve().parents[1]
MAIN = "a" * 40


def state(**kw):
    base = {"root": "/r", "is_git": True, "branch": "main", "head": MAIN, "origin_main": MAIN,
            "tracking_main": MAIN, "own_commits": 0, "kit_version": "1.0.13", "workspace": True,
            "gh_ok": True, "post_merge": "PASS"}
    base.update(kw)
    return rs.classify(rs.RepoFacts(**base))


def test_every_verb_has_a_label_badge_and_three_tooltip_lines():
    assert {v.key for v in VERBS} == set(rs.LABELS) - {rs.LAGEBERICHT}
    for verb in VERBS:
        assert verb.label == rs.LABELS[verb.key]
        assert verb.badge
        lines = verb.tooltip().splitlines()
        assert len(lines) == 3 and lines[1].startswith("Wirkung:") and lines[2].startswith("Verfügbar:")
    assert [v.step for v in VERBS if v.group == "weg"] == [1, 2, 3, 4]


def test_availability_follows_state_and_implementation():
    ready = state()
    assert availability(BY_KEY[rs.CHAT_WECHSELN], ready) == (True, "")
    enabled, reason = availability(BY_KEY[rs.ARBEITEN], ready)
    assert not enabled and "Zustand IN_ARBEIT" in reason and "Aktuell: BEREIT" in reason
    assert availability(BY_KEY[rs.ABSCHLIESSEN], ready)[1] == "In Vorbereitung (Plan P6)."
    assert availability(BY_KEY[rs.CHAT_WECHSELN], None) == (False, "Lagebericht läuft noch.")
    running = state(task_running=True)
    assert not any(availability(v, running)[0] for v in VERBS)


def test_standard_tasks_tab_comes_before_arbeiten():
    main = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text()
    assert main.index('text="Standard Tasks")') < main.index('text="Arbeiten")') < main.index('text="System")')
    assert "on_open_work=lambda: self.tabs.select(work_tab)" in main


@pytest.fixture
def panel(monkeypatch, tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
    opened = []
    widget = m.StandardTasksPanel(root, repository_root=Path(tmp_path), on_open_work=lambda: opened.append(1))
    widget.grid()
    yield root, widget, opened
    root.destroy()


def test_panel_enables_only_valid_verbs_and_marks_the_recommendation(panel):
    _root, widget, opened = panel
    assert all(str(b.cget("state")) == "disabled" for b in widget.verb_buttons.values())
    widget.apply_state(state(branch="feat/x", own_commits=1, changes=("a.py",)))   # IN_ARBEIT -> Arbeiten
    buttons = widget.verb_buttons
    assert str(buttons[rs.ARBEITEN].cget("state")) == "normal"
    assert buttons[rs.ARBEITEN].cget("text") == "★ ② Arbeiten"
    assert str(buttons[rs.ARBEITEN].cget("style")) == "Recommended.TButton"
    assert str(buttons[rs.CHAT_WECHSELN].cget("state")) == "normal"
    assert str(buttons[rs.ARBEIT_BEGINNEN].cget("state")) == "disabled"
    assert "In Vorbereitung (Plan P7)" in widget._tooltip(BY_KEY[rs.ARBEIT_BEGINNEN])
    widget.run_verb(BY_KEY[rs.ARBEITEN])
    assert opened == [1]
    widget.run_verb(BY_KEY[rs.ARBEIT_BEGINNEN])
    assert widget.status_var.get() == "In Vorbereitung (Plan P7)."


def test_more_section_is_collapsed_until_opened(panel):
    root, widget, _ = panel
    root.update()
    assert not widget.more_frame.winfo_ismapped()
    widget.toggle_more()
    root.update()
    assert widget.more_frame.winfo_ismapped() and widget.more_button.cget("text") == "Weitere ausblenden"


def test_tooltip_shows_and_hides(panel):
    _root, widget, _ = panel
    from agp_cockpit.ui.tooltip import Tooltip
    tip = Tooltip(widget.verb_buttons[rs.CHAT_WECHSELN], "Hallo")
    tip.show()
    assert tip._window is not None
    tip.hide()
    assert tip._window is None
