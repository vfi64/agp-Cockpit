from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import subprocess, sys
@dataclass(frozen=True)
class FileLoopRun:
    step:int
    command_file:Path
    return_bundle:Path
    runner_returncode:int
    stdout:str
    stderr:str
def step_from_command_file(path:Path)->int:
    prefix=path.name.split("_",1)[0]
    if not prefix.isdigit(): raise ValueError("command file must start with numeric step")
    return int(prefix)
def execute_with_run_next(root:Path,command_file:Path,timeout_seconds:int=300)->FileLoopRun:
    download=root/"Download"; runner=download/"run_next.py"
    if command_file.parent.resolve()!=download.resolve(): raise ValueError("command file must be in repository Download directory")
    step=step_from_command_file(command_file)
    before={p.resolve() for p in download.glob(f"{step:03d}_*_return_bundle.json")}
    cp=subprocess.run([sys.executable,str(runner),str(step)],cwd=root,text=True,capture_output=True,timeout=timeout_seconds)
    after={p.resolve() for p in download.glob(f"{step:03d}_*_return_bundle.json")}
    created=sorted(after-before)
    if len(created)!=1: raise RuntimeError(f"expected exactly one new return bundle for step {step}, got {len(created)}")
    return FileLoopRun(step,command_file,created[0],cp.returncode,cp.stdout,cp.stderr)
