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


def test_focus_chrome_uses_browser_port():
    calls = []

    class FakeBrowserPort:
        def installed(self):
            return True

        def focus(self):
            calls.append("focus")

        def open_url(self, url):
            raise AssertionError(f"unexpected URL open: {url}")

    browser.focus_chrome(FakeBrowserPort())

    assert calls == ["focus"]
