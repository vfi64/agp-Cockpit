from __future__ import annotations

from dataclasses import dataclass
import subprocess
from agp_cockpit.core.browser_transport import discover_chrome


def run_chrome_automation(script: str) -> tuple[bool, str]:
    """Bound optional browser navigation; never replay failed automation."""
    try:
        completed = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "Chrome automation timed out after 10 seconds."
    except OSError as exc:
        return False, f"Chrome automation unavailable: {exc}"[:500]
    if completed.returncode != 0:
        return False, (completed.stderr.strip() or f"Chrome automation exited {completed.returncode}.")[:500]
    return True, completed.stdout.strip()


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
