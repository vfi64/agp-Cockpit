from __future__ import annotations
import os
import signal
import subprocess
from dataclasses import dataclass
from agp_cockpit.core.process_control import ProcessInfo, PortOwner, parse_ps_lines, ollama_processes, port_owner

def list_processes() -> tuple[ProcessInfo, ...]:
    cp=subprocess.run(["ps","-axo","pid=,command="],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    return parse_ps_lines(cp.stdout.splitlines()) if cp.returncode == 0 else ()

def pids_listening_on_port(port: int) -> tuple[int, ...]:
    cp=subprocess.run(["lsof","-nP",f"-iTCP:{port}","-sTCP:LISTEN","-t"],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if cp.returncode != 0: return ()
    result=[]
    for line in cp.stdout.splitlines():
        try: result.append(int(line.strip()))
        except ValueError: pass
    return tuple(result)

def send_sigterm(pid: int) -> None: os.kill(pid,signal.SIGTERM)
def send_sigkill(pid: int) -> None: os.kill(pid,signal.SIGKILL)
def spawn_detached(argv: list[str]):
    return subprocess.Popen(argv,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)

@dataclass(frozen=True)
class MacOSProcessSnapshot:
    ollama_processes: tuple[ProcessInfo, ...]
    ollama_port_owner: PortOwner

def inspect_macos_process_state() -> MacOSProcessSnapshot:
    processes=list_processes()
    return MacOSProcessSnapshot(ollama_processes=ollama_processes(processes=processes),ollama_port_owner=port_owner(11434,processes=processes))
