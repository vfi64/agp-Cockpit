"""Slice A2 (owner 2026-10-06): the „Arbeiten“ tab gets the Ampel, a fixed-height editor,
wrapping buttons and a decision box whose buttons stay visible, with the Cockpit's own facts."""
import subprocess
from pathlib import Path
from typing import ClassVar

import pytest

from agp_cockpit.core import ampel as a
from agp_cockpit.core import work_facts

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")


def test_the_work_tab_light_follows_its_task_and_mirrors_the_lage_at_rest():
    repo = a.Ampel(a.GRUEN, "alles in Ordnung, bereit für neue Arbeit")
    assert a.work_ampel("EMPTY", repo_light=repo) == repo
    assert a.work_ampel("STARTED", repo_light=repo).color == a.GELB
    assert "Anhangslimit" in a.work_ampel("STARTED", waiting="wartet auf das ChatGPT-Anhangslimit").text
    assert a.work_ampel("LOADED", decision_pending=True).reason == "deine Entscheidung ist gefragt"
    assert a.work_ampel("LOADED", outcome="HUMAN_REQUIRED").color == a.ROT
    assert a.work_ampel("LOADED", outcome="STOPPED").color == a.ROT
    assert a.work_ampel("LOADED", outcome="DONE").color == a.GRUEN
    assert a.work_ampel("EMPTY").color == a.GRAU
    assert "repo_light=lambda: self.standard_tasks_panel.ampel_state" in MAIN


def _git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                   env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin:/usr/local/bin"})


def test_decision_facts_come_from_git_not_from_the_remote_side(tmp_path):
    _git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("1\n2\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "base")
    _git(tmp_path, "update-ref", "refs/remotes/origin/main", "HEAD")
    _git(tmp_path, "switch", "-qc", "fix/x")
    (tmp_path / "a.txt").write_text("1\n3\n4\n")
    (tmp_path / "b.txt").write_text("neu\n")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "change")
    (tmp_path / "c.txt").write_text("lose\n")
    facts = work_facts.observe(tmp_path)
    assert (facts.branch, facts.commits, facts.files, facts.insertions, facts.deletions) == ("fix/x", 1, 2, 3, 1)
    line = work_facts.facts_line(facts)
    assert line.startswith("Vom Cockpit geprüft: Branch fix/x @ ")
    assert "1 Commit(s) vor origin/main · 2 Datei(en) (+3 −1) · 1 nicht committete Änderung(en)" in line
    diff = work_facts.diff_text(tmp_path, facts)
    assert "change" in diff and "+neu" in diff and "?? c.txt" in diff
    assert work_facts.facts_line(work_facts.observe(tmp_path / "nope")).endswith("kein Git-Stand lesbar.")


@pytest.fixture
def tk_root():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    yield root
    root.destroy()


def test_the_buttons_wrap_with_the_window_width(tk_root):
    from tkinter import ttk

    from agp_cockpit.ui.flow_row import FlowRow
    row = FlowRow(tk_root)
    row.pack(fill="x")
    buttons = [row.add(ttk.Button(row, text=f"Knopf Nummer {i}")) for i in range(8)]
    tk_root.geometry("2000x200")
    for _ in range(4):
        tk_root.update()
    assert row.rows() == 1
    tk_root.geometry("320x400")
    for _ in range(4):
        tk_root.update()
    assert row.rows() > 2
    assert all(b.winfo_ismapped() for b in buttons)
    assert all(frame.winfo_reqwidth() <= 320 for frame in row._rows if frame.winfo_manager())


def _panel(tk_root, monkeypatch, tmp_path):
    import agp_cockpit.ui.simple_task_panel as m
    from agp_cockpit.ui.scrollable import ScrollableTab

    class FakeAPI:
        def __init__(self, *args, **kwargs):
            pass

        class operator_control:
            requests: ClassVar[list] = []

            @classmethod
            def request(cls, action):
                cls.requests.append(action)

    monkeypatch.setattr(m, "TaskOperatorAPI", FakeAPI)
    tk_root.geometry("720x480")
    from tkinter import ttk
    # the main window's title, repository line and tab bar take about 150 px
    ttk.Frame(tk_root, height=150).pack(fill="x")
    tab = ScrollableTab(tk_root)
    tab.pack(fill="both", expand=True)
    panel = m.SimpleTaskPanel(tab.inner, repository_root=tmp_path,
                              repo_light=lambda: a.Ampel(a.GRUEN, "alles in Ordnung"))
    panel.grid(row=0, column=0, sticky="nsew")
    return panel, tab


def test_at_720x480_the_decision_buttons_stay_visible_with_a_long_question(tk_root, monkeypatch, tmp_path):
    panel, tab = _panel(tk_root, monkeypatch, tmp_path)
    panel._set_editor("Zeile\n" * 200)
    question = "\n".join(f"Behauptung {i} der Remote-Seite über Branch, Commit und Dateien." for i in range(60))
    panel._show_decision("M1", question)
    for _ in range(3):
        tk_root.update()
        tab._layout()
    panel._scroll_to_decision()
    tk_root.update()
    assert int(panel.editor.cget("height")) == 8 and int(panel.decision_question.cget("height")) == 5
    bottom = tab.winfo_rooty() + tab.winfo_height()
    for button in (panel.approve_decision_button, panel.reject_decision_button, panel.diff_button):
        assert button.winfo_viewable()
        assert tab.winfo_rooty() <= button.winfo_rooty(), button.cget("text")
        assert button.winfo_rooty() + button.winfo_height() <= bottom, button.cget("text")
    assert panel.ampel_var.get() == "Gelb — deine Entscheidung ist gefragt"
    assert panel.decision_facts_var.get().startswith("Vom Cockpit geprüft:")
    assert panel.actions.rows() >= 1


def test_the_light_mirrors_the_lage_at_rest_and_the_changes_window_opens(tk_root, monkeypatch, tmp_path):
    panel, _tab = _panel(tk_root, monkeypatch, tmp_path)
    panel.update_ampel()
    assert panel.ampel_var.get() == "Grün — alles in Ordnung"
    panel._show_decision("M1", "Push?")
    panel.show_changes()
    tk_root.update()
    assert panel.changes_window.winfo_exists()
    panel._hide_decision()
    assert panel.ampel_var.get() == "Grün — alles in Ordnung"


def test_narrowing_the_window_wraps_instead_of_scrolling_sideways(tk_root, monkeypatch, tmp_path):
    """AGP_VIEWPORT_WRAP_V1 (live 2026-10-07, r5): narrowing the window cut off the buttons
    and showed a horizontal scroll bar, because the panel wrapped to its own (old) width."""
    from tkinter import ttk

    import agp_cockpit.ui.simple_task_panel as m
    from agp_cockpit.ui.scrollable import ScrollableTab

    class FakeAPI:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(m, "TaskOperatorAPI", FakeAPI)
    tk_root.geometry("1000x700")
    tabs = ttk.Notebook(tk_root)
    tabs.pack(fill="both", expand=True)
    tab = ScrollableTab(tabs)
    tabs.add(tab, text="Arbeiten")
    panel = m.SimpleTaskPanel(tab.inner, repository_root=tmp_path)
    panel.grid(row=0, column=0, sticky="nsew")
    panel._show_decision("M1", "Frage " * 200)

    def settle(width):
        tk_root.geometry(f"{width}x700")
        for _ in range(6):
            tk_root.update()

    settle(1000)
    assert panel.actions.rows() == 1
    for width in (760, 620):
        settle(width)
        right = tab.canvas.winfo_rootx() + tab.canvas.winfo_width()
        assert not tab.hbar.winfo_ismapped(), width
        assert panel.actions.rows() >= 2, width
        for widget in (*panel.actions.items, panel.approve_decision_button, panel.diff_button):
            assert widget.winfo_rootx() + widget.winfo_width() <= right, (width, widget)
    settle(1000)
    assert panel.actions.rows() == 1 and not tab.hbar.winfo_ismapped()


def test_the_standard_tasks_rows_wrap_and_the_repo_path_has_its_own_line(tk_root, monkeypatch, tmp_path):
    """AGP_VIEWPORT_WRAP_V1 + AGP_REPO_LINE_V1 (live 2026-10-07): „Arbeitsweg“ and „Bei Problemen“
    were cut at the right edge, the System tab and the repository path as well."""
    from tkinter import ttk

    from agp_cockpit.ui import standard_tasks_panel as m
    from agp_cockpit.ui.scrollable import ScrollableTab
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
    tk_root.geometry("1000x700")
    tabs = ttk.Notebook(tk_root)
    tabs.pack(fill="both", expand=True)
    tab = ScrollableTab(tabs)
    tabs.add(tab, text="Standard Tasks")
    panel = m.StandardTasksPanel(tab.inner, repository_root=tmp_path, on_open_work=lambda: None)
    panel.grid(row=0, column=0, sticky="nsew")
    for width in (1000, 560):
        tk_root.geometry(f"{width}x700")
        for _ in range(8):
            tk_root.update()
    right = tab.canvas.winfo_rootx() + tab.canvas.winfo_width()
    assert not tab.hbar.winfo_ismapped()
    assert panel.path_row.rows() >= 2
    for button in panel.verb_buttons.values():
        if button.winfo_ismapped():
            assert button.winfo_rootx() + button.winfo_width() <= right, button.cget("text")
    main = MAIN
    assert 'self._context_label.grid(row=0, column=0, columnspan=3, sticky="w")' in main
    assert "follow_viewport(parent, wrap_system)" in main


def test_problem_buttons_align_and_the_system_boxes_share_their_height(tk_root, monkeypatch, tmp_path):
    """Owner 2026-10-07: „Wiederherstellen“ and „Weitere anzeigen“ on one line; Ollama and
    Hermes equally high with their buttons at the bottom (AGP_SYSTEM_BOXES_V1)."""
    from agp_cockpit.core import repo_state as rs
    from agp_cockpit.ui import standard_tasks_panel as m
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
    tk_root.geometry("1000x700")
    panel = m.StandardTasksPanel(tk_root, repository_root=tmp_path, on_open_work=lambda: None)
    panel.pack(fill="both", expand=True)
    for _ in range(6):
        tk_root.update()
    assert panel.verb_buttons[rs.WIEDERHERSTELLEN].winfo_rooty() == panel.more_button.winfo_rooty()
    assert all(w.winfo_class() == "TFrame" for w in panel.path_row.items)  # arrows sit in the cells
    system = MAIN[MAIN.index("def _build_system_tab"):]
    assert system.count('sticky="nsew"') >= 2 and "ollama.rowconfigure(2, weight=1)" in system
    assert "hermes.rowconfigure(1, weight=1)" in system and system.count('sticky="sw"') >= 2
