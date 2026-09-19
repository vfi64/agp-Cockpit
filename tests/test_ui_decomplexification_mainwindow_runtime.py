from pathlib import Path

def test_mainwindow_schedules_visible_system_runtime_refresh():
    s=Path("src/agp_cockpit/ui/main_window.py").read_text()
    init=s[s.index("def __init__("):s.index("def _build(",s.index("def __init__("))]
    assert "self.after(80, self.refresh_runtime_status)" in s
    assert "self.simple_task_panel = SimpleTaskPanel(" in s

def test_runtime_diagnostics_are_part_of_visible_system_build():
    s=Path("src/agp_cockpit/ui/main_window.py").read_text()
    build=s[s.index("def _build("):s.index("def _build_system_tab(",s.index("def _build("))]
    assert 'self.tabs.add(system_tab, text="System")' in s
    assert "model_box" in s
    assert "runtime_refresh_button" in s
    assert "repair_button" in s
    assert "hermes_model_button" in s


def test_simplified_header_is_not_pending():
    s=Path("src/agp_cockpit/ui/main_window.py").read_text()
    assert 'value="Lokale Laufzeit bereit"' in s
