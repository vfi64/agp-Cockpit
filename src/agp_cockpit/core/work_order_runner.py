from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.kit_carrier import (
    KitAuthorityResult,
    require_kit_authority,
)
from agp_cockpit.core.terminal_exec import (
    TerminalResult,
    preview_command,
    run_command,
)
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


def preview_work_order(
    order: LocalWorkOrder,
    *,
    policy: ExecutionPolicy,
    kit_binary: Path | None = None,
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

    text = preview_command(command)

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

    result = run_command(command)

    return WorkOrderRun(
        result=result,
        result_block=format_result_block(order, result),
        authority=authority,
    )
