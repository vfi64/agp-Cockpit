from pathlib import Path

from agp_cockpit.adapters.macos_context import resolve_repository_root
from agp_cockpit.settings import AppSettings

ROOT = Path(__file__).resolve().parents[1]

def _repo(path: Path) -> Path:
    (path / "chrome_extension").mkdir(parents=True)
    (path / ".agentic").mkdir()
    (path / ".git").mkdir()
    return path

def test_default_bridge_is_simple_operator_surface_without_diagnostics_toggle():
    source = (ROOT / "chrome_extension" / "content.js").read_text()
    source += (ROOT / "chrome_extension" / "cockpit_panel.js").read_text()   # AGP_PANEL_MODULE_V1: the overlay lives in cockpit_panel.js
    for label in ("Aufgabe starten","Stoppen","Nächster Schritt","Aktualisieren"):
        assert label in source
    assert "▸ Diagnose" not in source
    assert "▾ Diagnose" not in source

def test_historical_phase_controls_are_absent_from_normal_overlay():
    source = (ROOT / "chrome_extension" / "content.js").read_text()
    source += (ROOT / "chrome_extension" / "cockpit_panel.js").read_text()   # AGP_PANEL_MODULE_V1: the overlay lives in cockpit_panel.js
    for label in ("Phase 5: Bind","Phase 7: One Round","Phase 8: Run","LIVE 3-Turn"):
        assert label not in source

def test_structurally_valid_saved_root_remains_authoritative(tmp_path):
    saved = _repo(tmp_path / "saved-repository")
    actual = _repo(tmp_path / "actual-repository")
    root, source = resolve_repository_root(
        explicit_root=None,
        settings=AppSettings(repository_root=str(saved)),
        cwd=actual,
        chooser=None,
    )
    assert root == saved.resolve()
    assert source == "settings"


def test_persist_repository_root_rejects_non_repository(tmp_path, monkeypatch):
    from agp_cockpit.adapters import macos_context
    from agp_cockpit.settings import AppSettings
    monkeypatch.setattr(macos_context, "save_settings", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not persist")))
    import pytest
    with pytest.raises(ValueError, match="valid AGP Cockpit repository"):
        macos_context.persist_repository_root(AppSettings(), tmp_path / "not-a-repo")
