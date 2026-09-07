from __future__ import annotations
from pathlib import Path
from agp_cockpit.core.bridge_execution import execute_structured_work_order
from agp_cockpit.core.transport_protocol_v1 import ActionEnvelope, ResultEnvelope, encode_result_frame

def execute_direct_action(action: ActionEnvelope, *, repository_root: Path, kit_binary: Path) -> str:
    if action.mode not in {"DIRECT_EXECUTION", "FILE_TRANSFER"}:
        raise ValueError("supported execution mode required")
    work_order = action.work_order
    if not isinstance(work_order, dict) or set(work_order) != {"type","content"}:
        raise ValueError("canonical work_order object required")
    if work_order["type"] != "terminal_payload" or not isinstance(work_order["content"], str):
        raise ValueError("unsupported work_order transport shape")
    step = execute_structured_work_order(work_order["content"], repository_root=repository_root, kit_binary=kit_binary)
    local = {"return_code": step.returncode, "bounded_output": step.result_block, "log_ref": None}
    status = "PASS" if step.returncode == 0 and not step.timed_out else "FAIL"
    return encode_result_frame(ResultEnvelope(
        action.protocol_version, action.session_id, action.round_id, action.action_id, status, local
    ))
