"""Where the Cockpit keeps its runtime data (AGP_RUNTIME_HOME_V1, slice A3).

Live 2026-10-06 (P4, the Cockpit steering the Kit repository): bridge log, mission
state, Kit digest, delivery copies and work-order temp files were written into the
steered repository's ``.local/agp-cockpit``; the Kit's audits then scanned them
(KIT-GF-054) and the disk filled up. The runtime belongs to the Cockpit, not to the
repository it steers.

The app announces its own checkout in ``AGP_COCKPIT_RUNTIME_HOME`` at start. For the
Cockpit's own repository nothing moves; for every other repository the data lives in
``<home>/.local/agp-cockpit/repos/<name>-<hash>/``, one folder per steered repository.
Without the variable (tests, the CLI) the repository's own folder is used as before.
``Download/`` stays in the steered repository: it is part of the work-order contract.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

HOME_ENV = "AGP_COCKPIT_RUNTIME_HOME"


def runtime_base(repository_root: Path) -> Path:
    root = Path(repository_root).expanduser().resolve()
    home = os.environ.get(HOME_ENV, "").strip()
    if home:
        home_path = Path(home).expanduser().resolve()
        if home_path != root:
            digest = hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:8]
            return home_path / ".local" / "agp-cockpit" / "repos" / f"{root.name}-{digest}"
    return root / ".local" / "agp-cockpit"


def runtime_home_base() -> Path | None:
    """``<home>/.local/agp-cockpit`` of the announced runtime home, or None without one."""
    home = os.environ.get(HOME_ENV, "").strip()
    return Path(home).expanduser().resolve() / ".local" / "agp-cockpit" if home else None


def runtime_dir(repository_root: Path, *parts: str) -> Path:
    """``<runtime base>/<parts…>`` of ``repository_root`` (not created)."""
    return runtime_base(repository_root).joinpath(*parts)


def announce_home(repository_root: Path) -> Path | None:
    """Called once at app start: the Cockpit's own checkout becomes the runtime home."""
    from agp_cockpit.core.build_freshness import cockpit_home
    home = cockpit_home()
    if home is not None:
        os.environ[HOME_ENV] = str(home)
    return home
