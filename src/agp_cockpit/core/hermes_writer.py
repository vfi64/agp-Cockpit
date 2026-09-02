from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tempfile
from typing import Any

import yaml

from agp_cockpit.core.hermes_config import HermesConfigInfo, read_hermes_config


@dataclass(frozen=True)
class HermesWriteResult:
    path: Path
    backup_path: Path
    old_model: str
    new_model: str
    verified: bool


def _set_path(data: Any, path: tuple[str, ...], value: str) -> None:
    if not path:
        raise ValueError("empty model path")
    current = data
    for key in path[:-1]:
        if not isinstance(current, dict) or key not in current:
            raise ValueError(f"model path disappeared before write: {path}")
        current = current[key]
    if not isinstance(current, dict) or path[-1] not in current:
        raise ValueError(f"model field disappeared before write: {path}")
    current[path[-1]] = value


def update_hermes_model(new_model: str, *, path: Path) -> HermesWriteResult:
    new_model = new_model.strip()
    if not new_model:
        raise ValueError("new model must not be empty")

    before = read_hermes_config(path)
    if not before.exists:
        raise FileNotFoundError(path)
    if before.error:
        raise ValueError(before.error)
    if before.model is None or before.model_path is None:
        raise ValueError("Hermes model field is not uniquely recognized; refusing write")

    original_bytes = path.read_bytes()
    data = yaml.safe_load(original_bytes.decode("utf-8"))
    _set_path(data, before.model_path, new_model)

    backup_path = path.with_name(path.name + ".agp-cockpit.bak")
    backup_path.write_bytes(original_bytes)

    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    temp_path = Path(temp_name)

    try:
        with open(fd, "w", encoding="utf-8", closefd=True) as handle:
            yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True)
        temp_path.replace(path)

        after = read_hermes_config(path)
        if after.error or after.model != new_model or after.model_path != before.model_path:
            raise RuntimeError("post-write verification failed; restoring original config")

        return HermesWriteResult(
            path=path,
            backup_path=backup_path,
            old_model=before.model,
            new_model=new_model,
            verified=True,
        )
    except Exception:
        path.write_bytes(original_bytes)
        raise
    finally:
        if temp_path.exists():
            temp_path.unlink()


def restore_hermes_backup(*, path: Path, backup_path: Path | None = None) -> HermesConfigInfo:
    backup = backup_path or path.with_name(path.name + ".agp-cockpit.bak")
    if not backup.exists():
        raise FileNotFoundError(backup)
    path.write_bytes(backup.read_bytes())
    restored = read_hermes_config(path)
    if restored.error:
        raise RuntimeError(f"backup restore verification failed: {restored.error}")
    return restored
