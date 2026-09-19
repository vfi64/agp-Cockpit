from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'src/agp_cockpit/ui/main_window.py').read_text()
WORK=(ROOT/'src/agp_cockpit/ui/work_order_panel.py').read_text()
TASK=(ROOT/'src/agp_cockpit/ui/task_operator_panel.py').read_text()
def test_task_buttons_are_direct_native_children():
    assert 'ttk.Button(self,text="Status aktualisieren"' in TASK
    assert 'controls=ttk.Frame' not in TASK
def test_task_focus_feedback_remains_explicit():
    assert 'Tastaturfokus:' in TASK and '<FocusIn>' in TASK
def test_order_editor_tab_moves_focus():
    assert 'bind("<Tab>", self._focus_next)' in WORK
    assert 'Tastaturfokus:' in WORK
def test_system_focus_feedback_exists():
    assert 'system_focus_var' in MAIN
    assert 'runtime_refresh_button' in MAIN
