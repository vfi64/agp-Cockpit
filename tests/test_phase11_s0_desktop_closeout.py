from __future__ import annotations

import json
from pathlib import Path


def _make_extension(root: Path, *, version: str = "0.3.0") -> Path:
    ext = root / "chrome_extension"
    ext.mkdir(parents=True)
    (ext / "manifest.json").write_text(
        json.dumps(
            {
                "manifest_version": 3,
                "name": "AGP Cockpit Bridge",
                "version": version,
            }
        ),
        encoding="utf-8",
    )
    (ext / "background.js").write_text("console.log('agp');\n", encoding="utf-8")
    (ext / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "test-build";\n', encoding="utf-8"
    )
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
    assert marker["build_id"] == "test-build"
    assert len(marker["sha256"]) == 64
    assert marker["download_directory"].endswith("/repo/Download")
    assert marker["run_next"].endswith("/repo/Download/run_next.py")


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


def test_stage_extension_prefers_repository_source_over_stale_bundled_app(monkeypatch, tmp_path):
    from agp_cockpit.adapters import macos_extension

    repo = tmp_path / "repo"
    _make_extension(repo, version="0.3.13")
    (repo / "chrome_extension" / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "source-build";\n', encoding="utf-8"
    )

    bundle = tmp_path / "bundle"
    _make_extension(bundle, version="0.3.12")
    (bundle / "chrome_extension" / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "stale-bundle";\n', encoding="utf-8"
    )
    monkeypatch.setattr(macos_extension.sys, "_MEIPASS", str(bundle), raising=False)

    support = tmp_path / "support"
    monkeypatch.setattr(macos_extension, "settings_path", lambda: support / "settings.json")

    staged = macos_extension.stage_extension(repo)
    marker = json.loads((staged / ".agp-stage.json").read_text(encoding="utf-8"))

    assert json.loads((staged / "manifest.json").read_text(encoding="utf-8"))["version"] == "0.3.13"
    assert (staged / "build_identity.js").read_text(encoding="utf-8").strip().endswith('"source-build";')
    assert marker["version"] == "0.3.13"
    assert marker["build_id"] == "source-build"
    assert marker["source_extension"] == str((repo / "chrome_extension").resolve())


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


def test_macos_app_bundle_version_comes_from_runtime_version():
    spec = Path("packaging/macos/agp_cockpit.spec").read_text(encoding="utf-8")

    assert "def _app_version()" in spec
    assert 'version=_app_version()' in spec
    assert 'version="0.1.0' not in spec


def test_an_older_checkout_gives_way_to_the_running_apps_extension(monkeypatch, tmp_path):
    """AGP_EXTENSION_MATCHES_RUNNING_APP_V1 (live 2026-10-26): checkout on main (release-0.3.3), app
    built from a fix branch (release-0.3.3-r1): the staged extension must be the app's own."""
    from agp_cockpit import version
    from agp_cockpit.adapters import macos_extension

    repo, bundle = tmp_path / "repo", tmp_path / "bundle"
    _make_extension(repo, version="0.3.3")
    (repo / "chrome_extension" / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "release-0.3.3";\n', encoding="utf-8")
    _make_extension(bundle, version="0.3.3")
    (bundle / "chrome_extension" / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "release-0.3.3-r7";\n', encoding="utf-8")
    monkeypatch.setattr(macos_extension.sys, "_MEIPASS", str(bundle), raising=False)
    monkeypatch.setattr(version, "BRIDGE_BUILD_ID", "release-0.3.3-r7")   # not the checkout's own
    assert macos_extension.packaged_extension_source(repo) == bundle / "chrome_extension"
    # a checkout newer than the app still wins (the stale-app guard then asks for a rebuild)
    (repo / "chrome_extension" / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "release-0.3.3-r8";\n', encoding="utf-8")
    assert macos_extension.packaged_extension_source(repo) == (repo / "chrome_extension").resolve()
