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


# --- AGP_CONNECTED_CHAT_TARGET_V1 (live 2026-10-03) -------------------------------------------

def _handshake(tmp_path, url, age=10.0):
    import json
    import time
    (tmp_path / "extension.json").write_text(json.dumps({"timestamp_unix": time.time() - age, "page_url": url}))


def test_front_extensions_tab_falls_back_to_the_connected_chat(monkeypatch, tmp_path):
    focused = []
    monkeypatch.setattr(chrome, "active_chrome_url", lambda: "chrome://extensions/")
    monkeypatch.setattr(chrome, "focus_chat_tab", lambda url: focused.append(url) or True)
    _handshake(tmp_path, "https://chatgpt.com/c/abc")
    target = chrome.require_allowed_active_chat(tmp_path)
    assert target.url == "https://chatgpt.com/c/abc" and target.allowed
    assert focused == ["https://chatgpt.com/c/abc"]


def test_front_chat_tab_wins_and_nothing_is_focused(monkeypatch, tmp_path):
    focused = []
    monkeypatch.setattr(chrome, "active_chrome_url", lambda: "https://chatgpt.com/c/front")
    monkeypatch.setattr(chrome, "focus_chat_tab", lambda url: focused.append(url) or True)
    _handshake(tmp_path, "https://chatgpt.com/c/abc")
    assert chrome.require_allowed_active_chat(tmp_path).url == "https://chatgpt.com/c/front"
    assert focused == []


def test_stale_or_foreign_handshake_still_blocks(monkeypatch, tmp_path):
    monkeypatch.setattr(chrome, "active_chrome_url", lambda: "chrome://extensions/")
    monkeypatch.setattr(chrome, "focus_chat_tab", lambda url: True)
    _handshake(tmp_path, "https://chatgpt.com/c/abc", age=600)
    with pytest.raises(PermissionError, match="keine verbundene ChatGPT-Seite"):
        chrome.require_allowed_active_chat(tmp_path)
    _handshake(tmp_path, "https://example.com/")
    with pytest.raises(PermissionError):
        chrome.require_allowed_active_chat(tmp_path)


def test_unreadable_front_tab_falls_back_too(monkeypatch, tmp_path):
    def broken():
        raise RuntimeError("Google Chrome has no window")
    monkeypatch.setattr(chrome, "active_chrome_url", broken)
    monkeypatch.setattr(chrome, "focus_chat_tab", lambda url: True)
    _handshake(tmp_path, "https://chatgpt.com/c/abc")
    assert chrome.require_allowed_active_chat(tmp_path).url == "https://chatgpt.com/c/abc"
