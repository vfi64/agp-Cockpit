from __future__ import annotations

import plistlib
from pathlib import Path

import pytest

from agp_cockpit.adapters.macos_context import (
    looks_like_repository_context,
    resolve_repository_root,
)
from agp_cockpit.settings import AppSettings
from scripts.build_macos_app import verify_bundle


def make_repo(root: Path) -> Path:
    (root / "chrome_extension").mkdir(parents=True)
    (root / ".agentic").mkdir()
    return root


def test_context_resolution_prefers_explicit_root(tmp_path):
    explicit = make_repo(tmp_path / "explicit")
    saved = make_repo(tmp_path / "saved")
    root, source = resolve_repository_root(
        explicit_root=explicit,
        settings=AppSettings(repository_root=str(saved)),
        cwd=tmp_path,
    )
    assert root == explicit.resolve()
    assert source == "explicit"


def test_context_resolution_uses_saved_root(tmp_path):
    saved = make_repo(tmp_path / "saved")
    root, source = resolve_repository_root(
        explicit_root=None,
        settings=AppSettings(repository_root=str(saved)),
        cwd=tmp_path,
    )
    assert root == saved.resolve()
    assert source == "settings"


def test_context_resolution_can_use_chooser(tmp_path):
    selected = make_repo(tmp_path / "selected")
    root, source = resolve_repository_root(
        explicit_root=None,
        settings=AppSettings(),
        cwd=tmp_path,
        chooser=lambda: str(selected),
    )
    assert root == selected.resolve()
    assert source == "chooser"


def test_repository_context_requires_extension_and_agentic(tmp_path):
    assert not looks_like_repository_context(tmp_path)
    (tmp_path / "chrome_extension").mkdir()
    assert not looks_like_repository_context(tmp_path)
    (tmp_path / ".agentic").mkdir()
    assert looks_like_repository_context(tmp_path)


def test_verify_bundle_checks_native_structure(tmp_path):
    app = tmp_path / "AGP Cockpit.app"
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Resources").mkdir()
    (contents / "MacOS" / "AGP Cockpit").write_text("binary", encoding="utf-8")
    (contents / "Info.plist").write_bytes(
        plistlib.dumps({"CFBundleIdentifier": "de.vfi64.agp-cockpit", "CFBundleName": "AGP Cockpit"})
    )
    report = verify_bundle(app)
    assert report["bundle_identifier"] == "de.vfi64.agp-cockpit"


def test_verify_bundle_rejects_wrong_identifier(tmp_path):
    app = tmp_path / "AGP Cockpit.app"
    contents = app / "Contents"
    (contents / "MacOS").mkdir(parents=True)
    (contents / "Resources").mkdir()
    (contents / "MacOS" / "AGP Cockpit").write_text("binary", encoding="utf-8")
    (contents / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "wrong"}))
    with pytest.raises(RuntimeError, match="bundle identifier"):
        verify_bundle(app)
