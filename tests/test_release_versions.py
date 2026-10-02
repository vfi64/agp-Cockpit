"""AGP_VERSION_MAP_V1: one version mapping, kept consistent by tests."""

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_app_versions_agree_with_the_latest_release_row():
    from agp_cockpit.version import APP_VERSION, BRIDGE_BUILD_ID
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    manifest = json.loads((ROOT / "chrome_extension/manifest.json").read_text(encoding="utf-8"))["version"]
    build_js = (ROOT / "chrome_extension/build_identity.js").read_text(encoding="utf-8")
    rows = json.loads((ROOT / "docs/releases/versions.json").read_text(encoding="utf-8"))["releases"]
    latest = rows[-1]
    assert pyproject == APP_VERSION
    if not re.search(r"(dev|rc|a|b)\d*$", APP_VERSION):     # a release version needs its row
        assert latest["app"] == APP_VERSION and latest["tag"] == f"v{APP_VERSION}"
        assert latest["extension"] == manifest and latest["build_id"] == BRIDGE_BUILD_ID
    assert f'"{BRIDGE_BUILD_ID}"' in build_js
    assert all(row["published"] is False for row in rows)


def test_changelog_has_a_section_per_release():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for row in json.loads((ROOT / "docs/releases/versions.json").read_text(encoding="utf-8"))["releases"]:
        assert f"## {row['tag']} - {row['date']}" in changelog
    assert "No GitHub Release" in changelog or "not published" in changelog
