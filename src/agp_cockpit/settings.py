from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Any


SETTINGS_SCHEMA_VERSION = 1


class SettingsError(RuntimeError):
    pass


@dataclass(frozen=True)
class AppSettings:
    schema_version: int = SETTINGS_SCHEMA_VERSION
    bridge_host: str = "127.0.0.1"
    bridge_port: int = 8765
    max_rounds: int = 8
    diagnostics_enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_v0(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SETTINGS_SCHEMA_VERSION,
        "bridge_host": data.get("bridge_host", data.get("host", "127.0.0.1")),
        "bridge_port": data.get("bridge_port", data.get("port", 8765)),
        "max_rounds": data.get("max_rounds", 8),
        "diagnostics_enabled": data.get("diagnostics_enabled", True),
    }


def migrate_settings_dict(data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    raw_version = data.get("schema_version", 0)
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise SettingsError("settings schema_version must be an integer")
    if raw_version > SETTINGS_SCHEMA_VERSION:
        raise SettingsError(
            f"settings schema {raw_version} is newer than supported "
            f"schema {SETTINGS_SCHEMA_VERSION}"
        )
    if raw_version == 0:
        return _coerce_v0(data), True
    if raw_version == SETTINGS_SCHEMA_VERSION:
        return dict(data), False
    raise SettingsError(f"unsupported settings schema {raw_version}")


def _validated(data: dict[str, Any]) -> AppSettings:
    host = data.get("bridge_host", "127.0.0.1")
    port = data.get("bridge_port", 8765)
    max_rounds = data.get("max_rounds", 8)
    diagnostics_enabled = data.get("diagnostics_enabled", True)

    if not isinstance(host, str) or not host.strip():
        raise SettingsError("bridge_host must be a non-empty string")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise SettingsError("bridge_port must be an integer between 1 and 65535")
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 1:
        raise SettingsError("max_rounds must be a positive integer")
    if not isinstance(diagnostics_enabled, bool):
        raise SettingsError("diagnostics_enabled must be boolean")

    return AppSettings(
        schema_version=SETTINGS_SCHEMA_VERSION,
        bridge_host=host.strip(),
        bridge_port=port,
        max_rounds=max_rounds,
        diagnostics_enabled=diagnostics_enabled,
    )


def load_settings(path: Path) -> tuple[AppSettings, bool]:
    path = path.expanduser()
    if not path.exists():
        return AppSettings(), False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SettingsError(f"cannot read settings: {exc}") from exc
    if not isinstance(raw, dict):
        raise SettingsError("settings document must be a JSON object")
    migrated, changed = migrate_settings_dict(raw)
    return _validated(migrated), changed


def save_settings(path: Path, settings: AppSettings) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(
        json.dumps(settings.to_dict(), indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temp.replace(path)


def load_and_migrate_settings(path: Path) -> tuple[AppSettings, bool]:
    settings, migrated = load_settings(path)
    if migrated:
        save_settings(path, settings)
    return settings, migrated
