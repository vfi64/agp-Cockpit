from pathlib import Path

from agp_cockpit.adapters import macos_settings
from agp_cockpit.app_bootstrap import build_extension_guidance


def test_production_bridge_token_path_is_application_support(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    expected=tmp_path/"Library"/"Application Support"/"AGP Cockpit"/"bridge"/"token.txt"
    assert macos_settings.bridge_token_path() == expected

def test_extension_guidance_uses_production_token_authority(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    repo=tmp_path/"repo"; ext=tmp_path/"staged-extension"
    text=build_extension_guidance(repo, extension_path=ext, bridge_host="127.0.0.1", bridge_port=8765)
    assert str(macos_settings.bridge_token_path()) in text
    assert str(repo/".local"/"agp-cockpit"/"bridge"/"token.txt") not in text

def test_production_extension_readme_names_application_support_token():
    text=Path("chrome_extension/README.md").read_text(encoding="utf-8")
    assert "~/Library/Application Support/AGP Cockpit/bridge/token.txt" in text
    assert "Do not use that development token for the production desktop bridge." in text
