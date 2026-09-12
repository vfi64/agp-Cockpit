from __future__ import annotations

import json
from pathlib import Path


def _make_extension(root: Path, *, version: str = "0.3.0") -> Path:
    ext = root / "chrome_extension"
    ext.mkdir(parents=True)
    (ext / "manifest.json").write_text(
        json.dumps({"manifest_version": 3, "name": "AGP Cockpit Bridge", "version": version}),
        encoding="utf-8",
    )
    (ext / "background.js").write_text("console.log('agp');\n", encoding="utf-8")
    (ext / "ignored.bak").write_text("do not stage\n", encoding="utf-8")
    return ext


def test_stage_extension_uses_application_support_not_repository(monkeypatch, tmp_path):
    from agp_cockpit.adapters import macos_extension

    repo = tmp_path / "repo"
    source = _make_extension(repo)
    support = tmp_path / "Library" / "Application Support" / "AGP Cockpit"
    monkeypatch.setattr(macos_extension, "settings_path", lambda: support / "settings.json")

    staged = macos_extension.stage_extension(repo)

    assert staged == support / "chrome_extension"
    assert staged != source
    assert (staged / "manifest.json").is_file()
    assert (staged / "background.js").is_file()
    assert not (staged / "ignored.bak").exists()
    marker = json.loads((staged / ".agp-stage.json").read_text(encoding="utf-8"))
    assert marker["version"] == "0.3.0"
    assert len(marker["sha256"]) == 64


def test_stage_extension_reuses_identical_stage(monkeypatch, tmp_path):
    from agp_cockpit.adapters import macos_extension

    repo = tmp_path / "repo"
    _make_extension(repo)
    support = tmp_path / "support"
    monkeypatch.setattr(macos_extension, "settings_path", lambda: support / "settings.json")

    first = macos_extension.stage_extension(repo)
    marker_before = (first / ".agp-stage.json").read_text(encoding="utf-8")
    second = macos_extension.stage_extension(repo)

    assert second == first
    assert (second / ".agp-stage.json").read_text(encoding="utf-8") == marker_before


def test_bootstrap_contract_uses_configured_bridge_endpoint_and_local_extension():
    source = Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert "host=bridge_host" in source
    assert "port=bridge_port" in source
    assert 'f"http://{bridge_host}:{bridge_port}/v1/status"' in source
    assert "stage_extension(root)" in source
    assert "extension_path=extension_path" in source
    assert "DEFAULT_PORT = 8765" not in source
    assert '"http://127.0.0.1:9876/v1/status"' not in source


def test_app_passes_versioned_bridge_settings_to_bootstrap():
    source = Path("src/agp_cockpit/app.py").read_text(encoding="utf-8")
    assert "bridge_host=settings.bridge_host" in source
    assert "bridge_port=settings.bridge_port" in source
