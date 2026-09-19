from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SETTINGS_SCHEMA_VERSION = 2


class SettingsError(RuntimeError):
    pass


@dataclass(frozen=True)
class AppSettings:
    schema_version: int = SETTINGS_SCHEMA_VERSION
    bridge_host: str = "127.0.0.1"
    bridge_port: int = 8765
    max_rounds: int = 8
    diagnostics_enabled: bool = True
    repository_root: str | None = None
    allowed_effects: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    allow_network: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _coerce_v0(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
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

    current = dict(data)
    changed = False
    if raw_version == 0:
        current = _coerce_v0(current)
        raw_version = 1
        changed = True
    if raw_version == 1:
        current["schema_version"] = 2
        current.setdefault("repository_root", None)
        current.setdefault("allowed_effects", [])
        current.setdefault("allowed_tools", [])
        current.setdefault("allow_network", False)
        raw_version = 2
        changed = True
    if raw_version != SETTINGS_SCHEMA_VERSION:
        raise SettingsError(f"unsupported settings schema {raw_version}")
    return current, changed


def _validated(data: dict[str, Any]) -> AppSettings:
    host = data.get("bridge_host", "127.0.0.1")
    port = data.get("bridge_port", 8765)
    max_rounds = data.get("max_rounds", 8)
    diagnostics_enabled = data.get("diagnostics_enabled", True)
    repository_root = data.get("repository_root")
    allowed_effects = data.get("allowed_effects", [])
    allowed_tools = data.get("allowed_tools", [])
    allow_network = data.get("allow_network", False)

    if not isinstance(host, str) or not host.strip():
        raise SettingsError("bridge_host must be a non-empty string")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise SettingsError("bridge_port must be an integer between 1 and 65535")
    if isinstance(max_rounds, bool) or not isinstance(max_rounds, int) or max_rounds < 1:
        raise SettingsError("max_rounds must be a positive integer")
    if not isinstance(diagnostics_enabled, bool):
        raise SettingsError("diagnostics_enabled must be boolean")
    if repository_root is not None and (
        not isinstance(repository_root, str) or not repository_root.strip()
    ):
        raise SettingsError("repository_root must be null or a non-empty string")
    if not isinstance(allowed_effects, (list, tuple)) or any(not isinstance(x, str) or not x for x in allowed_effects):
        raise SettingsError("allowed_effects must contain non-empty strings")
    if not isinstance(allowed_tools, (list, tuple)) or any(not isinstance(x, str) or not x for x in allowed_tools):
        raise SettingsError("allowed_tools must contain non-empty strings")
    if not isinstance(allow_network, bool):
        raise SettingsError("allow_network must be boolean")

    return AppSettings(
        schema_version=SETTINGS_SCHEMA_VERSION,
        bridge_host=host.strip(),
        bridge_port=port,
        max_rounds=max_rounds,
        diagnostics_enabled=diagnostics_enabled,
        repository_root=repository_root.strip() if isinstance(repository_root, str) else None,
        allowed_effects=tuple(allowed_effects),
        allowed_tools=tuple(allowed_tools),
        allow_network=allow_network,
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
