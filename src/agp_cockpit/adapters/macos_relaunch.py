"""Restart the Cockpit after a repository switch (AGP_REPOSITORY_SWITCH_V1).

The new instance starts after a short delay so the old one can stop its
bridge first; it reads the switched repository from the settings.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

DELAY_SECONDS = 3


def relaunch_command(*, frozen: bool, executable: str, delay: int = DELAY_SECONDS) -> list[str]:
    exe = Path(executable).resolve()
    if frozen:
        app = next((p for p in exe.parents if p.suffix == ".app"), None)
        if app is None:
            raise RuntimeError(f"app bundle of {exe} not found")
        start = f"/usr/bin/open -n {shlex.quote(str(app))}"
    else:
        start = f"{shlex.quote(str(exe))} -m agp_cockpit"
    return ["/bin/sh", "-c", f"sleep {int(delay)}; {start}"]


def schedule_relaunch(*, popen=subprocess.Popen) -> list[str]:
    command = relaunch_command(frozen=bool(getattr(sys, "frozen", False)), executable=sys.executable)
    popen(command, start_new_session=True, stdin=subprocess.DEVNULL,
          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return command
