from __future__ import annotations

import json

import pytest

from agp_cockpit.settings import (
    SETTINGS_SCHEMA_VERSION,
    AppSettings,
    SettingsError,
    load_and_migrate_settings,
    load_settings,
    save_settings,
)


def test_missing_settings_returns_defaults(tmp_path):
    settings, migrated = load_settings(tmp_path / "settings.json")
    assert settings == AppSettings()
    assert migrated is False


def test_legacy_v0_settings_are_migrated_atomically(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"host": "127.0.0.1", "port": 9000, "max_rounds": 3}),
        encoding="utf-8",
    )
    settings, migrated = load_and_migrate_settings(path)
    assert migrated is True
    assert settings.bridge_port == 9000
    assert settings.max_rounds == 3
    written = json.loads(path.read_text(encoding="utf-8"))
    assert written["schema_version"] == SETTINGS_SCHEMA_VERSION
    assert "host" not in written
    assert "port" not in written


def test_current_settings_round_trip(tmp_path):
    path = tmp_path / "settings.json"
    expected = AppSettings(bridge_port=9100, max_rounds=4, diagnostics_enabled=False)
    save_settings(path, expected)
    actual, migrated = load_settings(path)
    assert actual == expected
    assert migrated is False
    assert not path.with_suffix(".json.tmp").exists()


def test_future_schema_fails_closed(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(SettingsError, match="newer than supported"):
        load_settings(path)


@pytest.mark.parametrize("port", [0, 65536, True, "8765"])
def test_invalid_ports_fail_closed(tmp_path, port):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"schema_version": 1, "bridge_port": port}),
        encoding="utf-8",
    )
    with pytest.raises(SettingsError, match="bridge_port"):
        load_settings(path)
