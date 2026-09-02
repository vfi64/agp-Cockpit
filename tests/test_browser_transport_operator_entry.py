from pathlib import Path


def test_browser_transport_has_operator_entry():
    source = Path(
        "src/agp_cockpit/ui/browser_transport_panel.py"
    ).read_text(encoding="utf-8")

    assert "Mission Operator öffnen" in source
    assert "MissionOperatorWindow" in source
