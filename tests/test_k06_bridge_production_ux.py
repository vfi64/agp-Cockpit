from pathlib import Path

from agp_cockpit.adapters.macos_context import resolve_repository_root
from agp_cockpit.settings import AppSettings

ROOT = Path(__file__).resolve().parents[1]

def _repo(path: Path) -> Path:
    (path / "chrome_extension").mkdir(parents=True)
    (path / ".agentic").mkdir()
    return path

def test_default_bridge_is_simple_operator_surface():
    source = (ROOT / "chrome_extension" / "content.js").read_text()
    start = source.index('const actions = document.createElement("div")')
    end = source.index("if (AGP_DIAGNOSTICS_OPEN)", start)
    default = source[start:end]
    for label in ("Aufgabe starten","Stoppen","Nächster Schritt","Aktualisieren","Diagnose"):
        assert label in default
    for historical in ("P5 Bind","P7 One Round","P8 Run","LIVE Probe","New DRY Mission"):
        assert historical not in default

def test_diagnostics_collapsed_by_default_and_accessible():
    source = (ROOT / "chrome_extension" / "content.js").read_text()
    assert "let AGP_DIAGNOSTICS_OPEN = false;" in source
    assert 'setAttribute("aria-expanded"' in source
    assert 'setAttribute("aria-controls", "agp-cockpit-diagnostics")' in source
    assert 'setAttribute("aria-label", "Entwicklerdiagnose")' in source

def test_historical_controls_remain_available_only_in_diagnostics():
    source = (ROOT / "chrome_extension" / "content.js").read_text()
    diag = source[source.index("if (AGP_DIAGNOSTICS_OPEN)"):]
    for label in ("Phase 5: Bind","Phase 7: One Round","Phase 8: Run","LIVE 3-Turn"):
        assert label in diag

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
