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


HANDSHAKE_MAX_AGE_SECONDS = 180.0


def connected_chat_url(runtime_root=None, *, max_age: float = HANDSHAKE_MAX_AGE_SECONDS,
                       now: float | None = None) -> str:
    """The ChatGPT page of the connected extension (fresh handshake), or "".

    The extension reports its page about once a minute; this is the chat the
    Cockpit actually talks to, independent of which Chrome tab is in front.
    """
    import json
    import math
    import time
    from pathlib import Path

    if runtime_root is None:
        from agp_cockpit.adapters.macos_settings import bridge_runtime_root
        runtime_root = bridge_runtime_root()
    try:
        handshake = json.loads((Path(runtime_root) / "extension.json").read_text(encoding="utf-8"))
        stamp = float(handshake.get("timestamp_unix", 0.0))
    except (OSError, ValueError, TypeError, AttributeError):
        return ""
    current = time.time() if now is None else now
    url = str(handshake.get("page_url", ""))
    if not math.isfinite(stamp) or current - stamp > max_age or not classify_target(url).allowed:
        return ""
    return url


def focus_chat_tab(url: str) -> bool:
    """Bring the Chrome tab with exactly this URL to the front (best effort)."""
    quoted = url.replace("\\", "\\\\").replace('"', '\\"')
    script = (
        'tell application "Google Chrome"\n'
        '  repeat with w in windows\n'
        '    repeat with i from 1 to count of tabs of w\n'
        f'      if URL of tab i of w is "{quoted}" then\n'
        '        set active tab index of w to i\n'
        '        set index of w to 1\n'
        '        activate\n'
        '        return "ok"\n'
        '      end if\n'
        '    end repeat\n'
        '  end repeat\n'
        '  return "missing"\n'
        'end tell'
    )
    try:
        completed = _run_osascript(script)
    except Exception:  # noqa: BLE001 - focusing is best effort
        return False
    return completed.returncode == 0 and completed.stdout.strip() == "ok"


def require_allowed_active_chat(runtime_root=None) -> ChromeTarget:
    """The ChatGPT chat to start in.

    AGP_CONNECTED_CHAT_TARGET_V1 (live 2026-10-03): the front Chrome tab was
    chrome://extensions while the extension's ChatGPT tab was connected and
    fresh; the start was blocked until the owner reloaded the chat by hand.
    The front tab is preferred; otherwise the chat of the fresh extension
    handshake is used and brought to the front.
    """
    try:
        target = classify_target(active_chrome_url())
        active_note = target.url or "<leer>"
    except Exception as exc:  # noqa: BLE001 - fall back to the connected chat
        target = None
        active_note = str(exc)
    if target is not None and target.allowed:
        return target
    connected = connected_chat_url(runtime_root)
    if not connected:
        raise PermissionError(
            "Aktiver Chrome-Tab ist kein freigegebenes ChatGPT-Ziel: "
            f"{active_note} — und keine verbundene ChatGPT-Seite der Erweiterung "
            "(Handshake älter als 3 Minuten). ChatGPT-Tab öffnen oder neu laden."
        )
    focus_chat_tab(connected)
    return classify_target(connected)


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
