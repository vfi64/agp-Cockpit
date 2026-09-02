import pytest

import agp_cockpit.core.chrome_automation as chrome


def test_chatgpt_host_is_allowed():
    target = chrome.classify_target(
        "https://chatgpt.com/c/123"
    )
    assert target.allowed is True
    assert target.host == "chatgpt.com"


def test_non_https_is_rejected():
    target = chrome.classify_target(
        "http://chatgpt.com/c/123"
    )
    assert target.allowed is False


def test_foreign_host_is_rejected():
    target = chrome.classify_target(
        "https://example.com/"
    )
    assert target.allowed is False


def test_require_allowed_active_chat_blocks_foreign(monkeypatch):
    monkeypatch.setattr(
        chrome,
        "active_chrome_url",
        lambda: "https://example.com/",
    )

    with pytest.raises(PermissionError):
        chrome.require_allowed_active_chat()


def test_paste_send_checks_target_before_keystrokes(monkeypatch):
    calls = []

    monkeypatch.setattr(
        chrome,
        "active_chrome_url",
        lambda: "https://chatgpt.com/c/abc",
    )

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(
        chrome,
        "_run_osascript",
        lambda script: calls.append(script) or Result(),
    )

    target = chrome.paste_and_send_active_chat()

    assert target.allowed is True
    assert len(calls) == 1
    assert 'keystroke "v"' in calls[0]
    assert "key code 36" in calls[0]


def test_paste_send_never_types_into_foreign_target(monkeypatch):
    calls = []

    monkeypatch.setattr(
        chrome,
        "active_chrome_url",
        lambda: "https://github.com/",
    )

    monkeypatch.setattr(
        chrome,
        "_run_osascript",
        lambda script: calls.append(script),
    )

    with pytest.raises(PermissionError):
        chrome.paste_and_send_active_chat()

    assert calls == []
