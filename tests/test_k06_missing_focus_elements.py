from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MAIN=(ROOT/'src/agp_cockpit/ui/main_window.py').read_text()
BROWSER=(ROOT/'src/agp_cockpit/ui/browser_transport_panel.py').read_text()
def test_mission_operator_native_named_focus_control():
    assert 'self.mission_operator_button = ttk.Button(' in BROWSER
    assert 'text=\"Mission Operator öffnen\"' in BROWSER
    assert 'takefocus=True' in BROWSER
def test_missing_auftrag_focus_labels():
    assert 'Tastaturfokus: Mission Operator öffnen' in MAIN
    assert 'Tastaturfokus: Browser-Verbindung neu laden' in MAIN
