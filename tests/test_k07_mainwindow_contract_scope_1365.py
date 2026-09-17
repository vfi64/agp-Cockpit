from pathlib import Path
def test_mainwindow_persists_and_forwards_injected_local_contract():
    s=Path("src/agp_cockpit/ui/main_window.py").read_text()
    assert "self.local_contract = local_contract" in s
    assert "local_contract=self.local_contract," in s
    # The failing _build expression from the real 1364 traceback is gone.
    assert "local_contract=local_contract," not in s
