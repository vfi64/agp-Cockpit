"""Rebuild and restart the Cockpit from the Cockpit itself (AGP_REBUILD_BUTTON_V1).

Owner 2026-10-05: after every slice the owner typed
``.venv/bin/python scripts/build_macos_app.py --restart`` in a terminal while the
stale-app guard (AGP_STALE_APP_GUARD_V1) already knew that a newer build was on
disk. The guard's warning line now offers the same step as a button. The app
runs the project's own build script (without ``--restart``; log file in
``.local/agp-cockpit/logs``) and watches it. Only after a successful build, and
only while no task runs, it starts a detached relauncher (waits for this process
to end, then opens the bundle) and closes itself the normal way (bridge stopped).
No Apple Event is sent, a failed build leaves the app running and the log names
the cause. The extension follows by itself: the bridge asks it to reload when its
build differs (AGP_EXTENSION_AUTO_REFRESH_V2, live 2026-10-05: r1 → r2 within two
seconds of the restart).
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.build_freshness import BuildFreshness
from agp_cockpit.core.ci_gate import tool_env

BUILD = "build"
RESTART = "restart"
SCRIPT = Path("scripts/build_macos_app.py")
# Variables a frozen (PyInstaller) app passes to its children; the project's own
# interpreter must not inherit them.
_FROZEN_ENV_PREFIXES = ("_PYI", "_MEI", "PYINSTALLER")
_FROZEN_ENV_KEYS = ("PYTHONHOME", "PYTHONPATH", "DYLD_LIBRARY_PATH", "DYLD_FRAMEWORK_PATH",
                    # Live 2026-10-06 (first button run): the frozen app's tkinter runtime hook
                    # points TCL_LIBRARY/TK_LIBRARY into its own bundle; PyInstaller then took
                    # the Tcl data from the bundle it was about to delete („Resource …/dist/AGP
                    # Cockpit.app/Contents/Frameworks/_tcl_data/auto.tcl is not a valid file“).
                    "TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH", "TIX_LIBRARY")


def offer(freshness: BuildFreshness | None) -> str:
    """BUILD when the source is newer than the running app, RESTART when only the
    bundle on disk is newer, "" when nothing is stale."""
    if freshness is None or not freshness.stale:
        return ""
    if freshness.bundle and freshness.bundle != freshness.running and \
            (not freshness.source or freshness.source == freshness.bundle):
        return RESTART
    return BUILD


def label(kind: str) -> str:
    return {BUILD: "Neu bauen und neu starten", RESTART: "Neu starten"}.get(kind, "")


def python_of(home: Path) -> Path:
    return Path(home) / ".venv" / "bin" / "python"


def bundle_of(home: Path) -> Path:
    return Path(home) / ".local" / "agp-cockpit" / "dist" / "AGP Cockpit.app"


def command(home: Path) -> list[str]:
    """Build only; the app relaunches itself after a successful build."""
    return [str(python_of(home)), str(Path(home) / SCRIPT)]


# Waits until the given pid is gone, then opens the bundle (macOS ``open``).
RELAUNCH_SCRIPT = 'while kill -0 "$1" 2>/dev/null; do sleep 0.5; done; exec open "$2"'


def relaunch_command(app: Path, pid: int) -> list[str]:
    return ["/bin/sh", "-c", RELAUNCH_SCRIPT, "agp-relaunch", str(int(pid)), str(app)]


def relaunch(home: Path, pid: int, *, popen=subprocess.Popen):
    """Start the detached relauncher; the caller then closes the app."""
    app = bundle_of(home)
    if not (app / "Contents" / "MacOS" / "AGP Cockpit").is_file():
        raise FileNotFoundError(f"kein App-Bundle: {app}")
    return popen(relaunch_command(app, pid), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                 stderr=subprocess.DEVNULL, start_new_session=True, env=child_env(home))


def block_reason(home: Path | None, *, task_running: bool, kind: str = BUILD) -> str:
    if task_running:
        return "Ein Task läuft — erst nach seinem Ende neu starten (der Neustart beendet die App)."
    if home is None:
        return "Der Cockpit-Checkout ist nicht bekannt; bitte im Terminal neu bauen."
    if kind == RESTART:
        return "" if bundle_of(home).is_dir() else f"Kein App-Bundle unter {bundle_of(home)}."
    if not python_of(home).is_file():
        return f"Kein Python im Cockpit-Checkout ({python_of(home)}); bitte im Terminal neu bauen."
    if not (Path(home) / SCRIPT).is_file():
        return f"Das Build-Skript fehlt ({Path(home) / SCRIPT})."
    return ""


def child_env(home: Path, base: dict | None = None) -> dict:
    env = {key: value for key, value in dict(os.environ if base is None else base).items()
           if not key.startswith(_FROZEN_ENV_PREFIXES) and key not in _FROZEN_ENV_KEYS}
    return tool_env(Path(home), env)


@dataclass
class Rebuild:
    kind: str
    log: Path
    process: object

    def returncode(self):
        return self.process.poll()

    def tail(self, lines: int = 6) -> str:
        try:
            text = self.log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return "\n".join(text.strip().splitlines()[-lines:])

    def cause(self, limit: int = 160) -> str:
        """The first exception line of the log (the root cause, not the wrapper)."""
        try:
            text = self.log.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        for line in text.splitlines():
            if _CAUSE.match(line.strip()):
                line = line.strip()
                return line if len(line) <= limit else line[:limit].rsplit(" ", 1)[0] + " …"
        return ""


_CAUSE = __import__("re").compile(r"^[A-Za-z_.]*(Error|Exception)\b.*:")


def start(home: Path, kind: str = BUILD, *, popen=subprocess.Popen, now=time.strftime) -> Rebuild:
    home = Path(home)
    logs = home / ".local" / "agp-cockpit" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log = logs / f"rebuild-{now('%Y%m%d-%H%M%S')}.log"
    handle = open(log, "w", encoding="utf-8")  # noqa: SIM115 - the child owns the handle
    try:
        process = popen(command(home), cwd=str(home), env=child_env(home), stdin=subprocess.DEVNULL,
                        stdout=handle, stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        handle.close()
    return Rebuild(kind, log, process)
