from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agp_cockpit.core.terminal_policy import ExecutionPolicy
from agp_cockpit.core.work_order import parse_work_order_json
from agp_cockpit.core.work_order_runner import (
    execute_work_order,
    preview_work_order,
)


@dataclass(frozen=True)
class PreviewedBridgeStep:
    order: Any
    preview_text: str


@dataclass(frozen=True)
class ExecutedBridgeStep:
    order: Any
    preview_text: str
    result_block: str
    returncode: int
    timed_out: bool
    stdout: str
    stderr: str


def _get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


def order_cwd(order: Any) -> Path:
    value = _get(order, "cwd", "working_directory", "workdir")
    if value is None:
        raise ValueError("work order exposes no cwd")
    return Path(value)


def order_argv(order: Any) -> tuple[str, ...]:
    value = _get(order, "argv", "command")
    if value is None:
        raise ValueError("work order exposes no argv")
    if isinstance(value, str):
        raise TypeError("work order command must be argv-like")
    return tuple(str(x) for x in value)


def order_kind(order: Any) -> str:
    return str(_get(order, "kind", default="generic"))


def order_label(order: Any) -> str:
    return str(_get(order, "label", "title", default=""))


def _construct_policy(root: Path, *, allowed_tools: frozenset[str] | None = None, allow_network: bool = True) -> ExecutionPolicy:
    return ExecutionPolicy(repository_root=root, allowed_tools=allowed_tools, allow_network=allow_network)


def _validate_root(order: Any, root: Path) -> None:
    cwd = order_cwd(order).expanduser()
    try:
        resolved = cwd.resolve()
    except FileNotFoundError:
        resolved = cwd.absolute()

    if resolved != root and root not in resolved.parents:
        raise PermissionError(
            f"bridge work order cwd escapes repository root: {cwd}"
        )


def _invoke(
    func,
    order: Any,
    *,
    policy: ExecutionPolicy,
    kit_binary: Path,
):
    return func(
        order,
        policy=policy,
        kit_binary=kit_binary,
    )


def preview_structured_work_order(
    work_order_text: str,
    *,
    repository_root: Path,
    kit_binary: Path,
    allowed_tools: frozenset[str] | None = None,
    allow_network: bool = True,
) -> PreviewedBridgeStep:
    root = repository_root.resolve()
    order = parse_work_order_json(work_order_text)
    _validate_root(order, root)

    policy = _construct_policy(root, allowed_tools=allowed_tools, allow_network=allow_network)
    preview = _invoke(
        preview_work_order,
        order,
        policy=policy,
        kit_binary=kit_binary,
    )

    return PreviewedBridgeStep(
        order=order,
        preview_text=str(
            _get(preview, "preview_text", "text", default=preview)
        ),
    )


def execute_structured_work_order(
    work_order_text: str,
    *,
    repository_root: Path,
    kit_binary: Path,
    allowed_tools: frozenset[str] | None = None,
    allow_network: bool = True,
) -> ExecutedBridgeStep:
    root = repository_root.resolve()
    previewed = preview_structured_work_order(
        work_order_text,
        repository_root=root,
        kit_binary=kit_binary,
        allowed_tools=allowed_tools,
        allow_network=allow_network,
    )

    policy = _construct_policy(root, allowed_tools=allowed_tools, allow_network=allow_network)
    run = _invoke(
        execute_work_order,
        previewed.order,
        policy=policy,
        kit_binary=kit_binary,
    )

    result = _get(run, "result", default=run)
    returncode = int(
        _get(result, "returncode", "return_code", "rc", default=-1)
    )
    timed_out = bool(
        _get(result, "timed_out", "timeout", default=False)
    )
    stdout = str(_get(result, "stdout", default="") or "")
    stderr = str(_get(result, "stderr", default="") or "")

    block = _get(run, "result_block", "text", "output_block")
    if block is None:
        block = "\n".join([
            f"RC={returncode}",
            f"TIMED_OUT={str(timed_out).lower()}",
            "",
            "STDOUT:",
            stdout or "<leer>",
            "",
            "STDERR:",
            stderr or "<leer>",
        ])

    return ExecutedBridgeStep(
        order=previewed.order,
        preview_text=previewed.preview_text,
        result_block=str(block),
        returncode=returncode,
        timed_out=timed_out,
        stdout=stdout,
        stderr=stderr,
    )
