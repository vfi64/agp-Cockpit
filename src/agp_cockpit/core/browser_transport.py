from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.ports import BrowserPort


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



def focus_chrome(port: BrowserPort | None = None) -> None:
    browser = port or _default_browser_port()
    if not browser.installed():
        raise RuntimeError("Google Chrome wurde nicht gefunden")
    browser.focus()

def open_url_in_chrome(url: str, port: BrowserPort | None = None) -> None:
    if not url.startswith(("https://", "http://")):
        raise ValueError("Nur http/https URLs sind zulässig")
    browser = port or _default_browser_port()
    if not browser.installed():
        raise RuntimeError("Google Chrome wurde nicht gefunden")
    browser.open_url(url)

def _default_browser_port() -> BrowserPort:
    from agp_cockpit.adapters.macos_browser import MacOSChromeBrowserPort
    return MacOSChromeBrowserPort()
