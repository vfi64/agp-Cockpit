from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


ALLOWED_CHAT_HOSTS = {
    "chatgpt.com",
    "www.chatgpt.com",
    "chat.openai.com",
}


@dataclass(frozen=True)
class ChromeTarget:
    url: str
    host: str
    allowed: bool



def _run_osascript(script: str):
    from agp_cockpit.adapters.macos_chatgpt import run_osascript
    return run_osascript(script)

def active_chrome_url() -> str:
    script = (
        'tell application "Google Chrome"\n'
        'if not running then error "Google Chrome is not running"\n'
        'if (count of windows) = 0 then error "Google Chrome has no window"\n'
        'return URL of active tab of front window\n'
        'end tell'
    )
    completed = _run_osascript(script)
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "Aktive Chrome-URL konnte nicht gelesen werden"
        )
    return completed.stdout.strip()


def classify_target(url: str) -> ChromeTarget:
    parsed = urlparse(url)
    host = (parsed.hostname or "").casefold()
    allowed = (
        parsed.scheme == "https"
        and host in ALLOWED_CHAT_HOSTS
    )
    return ChromeTarget(
        url=url,
        host=host,
        allowed=allowed,
    )


def require_allowed_active_chat() -> ChromeTarget:
    target = classify_target(active_chrome_url())
    if not target.allowed:
        raise PermissionError(
            "Aktiver Chrome-Tab ist kein freigegebenes ChatGPT-Ziel: "
            f"{target.url or '<leer>'}"
        )
    return target


def paste_and_send_active_chat() -> ChromeTarget:
    target = require_allowed_active_chat()

    script = (
        'tell application "Google Chrome" to activate\n'
        'delay 0.2\n'
        'tell application "System Events"\n'
        'keystroke "v" using command down\n'
        'delay 0.15\n'
        'key code 36\n'
        'end tell'
    )

    completed = _run_osascript(script)
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or (
                "Paste/Send fehlgeschlagen. "
                "Prüfe die macOS-Bedienungshilfen für Terminal/Python."
            )
        )

    return target
