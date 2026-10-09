"""AGP_VERSION_MAP_V1/V2: one version mapping, kept consistent by tests.

V2 (owner 2026-10-04): `agentic-kit release prepare --write` appends the row
(.agentic/config.yaml release.version_anchors, Kit 1.0.16). The row's build id is
the release build `release-<app>`; rebuilds between releases carry `-r<N>` in
BRIDGE_BUILD_ID. The extension version lives in the Chrome manifest only.
"""

import json
import re
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _rows():
    return json.loads((ROOT / "docs/releases/versions.json").read_text(encoding="utf-8"))["releases"]


def test_app_versions_agree_with_the_latest_release_row():
    from agp_cockpit.version import APP_VERSION, BRIDGE_BUILD_ID
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    build_js = (ROOT / "chrome_extension/build_identity.js").read_text(encoding="utf-8")
    rows = _rows()
    latest = rows[-1]
    assert pyproject == APP_VERSION
    if not re.search(r"(dev|rc|a|b)\d*$", APP_VERSION):     # a release version needs its row
        assert latest["app"] == APP_VERSION and latest["tag"] == f"v{APP_VERSION}"
        assert latest["build_id"] == f"release-{APP_VERSION}"
        assert re.fullmatch(re.escape(latest["build_id"]) + r"(-r\d+)?", BRIDGE_BUILD_ID), (
            "BRIDGE_BUILD_ID must be the release build or a rebuild of it; a release sets "
            f"src/agp_cockpit/version.py and chrome_extension/build_identity.js to {latest['build_id']}")
    assert f'"{BRIDGE_BUILD_ID}"' in build_js
    assert all(row["published"] is False for row in rows)
    assert all("extension" not in row for row in rows)


def test_extension_version_is_valid():
    manifest = json.loads((ROOT / "chrome_extension/manifest.json").read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+(\.\d+){1,3}", manifest["version"])


def test_changelog_has_a_section_per_release():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    for row in _rows():
        assert f"## {row['tag']} - {row['date']}" in changelog
    # Public repository since 2026-10-09; never published to a package index or archive.
    assert "no PyPI package and no Zenodo record" in changelog


def test_the_kit_owns_the_version_anchors():
    """The release route of KIT-GF-037: APP_VERSION and the appended row."""
    config = yaml.safe_load((ROOT / ".agentic/config.yaml").read_text(encoding="utf-8"))
    anchors = {a["path"]: a for a in config["release"]["version_anchors"]}
    assert anchors["src/agp_cockpit/version.py"] == {
        "kind": "source_constant", "path": "src/agp_cockpit/version.py",
        "name": "APP_VERSION", "label": "APP_VERSION"}
    table = anchors["docs/releases/versions.json"]
    assert (table["kind"], table["list"], table["version_field"], table["position"]) == (
        "json_table", "releases", "app", "append")
    assert table["row"]["build_id"] == "release-{version}"
    assert "extension" not in table["row"]
