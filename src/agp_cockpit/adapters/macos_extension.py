from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from agp_cockpit.adapters.macos_settings import settings_path


class ExtensionStagingError(RuntimeError):
    pass


def _manifest_version(source: Path) -> str:
    try:
        data = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
        version = data.get("version")
    except (OSError, json.JSONDecodeError) as exc:
        raise ExtensionStagingError(f"cannot read extension manifest: {exc}") from exc
    if not isinstance(version, str) or not version.strip():
        raise ExtensionStagingError("extension manifest has no valid version")
    return version.strip()


def _tree_digest(source: Path) -> str:
    digest = hashlib.sha256()
    files = sorted(
        p for p in source.rglob("*")
        if p.is_file() and ".bak" not in p.name
    )
    for path in files:
        digest.update(path.relative_to(source).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def packaged_extension_source(repository_root: Path) -> Path:
    candidates: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "chrome_extension")
    candidates.append(repository_root.expanduser().resolve() / "chrome_extension")
    for candidate in candidates:
        if (candidate / "manifest.json").is_file():
            return candidate
    raise ExtensionStagingError("AGP Cockpit Chrome extension assets are not available.")


def local_extension_root() -> Path:
    return settings_path().parent / "chrome_extension"


def stage_extension(repository_root: Path) -> Path:
    source = packaged_extension_source(repository_root)
    version = _manifest_version(source)
    digest = _tree_digest(source)

    target = local_extension_root()
    marker = target / ".agp-stage.json"
    if target.is_dir() and marker.is_file():
        try:
            current = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            current = {}
        if (
            current.get("version") == version
            and current.get("sha256") == digest
            and (target / "manifest.json").is_file()
        ):
            return target

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".chrome_extension-", dir=parent))
    backup = parent / ".chrome_extension.previous"
    try:
        for child in source.iterdir():
            if ".bak" in child.name:
                continue
            dest = tmp / child.name
            if child.is_dir():
                shutil.copytree(child, dest)
            else:
                shutil.copy2(child, dest)

        (tmp / ".agp-stage.json").write_text(
            json.dumps({"version": version, "sha256": digest}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if not (tmp / "manifest.json").is_file():
            raise ExtensionStagingError("staged extension is incomplete")

        if backup.exists():
            shutil.rmtree(backup)
        if target.exists():
            os.replace(target, backup)
        os.replace(tmp, target)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        if not target.exists() and backup.exists():
            os.replace(backup, target)
        raise

    return target
