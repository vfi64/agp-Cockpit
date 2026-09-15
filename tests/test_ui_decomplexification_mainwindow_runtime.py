from pathlib import Path

def test_simplified_mainwindow_does_not_schedule_removed_system_tab_runtime_refresh():
    s=Path("src/agp_cockpit/ui/main_window.py").read_text()
    init=s[s.index("def __init__("):s.index("def _build(",s.index("def __init__("))]
    assert "self.after(80, self.refresh_runtime_status)" not in init
    assert "self.simple_task_panel = SimpleTaskPanel(" in s

def test_legacy_runtime_diagnostics_are_not_part_of_normal_build():
    s=Path("src/agp_cockpit/ui/main_window.py").read_text()
    build=s[s.index("def _build("):s.index("def _build_system_tab(",s.index("def _build("))]
    assert "model_box" not in build
    assert "runtime_refresh_button" not in build
    assert "repair_button" not in build
    assert "hermes_model_button" not in build


def test_simplified_header_is_not_pending():
    s=Path("src/agp_cockpit/ui/main_window.py").read_text()
    assert 'value="Lokale Laufzeit bereit"' in s
