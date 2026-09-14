from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, json
from .file_loop_protocol import RemoteState,parse_remote_reply,persist_command
from .file_loop_runner import FileLoopRun,execute_with_run_next

@dataclass(frozen=True)
class LoopOutcome:
    state: RemoteState
    run: FileLoopRun | None = None
    human_reason: str | None = None

def fingerprint(text:str)->str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def consume_remote_reply(text:str,root:Path,state_file:Path,stem:str="remote_command")->LoopOutcome:
    reply=parse_remote_reply(text)
    fp=fingerprint(text)
    state={}
    if state_file.exists():
        state=json.loads(state_file.read_text())
    if state.get("last_remote_fingerprint")==fp:
        raise RuntimeError("duplicate remote reply refused")
    if reply.state is RemoteState.DONE:
        state_file.parent.mkdir(parents=True,exist_ok=True)
        state_file.write_text(json.dumps({"last_remote_fingerprint":fp,"terminal":"DONE"},indent=2)+"\n")
        return LoopOutcome(RemoteState.DONE)
    if reply.state is RemoteState.NEEDS_HUMAN:
        state_file.parent.mkdir(parents=True,exist_ok=True)
        state_file.write_text(json.dumps({"last_remote_fingerprint":fp,"terminal":"NEEDS_HUMAN"},indent=2)+"\n")
        return LoopOutcome(RemoteState.NEEDS_HUMAN,human_reason=reply.human_reason)
    command=persist_command(reply,root/"Download",stem)
    run=execute_with_run_next(root,command)
    state_file.parent.mkdir(parents=True,exist_ok=True)
    state_file.write_text(json.dumps({"last_remote_fingerprint":fp,"step":run.step,"return_bundle":str(run.return_bundle)},indent=2)+"\n")
    return LoopOutcome(RemoteState.COMMAND_FILE,run=run)
