import signal
from agp_cockpit.adapters import macos_process_control as mac

def test_adapter_process_listing(monkeypatch):
    class R:
        returncode=0; stdout="  12 /opt/homebrew/bin/ollama serve\n  13 /bin/zsh\n"; stderr=""
    monkeypatch.setattr(mac.subprocess,"run",lambda *a,**k:R())
    assert [p.pid for p in mac.list_processes()] == [12,13]

def test_adapter_listening_pids(monkeypatch):
    class R:
        returncode=0; stdout="12\n99\n"; stderr=""
    monkeypatch.setattr(mac.subprocess,"run",lambda *a,**k:R())
    assert mac.pids_listening_on_port(11434) == (12,99)

def test_adapter_signals(monkeypatch):
    calls=[]
    monkeypatch.setattr(mac.os,"kill",lambda pid,sig:calls.append((pid,sig)))
    mac.send_sigterm(12); mac.send_sigkill(13)
    assert calls == [(12,signal.SIGTERM),(13,signal.SIGKILL)]
