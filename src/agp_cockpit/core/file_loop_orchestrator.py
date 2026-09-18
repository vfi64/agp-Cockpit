from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib,json
from .file_loop_protocol import RemoteState,parse_terminal_reply,accept_command_file
from .file_loop_runner import FileLoopRun,execute_with_run_next
CONTINUATION_TEXT="Attached is the result file. Evaluate it and continue the current task. Return exactly one Python command file if more local work is required; otherwise finish or request human input."
REPLAY_CONTINUATION_TEXT="This command file was already executed and is being replayed idempotently. Read the attached existing result file; do not return the same command again. Continue the current task or finish."
@dataclass(frozen=True)
class LoopOutcome:
    state:RemoteState;run:FileLoopRun|None=None;human_reason:str|None=None;continuation_text:str|None=None
    replayed:bool=False
def _load(path:Path)->dict:
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding="utf-8"));return data if isinstance(data,dict) else {}
def _save(path:Path,data:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
def consume_command_file(source:Path,root:Path,state_file:Path,stem:str="remote_command")->LoopOutcome:
    source=source.expanduser().resolve();fp=hashlib.sha256(source.read_bytes()).hexdigest();state=_load(state_file)
    if state.get("last_command_sha256")==fp:
        result_path = Path(str(state.get("return_bundle") or ""))
        if not result_path.is_file():
            raise RuntimeError("duplicate remote command file has no preserved result bundle")
        result = _load(result_path)
        run = FileLoopRun(
            step=int(state.get("step", 0)),
            command_file=source,
            return_bundle=result_path,
            runner_returncode=int(result.get("runner_returncode", 0)),
            stdout=str(result.get("stdout", "") or ""),
            stderr=str(result.get("stderr", "") or ""),
        )
        return LoopOutcome(
            RemoteState.COMMAND_FILE,
            run=run,
            continuation_text=REPLAY_CONTINUATION_TEXT,
            replayed=True,
        )
    command=accept_command_file(source,root/"Download",stem);run=execute_with_run_next(root,command)
    _save(state_file,{"last_command_sha256":fp,"step":run.step,"return_bundle":str(run.return_bundle),"command_file":str(run.command_file)})
    return LoopOutcome(RemoteState.COMMAND_FILE,run=run,continuation_text=CONTINUATION_TEXT)
def consume_terminal_reply(text:str,state_file:Path)->LoopOutcome:
    reply=parse_terminal_reply(text);state=_load(state_file);fp=hashlib.sha256(text.encode()).hexdigest()
    if state.get("last_terminal_sha256")==fp:raise RuntimeError("duplicate remote terminal reply refused")
    _save(state_file,{"last_terminal_sha256":fp,"terminal":reply.state.value})
    return LoopOutcome(reply.state,human_reason=reply.human_reason)
