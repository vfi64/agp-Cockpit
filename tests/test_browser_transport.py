from pathlib import Path

import pytest

import agp_cockpit.core.browser_transport as browser


def test_discover_chrome_not_found(monkeypatch):
    monkeypatch.setattr(Path, "exists", lambda self: False)
    info = browser.discover_chrome()
    assert info.installed is False


def test_open_url_rejects_non_http():
    with pytest.raises(ValueError):
        browser.open_url_in_chrome("file:///tmp/test")


def test_focus_chrome_uses_open(monkeypatch):
    monkeypatch.setattr(
        browser,
        "discover_chrome",
        lambda: browser.BrowserInfo(
            "Google Chrome",
            Path("/Applications/Google Chrome.app"),
        ),
    )

    calls = []

    class Result:
        returncode = 0
        stderr = ""

    monkeypatch.setattr(
        browser.subprocess,
        "run",
        lambda argv, **kwargs: calls.append(argv) or Result(),
    )

    browser.focus_chrome()

    assert calls == [["/usr/bin/open", "-a", "Google Chrome"]]
