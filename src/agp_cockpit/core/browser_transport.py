from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


@dataclass(frozen=True)
class BrowserInfo:
    name: str
    app_path: Path | None

    @property
    def installed(self) -> bool:
        return self.app_path is not None


def discover_chrome() -> BrowserInfo:
    candidates = (
        Path("/Applications/Google Chrome.app"),
        Path.home() / "Applications/Google Chrome.app",
    )
    for candidate in candidates:
        if candidate.exists():
            return BrowserInfo("Google Chrome", candidate)
    return BrowserInfo("Google Chrome", None)


def focus_chrome() -> None:
    info = discover_chrome()
    if not info.installed:
        raise RuntimeError("Google Chrome wurde nicht gefunden")

    completed = subprocess.run(
        ["/usr/bin/open", "-a", "Google Chrome"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "Google Chrome konnte nicht fokussiert werden"
        )


def open_url_in_chrome(url: str) -> None:
    if not url.startswith(("https://", "http://")):
        raise ValueError("Nur http/https URLs sind zulässig")

    info = discover_chrome()
    if not info.installed:
        raise RuntimeError("Google Chrome wurde nicht gefunden")

    completed = subprocess.run(
        ["/usr/bin/open", "-a", "Google Chrome", url],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "URL konnte nicht in Chrome geöffnet werden"
        )
