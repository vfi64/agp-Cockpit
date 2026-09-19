from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.kit_carrier import (
    KitAuthorityResult,
    require_kit_authority,
)
from agp_cockpit.core.ports import TerminalPort
from agp_cockpit.core.task_models import KitResultEvidence
from agp_cockpit.core.terminal_exec import TerminalResult
from agp_cockpit.core.terminal_policy import ExecutionPolicy
from agp_cockpit.core.work_order import (
    LocalWorkOrder,
    format_result_block,
)


@dataclass(frozen=True)
class WorkOrderPreview:
    order: LocalWorkOrder
    preview_text: str
    authority: KitAuthorityResult | None


@dataclass(frozen=True)
class WorkOrderRun:
    result: TerminalResult
    result_block: str
    authority: KitAuthorityResult | None



def acquire_trusted_kit_evidence(action_id: str, run: WorkOrderRun, *, repository_root: Path) -> KitResultEvidence:
    if not action_id: raise ValueError("action_id required")
    if run.authority is None or not run.authority.is_kit_command or not run.authority.accepted:
        raise PermissionError("trusted Kit evidence requires locally accepted Kit authority")
    argv=tuple(run.result.argv)
    if not argv or Path(argv[0]).name != "agentic-kit":
        raise PermissionError("trusted Kit evidence requires actual agentic-kit execution")
    status="PASS" if run.result.returncode == 0 and not run.result.timed_out else "FAIL"
    revision=subprocess.run(["git","rev-parse","HEAD"],cwd=repository_root,text=True,capture_output=True,check=True).stdout.strip()
    raw=(run.result_block+"\n"+run.result.stdout+"\n"+run.result.stderr).encode("utf-8")
    raw_hash=hashlib.sha256(raw).hexdigest()
    artifact_hash=hashlib.sha256((revision+"\0"+"\0".join(argv)).encode("utf-8")).hexdigest()
    return KitResultEvidence(action_id=action_id,status=status,producer="agentic-project-kit",command=argv,revision=revision,artifact_hash=artifact_hash,raw_hash=raw_hash)


def preview_work_order(
    order: LocalWorkOrder,
    *,
    policy: ExecutionPolicy,
    kit_binary: Path | None = None,
    terminal: TerminalPort | None = None,
) -> WorkOrderPreview:
    command = order.to_terminal_command()
    policy.validate(command)

    authority = None
    if order.kind == "kit":
        if kit_binary is None:
            raise ValueError("kit_binary required for kind='kit'")
        authority = require_kit_authority(
            order,
            kit_binary=kit_binary,
        )

    if terminal is None:
        from agp_cockpit.adapters.local_terminal import SubprocessTerminalAdapter
        terminal = SubprocessTerminalAdapter()

    text = terminal.preview(command)

    if authority is not None:
        text += (
            "\n\nKIT AUTHORITY:\n"
            f"  accepted={authority.accepted}\n"
            f"  reason={authority.reason}"
        )

    return WorkOrderPreview(
        order=order,
        preview_text=text,
        authority=authority,
    )


def execute_work_order(
    order: LocalWorkOrder,
    *,
    policy: ExecutionPolicy,
    kit_binary: Path | None = None,
    terminal: TerminalPort | None = None,
) -> WorkOrderRun:
    command = order.to_terminal_command()
    policy.validate(command)

    authority = None
    if order.kind == "kit":
        if kit_binary is None:
            raise ValueError("kit_binary required for kind='kit'")
        authority = require_kit_authority(
            order,
            kit_binary=kit_binary,
        )

    if terminal is None:
        from agp_cockpit.adapters.local_terminal import SubprocessTerminalAdapter
        terminal = SubprocessTerminalAdapter()

    result = terminal.execute(command)

    return WorkOrderRun(
        result=result,
        result_block=format_result_block(order, result),
        authority=authority,
    )
