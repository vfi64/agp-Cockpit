"""The installed Agentic Project Kit is the command authority.

AGP_KIT_INSTALLATION_AUTHORITY_V1 (plan P1 / R1, 2026-10-01): the command
digest used to come from ``docs/reference/agentic-kit-commands.json`` in the
repository. Foreign repositories do not carry that file, and in agp-Cockpit
the copy was stale (repository ``ce455b7df8c5`` vs. installed Kit
``ffae97536a52``). The manifest now comes from the Kit installation that
executes the commands for the active repository: ``<repo>/.venv/bin/agentic-kit``
or ``agentic-kit`` on the tool PATH. Its interpreter is asked for the packaged
manifest; the repository copy is only a fallback when no Kit is installed.

``AGP_COCKPIT_KIT_BINARY`` overrides discovery (a path, or ``none``).

AGP_KIT_RUNTIME_VERSION_V1 (owner 2026-10-25): in the Kit's own repository the Kit is an editable
install. Its package metadata keeps the version of the last ``pip install -e`` (1.1.4) while the
code that runs is the checkout's (1.1.5), and the Lage showed „Kit 1.1.4“. The version is now the
running package's ``agentic_project_kit.__version__`` (the metadata only as fallback); the
metadata version is kept as ``metadata_version``. The cache also follows the package's
``__init__.py``, so a pull that changes the version is seen without a restart.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

PROBE = (
    "import json, importlib.metadata as m\n"
    "from importlib import resources\n"
    "import agentic_project_kit as k\n"
    "r = resources.files('agentic_project_kit.reference').joinpath('agentic-kit-commands.json')\n"
    "meta = m.version('agentic-project-kit')\n"
    "print(json.dumps({'version': getattr(k, '__version__', '') or meta, 'metadata_version': meta,\n"
    "                  'package_init': getattr(k, '__file__', '') or '', 'manifest': str(r)}))\n"
)


@dataclass(frozen=True)
class KitInstallation:
    binary: Path
    version: str
    manifest_path: Path
    metadata_version: str = ""      # pip metadata; differs from version for a stale editable install
    package_init: str = ""

    def load_manifest(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))


_CACHE: dict[tuple, tuple[KitInstallation | None, tuple]] = {}


def _mtime(path: str) -> int:
    try:
        return Path(path).stat().st_mtime_ns if path else 0
    except OSError:
        return 0


def find_kit_binary(repository_root: Path) -> Path | None:
    override = os.environ.get("AGP_COCKPIT_KIT_BINARY", "").strip()
    if override:
        return None if override.lower() == "none" else Path(override)
    local = Path(repository_root) / ".venv" / "bin" / "agentic-kit"
    if local.is_file():
        return local
    from agp_cockpit.core.ci_gate import tool_env
    found = shutil.which("agentic-kit", path=tool_env(repository_root).get("PATH"))
    return Path(found) if found else None


def _interpreter(binary: Path) -> list[str] | None:
    try:
        first = binary.read_bytes()[:256].split(b"\n", 1)[0].decode("utf-8", "replace")
    except OSError:
        return None
    if not first.startswith("#!"):
        return None
    parts = first[2:].strip().split()
    return parts or None


def discover(repository_root: Path) -> KitInstallation | None:
    binary = find_kit_binary(repository_root)
    if binary is None or not binary.is_file():
        return None
    try:
        key = (str(binary.resolve()), binary.stat().st_mtime_ns)
    except OSError:
        return None
    cached = _CACHE.get(key)
    if cached is not None and all(_mtime(path) == stamp for path, stamp in cached[1]):
        return cached[0]
    result = None
    interpreter = _interpreter(binary)
    if interpreter:
        try:
            completed = subprocess.run([*interpreter, "-c", PROBE], capture_output=True, text=True,
                                       timeout=30, check=False)
            data = json.loads(completed.stdout.strip().splitlines()[-1]) if completed.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError, IndexError):
            data = None
        if isinstance(data, dict) and Path(str(data.get("manifest") or "")).is_file():
            result = KitInstallation(binary, str(data.get("version") or ""), Path(data["manifest"]),
                                     metadata_version=str(data.get("metadata_version") or ""),
                                     package_init=str(data.get("package_init") or ""))
    watched = ((result.package_init, _mtime(result.package_init)),) if result and result.package_init else ()
    _CACHE[key] = (result, watched)
    return result
