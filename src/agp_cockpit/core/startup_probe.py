from __future__ import annotations
import json
import shutil
import socket
import subprocess
import urllib.request
from .startup import StartupObservation, decide_startup, format_startup_status

def _busy(port=11434):
    with socket.socket() as s:
        s.settimeout(0.25)
        return s.connect_ex(("127.0.0.1", port)) == 0

def _owner_is_ollama(port=11434):
    lsof = shutil.which("lsof") or "/usr/sbin/lsof"
    try:
        cp = subprocess.run([lsof, "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"],
                            capture_output=True, text=True, timeout=2)
        return cp.returncode == 0 and "ollama" in cp.stdout.lower()
    except (OSError, subprocess.TimeoutExpired):
        return False

def _models():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1) as r:
            data = json.load(r)
        return True, tuple(x["name"] for x in data.get("models", []) if x.get("name"))
    except Exception:
        return False, ()

def observe_live_read_only():
    busy = _busy()
    reachable, models = _models() if busy else (False, ())
    return StartupObservation(
        ollama_installed=shutil.which("ollama") is not None,
        port_busy=busy,
        port_owner_is_ollama=_owner_is_ollama() if busy else False,
        api_reachable=reachable,
        models=models,
    )

def main():
    obs = observe_live_read_only()
    decision = decide_startup(obs)
    print(format_startup_status(obs))
    print("Startup-Aktion:", decision.action.value)
    print("Mutation zulässig:", "ja" if decision.may_mutate else "nein")
    print("LIVE_PROBE_MODE=READ_ONLY")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
