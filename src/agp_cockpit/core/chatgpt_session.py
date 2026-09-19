from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from agp_cockpit.core.browser_transport import discover_chrome

CHATGPT_HOSTS = {
    "chatgpt.com",
    "www.chatgpt.com",
    "chat.openai.com",
}


@dataclass(frozen=True)
class ChromeTabRef:
    window_index: int
    tab_index: int
    title: str
    url: str

    @property
    def host(self) -> str:
        return (urlparse(self.url).hostname or "").casefold()

    @property
    def is_chatgpt(self) -> bool:
        return self.host in CHATGPT_HOSTS


@dataclass(frozen=True)
class ChatGPTResolution:
    action: str
    tabs_found: tuple[ChromeTabRef, ...]
    selected: ChromeTabRef | None
    ready_for_user: bool
    note: str



def _osascript(script: str):
    from agp_cockpit.adapters.macos_chatgpt import run_osascript
    return run_osascript(script)

def chrome_running() -> bool:
    completed = _osascript(
        'tell application "System Events" to return exists process "Google Chrome"'
    )
    if completed.returncode != 0:
        return False
    return completed.stdout.strip().casefold() == "true"


def list_chrome_tabs() -> tuple[ChromeTabRef, ...]:
    if not chrome_running():
        return ()

    script = """
tell application "Google Chrome"
    set output to ""
    repeat with wi from 1 to count of windows
        set w to window wi
        repeat with ti from 1 to count of tabs of w
            set t to tab ti of w
            set output to output & wi & tab & ti & tab & (title of t) & tab & (URL of t) & linefeed
        end repeat
    end repeat
    return output
end tell
"""
    completed = _osascript(script)
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "Chrome-Tabs konnten nicht gelesen werden"
        )

    tabs = []
    for line in completed.stdout.splitlines():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        try:
            wi = int(parts[0])
            ti = int(parts[1])
        except ValueError:
            continue
        tabs.append(
            ChromeTabRef(
                window_index=wi,
                tab_index=ti,
                title=parts[2],
                url=parts[3],
            )
        )
    return tuple(tabs)


def activate_tab(tab: ChromeTabRef) -> None:
    script = f"""
tell application "Google Chrome"
    activate
    set active tab index of window {tab.window_index} to {tab.tab_index}
    set index of window {tab.window_index} to 1
end tell
"""
    completed = _osascript(script)
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "ChatGPT-Tab konnte nicht aktiviert werden"
        )


def open_chatgpt() -> None:
    chrome = discover_chrome()
    if not chrome.installed:
        raise RuntimeError("Google Chrome wurde nicht gefunden")

    from agp_cockpit.adapters.macos_chatgpt import open_chatgpt_in_chrome
    completed = open_chatgpt_in_chrome()
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip()
            or "ChatGPT konnte nicht in Chrome geöffnet werden"
        )


def resolve_chatgpt_session() -> ChatGPTResolution:
    chrome = discover_chrome()
    if not chrome.installed:
        return ChatGPTResolution(
            action="blocked",
            tabs_found=(),
            selected=None,
            ready_for_user=False,
            note="Google Chrome ist nicht installiert.",
        )

    if not chrome_running():
        open_chatgpt()
        return ChatGPTResolution(
            action="opened-chatgpt",
            tabs_found=(),
            selected=None,
            ready_for_user=False,
            note=(
                "Chrome wurde mit ChatGPT geöffnet. "
                "Bitte ggf. anmelden und den gewünschten Chat öffnen."
            ),
        )

    tabs = tuple(
        tab for tab in list_chrome_tabs()
        if tab.is_chatgpt
    )

    if not tabs:
        open_chatgpt()
        return ChatGPTResolution(
            action="opened-chatgpt",
            tabs_found=(),
            selected=None,
            ready_for_user=False,
            note=(
                "Kein ChatGPT-Tab war geöffnet. "
                "ChatGPT wurde in Chrome geöffnet."
            ),
        )

    if len(tabs) == 1:
        activate_tab(tabs[0])
        return ChatGPTResolution(
            action="activated-existing",
            tabs_found=tabs,
            selected=tabs[0],
            ready_for_user=True,
            note=(
                "Vorhandener ChatGPT-Tab wurde aktiviert. "
                "Login-/Chatbereitschaft bitte visuell prüfen."
            ),
        )

    return ChatGPTResolution(
        action="multiple-candidates",
        tabs_found=tabs,
        selected=None,
        ready_for_user=False,
        note=(
            "Mehrere ChatGPT-Tabs gefunden. "
            "Bitte Zielchat auswählen."
        ),
    )
