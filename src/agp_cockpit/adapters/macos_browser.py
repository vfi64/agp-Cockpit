from __future__ import annotations

from dataclasses import dataclass
import subprocess
from agp_cockpit.core.browser_transport import discover_chrome

@dataclass(frozen=True)
class MacOSChromeBrowserPort:
    def installed(self) -> bool:
        return discover_chrome().installed

    def focus(self) -> None:
        completed = subprocess.run(["/usr/bin/open", "-a", "Google Chrome"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "Google Chrome konnte nicht fokussiert werden")

    def open_url(self, url: str) -> None:
        completed = subprocess.run(["/usr/bin/open", "-a", "Google Chrome", url], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "URL konnte nicht in Chrome geöffnet werden")
