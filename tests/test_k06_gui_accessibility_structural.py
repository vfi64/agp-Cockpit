from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'src/agp_cockpit/ui/main_window.py').read_text()
WORK=(ROOT/'src/agp_cockpit/ui/work_order_panel.py').read_text()
TASK=(ROOT/'src/agp_cockpit/ui/task_operator_panel.py').read_text()
def test_no_floating_browser_refresh_overlay():
    assert '.place(relx=0.985' not in MAIN
    assert 'Browser-Verbindung neu laden' in MAIN
def test_task_operator_is_notebook_tab():
    # K07 task-first UX keeps the durable operator as a preserved Expert tab.
    assert 'text="Expert · Task Operator"' in MAIN
    assert 'TaskOperatorPanel' in MAIN
    assert 'row=99' not in MAIN
def test_task_operator_has_visible_focus_status():
    assert 'Tastaturfokus:' in TASK
    assert '<FocusIn>' in TASK
    assert 'takefocus=True' in TASK
def test_work_order_areas_are_compact():
    assert 'height=4' in WORK
    assert 'height=5' in WORK
