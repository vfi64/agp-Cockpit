from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'src/agp_cockpit/ui/main_window.py').read_text()
WORK=(ROOT/'src/agp_cockpit/ui/work_order_panel.py').read_text()
TASK=(ROOT/'src/agp_cockpit/ui/task_operator_panel.py').read_text()
def test_no_legacy_browser_refresh_control_in_normal_gui():
    assert '.place(relx=0.985' not in MAIN
    assert 'Browser-Verbindung neu laden' not in MAIN
def test_normal_gui_is_single_task_first_surface():
    assert 'text="Expert · Task Operator"' not in MAIN
    assert 'ttk.Notebook' not in MAIN
    assert 'SimpleTaskPanel' in MAIN
def test_task_operator_has_visible_focus_status():
    assert 'Tastaturfokus:' in TASK
    assert '<FocusIn>' in TASK
    assert 'takefocus=True' in TASK
def test_work_order_areas_are_compact():
    assert 'height=4' in WORK
    assert 'height=5' in WORK
