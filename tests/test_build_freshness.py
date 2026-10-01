"""AGP_STALE_APP_GUARD_V1: an outdated running app refuses to start tasks."""
from __future__ import annotations

from agp_cockpit.core import build_freshness as bf


def repo(tmp_path, *, bundle=None, source=None):
    if bundle is not None:
        path = tmp_path / bf.BUNDLE_ID_FILE
        path.parent.mkdir(parents=True)
        path.write_text(f'globalThis.AGP_EXTENSION_BUILD_ID = "{bundle}";\n')
    if source is not None:
        path = tmp_path / bf.SOURCE_ID_FILE
        path.parent.mkdir(parents=True)
        path.write_text(f'BRIDGE_BUILD_ID = "{source}"\n')
    return tmp_path


def test_packaged_app_older_than_the_bundle_on_disk_is_stale(tmp_path):
    result = bf.check(repo(tmp_path, bundle="new", source="new"), running="old", frozen=True)
    assert result.stale and "Neuer Build vorhanden (new)" in result.message


def test_source_newer_than_the_running_app_is_stale(tmp_path):
    result = bf.check(repo(tmp_path, bundle="old", source="new"), running="old", frozen=True)
    assert result.stale and "neu bauen" in result.message


def test_a_run_from_source_ignores_an_older_bundle(tmp_path):
    assert not bf.check(repo(tmp_path, bundle="older", source="cur"), running="cur", frozen=False).stale


def test_current_build_starts_and_missing_files_do_not_block(tmp_path):
    assert not bf.check(repo(tmp_path, bundle="cur", source="cur"), running="cur", frozen=True).stale
    assert not bf.check(tmp_path, running="cur", frozen=True).stale


def test_start_block_reason_names_the_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(bf.sys, "frozen", True, raising=False)
    root = repo(tmp_path, bundle="other-build", source=bf.BRIDGE_BUILD_ID)
    assert bf.start_block_reason(root).startswith("Blockiert — Neuer Build vorhanden")
