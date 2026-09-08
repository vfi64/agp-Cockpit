from __future__ import annotations

import json

from agp_cockpit.settings import SETTINGS_SCHEMA_VERSION, AppSettings, load_and_migrate_settings


def test_v1_settings_migrate_to_v2_with_repository_root(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({
            "schema_version": 1,
            "bridge_host": "127.0.0.1",
            "bridge_port": 8765,
            "max_rounds": 8,
            "diagnostics_enabled": True,
        }),
        encoding="utf-8",
    )
    settings, migrated = load_and_migrate_settings(path)
    assert migrated is True
    assert settings.schema_version == SETTINGS_SCHEMA_VERSION == 2
    assert settings.repository_root is None
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == 2
    assert persisted["repository_root"] is None


def test_repository_root_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    root = tmp_path / "repo"
    settings = AppSettings(repository_root=str(root))
    from agp_cockpit.settings import save_settings, load_settings
    save_settings(path, settings)
    loaded, migrated = load_settings(path)
    assert migrated is False
    assert loaded.repository_root == str(root)
