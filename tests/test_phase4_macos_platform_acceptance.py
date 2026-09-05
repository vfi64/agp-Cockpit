from __future__ import annotations
import signal
from agp_cockpit.adapters import macos_browser, macos_process_control, macos_runtime

class CP:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

def test_macos_process_listing_is_owned_by_adapter(monkeypatch):
    seen = {}
    def fake(argv, **kwargs):
        seen["argv"] = argv
        seen["kwargs"] = kwargs
        return CP(stdout=" 12 /opt/homebrew/bin/ollama serve\n 13 /bin/zsh\n")
    monkeypatch.setattr(macos_process_control.subprocess, "run", fake)
    rows = macos_process_control.list_processes()
    assert [x.pid for x in rows] == [12, 13]
    assert seen["argv"] == ["ps", "-axo", "pid=,command="]
    assert seen["kwargs"]["check"] is False

def test_listener_discovery_is_exact_and_ignores_garbage(monkeypatch):
    seen = {}
    def fake(argv, **kwargs):
        seen["argv"] = argv
        return CP(stdout="321\nnot-a-pid\n654\n")
    monkeypatch.setattr(macos_process_control.subprocess, "run", fake)
    assert macos_process_control.pids_listening_on_port(11434) == (321, 654)
    assert seen["argv"] == ["lsof", "-nP", "-iTCP:11434", "-sTCP:LISTEN", "-t"]

def test_listener_discovery_fails_closed_to_empty_tuple(monkeypatch):
    monkeypatch.setattr(macos_process_control.subprocess, "run", lambda *a, **k: CP(returncode=1, stderr="not found"))
    assert macos_process_control.pids_listening_on_port(11434) == ()

def test_signal_mutation_is_pid_exact(monkeypatch):
    seen = []
    monkeypatch.setattr(macos_process_control.os, "kill", lambda pid, sig: seen.append((pid, sig)))
    macos_process_control.send_sigterm(41)
    macos_process_control.send_sigkill(42)
    assert seen == [(41, signal.SIGTERM), (42, signal.SIGKILL)]

def test_detached_spawn_has_no_shell_and_detaches(monkeypatch):
    seen = {}
    class P: pass
    def fake(argv, **kwargs):
        seen["argv"] = argv
        seen["kwargs"] = kwargs
        return P()
    monkeypatch.setattr(macos_process_control.subprocess, "Popen", fake)
    result = macos_process_control.spawn_detached(["/opt/homebrew/bin/ollama", "serve"])
    assert isinstance(result, P)
    assert seen["argv"] == ["/opt/homebrew/bin/ollama", "serve"]
    assert seen["kwargs"]["start_new_session"] is True
    assert "shell" not in seen["kwargs"]

def test_process_port_uses_ps_without_shell(monkeypatch):
    seen = {}
    def fake(argv, **kwargs):
        seen["argv"] = argv
        seen["kwargs"] = kwargs
        return CP(stdout=" 7 /usr/local/bin/hermes\n")
    monkeypatch.setattr(macos_runtime.subprocess, "run", fake)
    assert macos_runtime.MacOSProcessPort().is_running("Hermes") is True
    assert seen["argv"] == ["ps", "-axo", "pid=,command="]
    assert "shell" not in seen["kwargs"]

def test_browser_focus_and_open_url_are_adapter_owned(monkeypatch):
    calls = []
    def fake(argv, **kwargs):
        calls.append(argv)
        return CP()
    monkeypatch.setattr(macos_browser.subprocess, "run", fake)
    port = macos_browser.MacOSChromeBrowserPort()
    port.focus()
    port.open_url("https://chatgpt.com/c/test")
    assert calls == [
        ["/usr/bin/open", "-a", "Google Chrome"],
        ["/usr/bin/open", "-a", "Google Chrome", "https://chatgpt.com/c/test"],
    ]

def test_browser_adapter_surfaces_open_failure(monkeypatch):
    monkeypatch.setattr(macos_browser.subprocess, "run", lambda *a, **k: CP(returncode=1, stderr="boom"))
    try:
        macos_browser.MacOSChromeBrowserPort().focus()
    except RuntimeError as exc:
        assert "boom" in str(exc)
    else:
        raise AssertionError("focus failure must surface")

def test_runtime_rejects_non_macos(monkeypatch):
    monkeypatch.setattr(macos_runtime, "is_macos", lambda: False)
    try:
        macos_runtime.discover_macos_runtime()
    except RuntimeError as exc:
        assert "non-macOS" in str(exc)
    else:
        raise AssertionError("non-macOS use must fail")
