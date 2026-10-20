from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from .automation_guard import AutomationGuard
from .command_file_contract import WORK_ORDER_KIT_RULE
from .file_loop_protocol import (
    RemoteState,
    accept_command_file,
    next_step_number,
    parse_terminal_reply,
)
from .file_loop_runner import (
    FileLoopRun,
    RunNextProcessController,
    execute_with_run_next,
    step_from_command_file,
)
from .task_reply_policy import GENERIC, ReplyPolicy, terminal_reply_instruction

MAX_CONSECUTIVE_FAILURES = 3
MAX_PREFLIGHT_FAILURES = 2
CONTINUATION_TEXT="Attached is the result file. Evaluate it and continue the current task. Return exactly one Python command file if more local work is required; otherwise finish or request human input."
REPLAY_CONTINUATION_TEXT="This command file was already executed and is being replayed idempotently. Read the attached existing result file; do not return the same command again. Continue the current task or finish."
RECOVERY_CONTINUATION_PREFIX="""The attached local execution evidence reports a FAILED command-file step.
Recovery is required. Do not claim that the requested Kit operation ran successfully.
Read the attached result file completely: the canonical return bundle; the immutable step-scoped run_next log is embedded in it under "run_next_log".
If the failure is a syntax/compile failure, the real run was never reached and no Kit command was executed.
Return exactly one newly numbered Python command file that corrects the diagnosed failure.
The replacement file must execute the intended local work during its real run and create exactly one canonical return bundle.
Its filename, internal STEP constant, output names, and return-bundle names must use the newly assigned local step; do not copy the prior step number.
Keep the replacement file <= 80 source lines and <= 16 KiB; do not include long comments, embedded logs, or recursive Download scans.
The return-bundle file must contain exactly one parseable JSON object; do not append shell output, ACK text, or diagnostics to that file.
Do not return prose, a JSON command description, or the same broken file. Do not bypass the local runner, Kit gates, or evidence requirements.
"""
UNKNOWN_OUTCOME_NOTICE = (
    "The local execution outcome is UNKNOWN (timeout or operator stop): the command may have "
    "partially or fully applied its effects. The replacement work order must first inspect the "
    "current repository and Kit state and must not assume that nothing happened.\n"
)
REDELIVERY_NOTICE = (
    "Re-delivery: this local result was produced earlier, but its delivery to you was not "
    "confirmed. The command was NOT executed again.\n"
)
# AGP_K07_DELIVERY_STATE_V1
# Every executed step records whether its result reached the remote chat.
# PENDING: result exists, delivery unconfirmed (replay re-delivers it).
# DELIVERED: browser confirmed the continuation send.
# DELIVERED_IMPLIED: a newer remote command proves the remote continued.
# WITHHELD: local terminal/operator state intentionally suppressed delivery.
DELIVERY_PENDING = "PENDING"
DELIVERY_DELIVERED = "DELIVERED"
DELIVERY_IMPLIED = "DELIVERED_IMPLIED"
DELIVERY_WITHHELD = "WITHHELD"
# AGP_K07_INFLIGHT_RECORD_V1
# A step is persisted as RUNNING before run_next starts. A RUNNING or
# OUTCOME_UNKNOWN record found at admission means the bridge lost the outcome
# (crash/restart/exception); AGENTS.md forbids blind replay, so the loop blocks.
UNRESOLVED_STATES = frozenset({"RUNNING", "OUTCOME_UNKNOWN"})


@dataclass(frozen=True)
class LoopOutcome:
    state:RemoteState;run:FileLoopRun|None=None;human_reason:str|None=None;continuation_text:str|None=None
    replayed:bool=False
    delivery_pending:bool=False
def _load(path:Path)->dict:
    if not path.exists():return {}
    data=json.loads(path.read_text(encoding="utf-8"));return data if isinstance(data,dict) else {}
def _save(path:Path,data:dict)->None:
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+"\n",encoding="utf-8")
def _continuation_for_run(run:FileLoopRun)->str:
    try:
        result=json.loads(run.return_bundle.read_text(encoding="utf-8"))
    except (OSError,UnicodeDecodeError,json.JSONDecodeError):
        result={}
    failed=_run_failed(result, run)
    if not failed:
        return CONTINUATION_TEXT
    reason=str(result.get("failure_reason") or "local execution evidence is incomplete")
    unknown = UNKNOWN_OUTCOME_NOTICE if result.get("outcome") == "OUTCOME_UNKNOWN" else ""
    return (RECOVERY_CONTINUATION_PREFIX + unknown
        + f"Failure reason: {reason}\n"
        + f"Runner return code: {result.get('runner_returncode', run.runner_returncode)}\n"
        + f"Command file: {run.command_file}\n")


def _repository_facts(root: Path, command_file: Path | None) -> str:
    """AGP_REPOSITORY_FACTS_V1: locally verified facts for the continuation."""
    try:
        from agp_cockpit.core.ci_gate import gh_binary
        from agp_cockpit.core.merged_branch_guard import repository_facts
        source = None
        if command_file is not None and Path(command_file).is_file():
            source = Path(command_file).read_text(encoding="utf-8")
        line = repository_facts(root, source, gh=gh_binary(root))
    except Exception:  # noqa: BLE001 - facts are an aid, never a loop failure
        return ""
    return (line + "\n") if line else ""


def _with_next_local_step(text: str, root: Path, completed_step: int,
                          reply_policy: ReplyPolicy = GENERIC,
                          command_file: Path | None = None) -> str:
    next_step = next_step_number(root / "Download", minimum_step=completed_step)
    return (
        text
        + _repository_facts(root, command_file)
        + f"\nThe local bridge assigned step {completed_step}. "
        + f"The next remote command file must be new; expected local step: {next_step}. "
        + f"Set its internal STEP constant and all step-scoped output names to {next_step}. "
        + "Do not reuse the previous command-file content or identity.\n"
        + WORK_ORDER_KIT_RULE + "\n"
        + terminal_reply_instruction(next_step, reply_policy)
    )


def _result_for_run(run: FileLoopRun) -> dict:
    try:
        result = json.loads(run.return_bundle.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return result if isinstance(result, dict) else {}


def _run_failed(result: dict, run: FileLoopRun) -> bool:
    status = str(result.get("status") or "").strip().lower()
    return status in {"failed", "fail"} or run.artifact_kind == "execution_diagnostic"


def _failure_signature(result: dict, run: FileLoopRun) -> str:
    payload = {
        "status": result.get("status"),
        "failure_reason": result.get("failure_reason"),
        "artifact_kind": run.artifact_kind,
        "runner_returncode": result.get("runner_returncode", run.runner_returncode),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _is_preflight_failure(result: dict, run: FileLoopRun) -> bool:
    """Identify failures where the local command was never allowed to run."""
    reason = str(result.get("failure_reason") or "")
    return (
        run.artifact_kind == "execution_diagnostic"
        and result.get("execution") == "command_file_failed"
        and "semantic contract rejected" in reason
    )


def _file_sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def mark_result_delivered(state_file: Path, result_sha256: str, mission_id: str | None = None) -> dict:
    """Confirm browser delivery of one executed step result."""
    state = _load(state_file)
    if mission_id and state.get("mission_id") not in {None, mission_id}:
        raise ValueError("delivery acknowledgement belongs to another mission")
    history = state.get("command_history", [])
    if not isinstance(history, list):
        history = []
    for entry in reversed(history):
        if isinstance(entry, dict) and entry.get("result_sha256") == result_sha256:
            if entry.get("delivery") in {DELIVERY_DELIVERED, DELIVERY_IMPLIED}:
                return {"delivery": entry["delivery"], "step": entry.get("step"), "idempotent": True}
            if entry.get("delivery") != DELIVERY_PENDING:
                raise ValueError(f"result delivery is not pending: {entry.get('delivery')}")
            entry["delivery"] = DELIVERY_DELIVERED
            state["command_history"] = history
            _save(state_file, state)
            return {"delivery": DELIVERY_DELIVERED, "step": entry.get("step"), "idempotent": False}
    raise ValueError("unknown result delivery acknowledgement")


def withhold_result_delivery(state_file: Path, result_sha256: str) -> None:
    state = _load(state_file)
    history = state.get("command_history", [])
    if not isinstance(history, list):
        return
    for entry in reversed(history):
        if isinstance(entry, dict) and entry.get("result_sha256") == result_sha256:
            if entry.get("delivery") == DELIVERY_PENDING:
                entry["delivery"] = DELIVERY_WITHHELD
                _save(state_file, state)
            return


def consume_command_file(
    source: Path,
    root: Path,
    state_file: Path,
    stem: str | None = None,
    mission_id: str | None = None,
    guard: AutomationGuard | None = None,
    process_controller: RunNextProcessController | None = None,
    reply_policy: ReplyPolicy = GENERIC,
    kit_approvals=None,
) -> LoopOutcome:
    source=source.expanduser().resolve();fp=hashlib.sha256(source.read_bytes()).hexdigest();state=_load(state_file)
    if mission_id and state.get("mission_id") != mission_id:
        state = {}
    assistant_text = source.read_text(encoding="utf-8")
    if guard is not None:
        try:
            guard.before_turn()
        except RuntimeError as exc:
            _save(
                state_file,
                {
                    **state,
                    "mission_id": mission_id,
                    "state": RemoteState.BLOCKED.value,
                    "human_reason": str(exc),
                    "blocked_at_command": str(source),
                },
            )
            return LoopOutcome(RemoteState.BLOCKED, human_reason=str(exc))
    history = state.get("command_history", [])
    if not isinstance(history, list):
        history = []
    unresolved = next(
        (entry for entry in reversed(history)
         if isinstance(entry, dict) and entry.get("state") in UNRESOLVED_STATES),
        None,
    )
    if unresolved is not None:
        reason = (
            f"local step {unresolved.get('step')} has an unresolved execution outcome "
            f"({unresolved.get('state')}); the bridge lost its result, so no further "
            "command file is executed automatically"
        )
        _save(
            state_file,
            {
                **state,
                "mission_id": mission_id,
                "state": RemoteState.BLOCKED.value,
                "human_reason": reason,
                "blocked_at_command": str(source),
            },
        )
        return LoopOutcome(RemoteState.BLOCKED, human_reason=reason)
    previous = next(
        (entry for entry in reversed(history) if isinstance(entry, dict) and entry.get("sha256") == fp),
        None,
    )
    if previous is None and state.get("last_command_sha256") == fp:
        previous = state
    if previous is not None:
        result_path = Path(str(previous.get("return_bundle") or ""))
        if not result_path.is_file():
            raise RuntimeError("duplicate remote command file has no preserved result bundle")
        result = _load(result_path)
        run = FileLoopRun(
            step=int(previous.get("step", 0)),
            command_file=source,
            return_bundle=result_path,
            run_next_output=Path(str(previous.get("run_next_output") or (root / "Download" / "__run_next_output.txt"))),
            runner_returncode=int(result.get("runner_returncode", 0)),
            stdout=str(result.get("stdout", "") or ""),
            stderr=str(result.get("stderr", "") or ""),
            artifact_kind=str(result.get("artifact_kind", "return_bundle") or "return_bundle"),
        )
        if guard is not None:
            guard.success()
        blocked = previous.get("state") == RemoteState.BLOCKED.value
        delivery_pending = (not blocked) and previous.get("delivery") == DELIVERY_PENDING
        if delivery_pending:
            continuation = REDELIVERY_NOTICE + _with_next_local_step(
                _continuation_for_run(run), root, run.step, reply_policy, run.command_file
            )
            if guard is not None:
                try:
                    guard.record_prompt(continuation)
                except RuntimeError as exc:
                    return LoopOutcome(RemoteState.BLOCKED, run=run, human_reason=str(exc), replayed=True)
        else:
            continuation = None if blocked else REPLAY_CONTINUATION_TEXT
        return LoopOutcome(
            RemoteState.BLOCKED if blocked else RemoteState.COMMAND_FILE,
            run=run,
            continuation_text=continuation,
            human_reason=(str(previous.get("human_reason")) if blocked else None),
            replayed=True,
            delivery_pending=delivery_pending,
        )
    if guard is not None:
        try:
            guard.record_assistant(assistant_text)
        except RuntimeError as exc:
            _save(
                state_file,
                {
                    **state,
                    "mission_id": mission_id,
                    "state": RemoteState.BLOCKED.value,
                    "human_reason": str(exc),
                    "blocked_at_command": str(source),
                },
            )
            return LoopOutcome(RemoteState.BLOCKED, human_reason=str(exc))
    persisted_step = int(state.get("step", 0) or 0)
    effective_stem = source.stem if stem is None else stem
    # A new remote command proves that the remote continued after every
    # earlier result, even if the browser's explicit acknowledgement was lost.
    for entry in history:
        if isinstance(entry, dict) and entry.get("delivery") == DELIVERY_PENDING:
            entry["delivery"] = DELIVERY_IMPLIED
    command=accept_command_file(source,root/"Download",effective_stem,minimum_step=persisted_step)
    running_record = {
        "sha256": fp,
        "step": step_from_command_file(command),
        "command_file": str(command),
        "remote_filename": str(Path(effective_stem).name),
        "state": "RUNNING",
    }
    _save(
        state_file,
        {**state, "mission_id": mission_id, "command_history": (history + [running_record])[-16:]},
    )
    try:
        run=execute_with_run_next(root,command,process_controller=process_controller,
                                  kit_approvals=kit_approvals)
    except BaseException:
        running_record["state"] = "OUTCOME_UNKNOWN"
        _save(
            state_file,
            {**state, "mission_id": mission_id, "command_history": (history + [running_record])[-16:]},
        )
        raise
    result = _result_for_run(run)
    failed = _run_failed(result, run)
    preflight_failure = _is_preflight_failure(result, run)
    guard_blocked_reason = None
    if guard is not None:
        try:
            if failed:
                guard.error()
            else:
                guard.success()
        except RuntimeError as exc:
            guard_blocked_reason = str(exc)
    consecutive_failures = int(state.get("consecutive_failures", 0) or 0)
    failure_signature = str(state.get("last_failure_signature", "") or "")
    if failed:
        current_signature = _failure_signature(result, run)
        consecutive_failures = consecutive_failures + 1 if current_signature == failure_signature else 1
        failure_signature = current_signature
    else:
        consecutive_failures = 0
        failure_signature = ""
    preflight_failures = int(state.get("preflight_failures", 0) or 0)
    if preflight_failure:
        preflight_failures += 1
    else:
        preflight_failures = 0
    terminal_blocked = (
        guard_blocked_reason is not None
        or failed and consecutive_failures >= MAX_CONSECUTIVE_FAILURES
        or preflight_failure and preflight_failures >= MAX_PREFLIGHT_FAILURES
    )
    human_reason = (
        guard_blocked_reason
        if guard_blocked_reason is not None
        else (
            (
                "file-loop blocked after "
                f"{preflight_failures} command-file preflight failures; "
                "the remote Python file was not executed"
            )
            if preflight_failure and preflight_failures >= MAX_PREFLIGHT_FAILURES
            else f"file-loop blocked after {consecutive_failures} consecutive failures without proven progress"
            if terminal_blocked else None
        )
    )
    record={"sha256":fp,"step":run.step,"result_sha256":_file_sha256(run.return_bundle),"delivery":DELIVERY_WITHHELD if terminal_blocked else DELIVERY_PENDING,"return_bundle":str(run.return_bundle),"run_next_output":str(run.run_next_output),"artifact_kind":run.artifact_kind,"command_file":str(run.command_file),"remote_filename":str(Path(effective_stem).name),"state":RemoteState.BLOCKED.value if terminal_blocked else RemoteState.COMMAND_FILE.value,"human_reason":human_reason}
    history = (history + [record])[-16:]
    persisted={"mission_id":mission_id,"last_command_sha256":fp,"step":run.step,"return_bundle":str(run.return_bundle),"run_next_output":str(run.run_next_output),"artifact_kind":run.artifact_kind,"command_file":str(run.command_file),"remote_filename":str(Path(effective_stem).name),"command_history":history,"consecutive_failures":consecutive_failures,"last_failure_signature":failure_signature,"preflight_failures":preflight_failures,"state":RemoteState.BLOCKED.value if terminal_blocked else RemoteState.COMMAND_FILE.value,"human_reason":human_reason}
    _save(state_file,persisted)
    if terminal_blocked:
        return LoopOutcome(
            RemoteState.BLOCKED,
            run=run,
            human_reason=human_reason,
            continuation_text=None,
        )
    continuation = None if terminal_blocked else _with_next_local_step(
        _continuation_for_run(run), root, run.step, reply_policy, run.command_file)
    if guard is not None and continuation is not None:
        try:
            guard.record_prompt(continuation)
        except RuntimeError as exc:
            terminal_blocked = True
            human_reason = str(exc)
            continuation = None
    if terminal_blocked:
        persisted["state"] = RemoteState.BLOCKED.value
        persisted["human_reason"] = human_reason
        record["state"] = RemoteState.BLOCKED.value
        record["human_reason"] = human_reason
        record["delivery"] = DELIVERY_WITHHELD
        _save(state_file, persisted)
        return LoopOutcome(RemoteState.BLOCKED, run=run, human_reason=human_reason)
    return LoopOutcome(RemoteState.COMMAND_FILE,run=run,continuation_text=continuation,delivery_pending=True)
def consume_terminal_reply(text:str,state_file:Path)->LoopOutcome:
    reply=parse_terminal_reply(text);state=_load(state_file);fp=hashlib.sha256(text.encode()).hexdigest()
    if state.get("last_terminal_sha256")==fp:raise RuntimeError("duplicate remote terminal reply refused")
    _save(state_file,{"last_terminal_sha256":fp,"terminal":reply.state.value})
    return LoopOutcome(reply.state,human_reason=reply.human_reason)
