from pathlib import Path

GUI=Path('src/agp_cockpit/ui/main_window.py').read_text(encoding='utf-8')

def test_real_gui_has_no_legacy_refresh_control():
    assert 'AGP_BROWSER_REFRESH_BUTTON_062' not in GUI
    assert 'Browser-Verbindung neu laden' not in GUI
    assert 'reason="cockpit-button"' not in GUI

def test_actual_main_window_evidence():
    assert "AGP Cockpit" in GUI
    assert "SimpleTaskPanel(" in GUI
    for token in ("Expert · System", "Expert · Einzelauftrag", "Expert · Task Operator"):
        assert token not in GUI
    assert "ttk.Notebook" in GUI
    assert 'text="Standard Tasks"' in GUI
