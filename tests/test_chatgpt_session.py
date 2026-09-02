from pathlib import Path

import agp_cockpit.core.chatgpt_session as session
from agp_cockpit.core.browser_transport import BrowserInfo


def installed():
    return BrowserInfo(
        "Google Chrome",
        Path("/Applications/Google Chrome.app"),
    )


def test_no_chrome_blocks(monkeypatch):
    monkeypatch.setattr(
        session,
        "discover_chrome",
        lambda: BrowserInfo("Google Chrome", None),
    )
    result = session.resolve_chatgpt_session()
    assert result.action == "blocked"


def test_not_running_opens_chatgpt(monkeypatch):
    monkeypatch.setattr(session, "discover_chrome", installed)
    monkeypatch.setattr(session, "chrome_running", lambda: False)
    opened = []
    monkeypatch.setattr(session, "open_chatgpt", lambda: opened.append(True))

    result = session.resolve_chatgpt_session()

    assert opened == [True]
    assert result.action == "opened-chatgpt"


def test_single_existing_chat_tab_is_activated(monkeypatch):
    monkeypatch.setattr(session, "discover_chrome", installed)
    monkeypatch.setattr(session, "chrome_running", lambda: True)

    tab = session.ChromeTabRef(
        2, 3, "ChatGPT", "https://chatgpt.com/c/abc"
    )
    monkeypatch.setattr(session, "list_chrome_tabs", lambda: (tab,))

    activated = []
    monkeypatch.setattr(
        session,
        "activate_tab",
        lambda ref: activated.append(ref),
    )

    result = session.resolve_chatgpt_session()

    assert result.action == "activated-existing"
    assert activated == [tab]


def test_multiple_chat_tabs_fail_closed(monkeypatch):
    monkeypatch.setattr(session, "discover_chrome", installed)
    monkeypatch.setattr(session, "chrome_running", lambda: True)

    tabs = (
        session.ChromeTabRef(1, 1, "A", "https://chatgpt.com/c/a"),
        session.ChromeTabRef(1, 2, "B", "https://chatgpt.com/c/b"),
    )
    monkeypatch.setattr(session, "list_chrome_tabs", lambda: tabs)

    result = session.resolve_chatgpt_session()

    assert result.action == "multiple-candidates"
    assert result.selected is None
