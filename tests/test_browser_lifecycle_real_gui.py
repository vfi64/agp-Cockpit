from pathlib import Path

GUI=Path('src/agp_cockpit/ui/main_window.py').read_text(encoding='utf-8')

def test_real_gui_refresh_control():
    assert 'AGP_BROWSER_REFRESH_BUTTON_062' in GUI
    assert 'Browser-Verbindung neu laden' in GUI
    assert 'reason="cockpit-button"' in GUI
    assert '.winfo_toplevel()' in GUI

def test_actual_main_window_evidence():
    # K07 task-first default; established GUI remains as Expert tabs.
    for token in ('AGP Cockpit','Arbeiten','Expert · System','Expert · Einzelauftrag','Notebook'):
        assert token in GUI
