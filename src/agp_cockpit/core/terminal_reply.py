"""Terminal remote replies as step-scoped files.

AGP_K07_TERMINAL_REPLY_FILE_V1 (D4)
Live 2026-09-30: the ChatGPT DOM exposes no assistant role or message-id
nodes, so prose markers such as AGP_DONE / AGP_NEEDS_HUMAN are invisible to
the extension and a terminal remote answer ended in a 180 s wait timeout.
A terminal answer is therefore a file card with the same identity as a work
order: ``<expected step>_agp_terminal.json``. It carries no executable
content and is never authority for local completion: remote DONE is a request
that a local completion contract may reject.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

TERMINAL_NAME = re.compile(r"^(\d+)_agp_terminal\.json$")
TERMINAL_STATES = frozenset({"DONE", "NEEDS_HUMAN"})
ALLOWED_KEYS = frozenset({"state", "reason", "step", "pr"})
MAX_TERMINAL_BYTES = 16_384
MAX_REASON_CHARS = 2_000


@dataclass(frozen=True)
class TerminalReply:
    filename: str
    step: int
    state: str
    reason: str
    sha256: str
    # AGP_CI_GREEN_COMPLETION_V1: pull request whose CI the Cockpit verifies.
    pr: int | None = None


def is_terminal_filename(name: str) -> bool:
    return TERMINAL_NAME.fullmatch(str(name or "")) is not None


def parse_terminal_reply(filename: str, content: str) -> TerminalReply:
    match = TERMINAL_NAME.fullmatch(str(filename or ""))
    if match is None:
        raise ValueError("terminal reply filename must be <step>_agp_terminal.json")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("terminal reply content required")
    raw = content.encode("utf-8")
    if len(raw) > MAX_TERMINAL_BYTES:
        raise ValueError("terminal reply exceeds 16 KiB")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"terminal reply is not valid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("terminal reply must be a JSON object")  # noqa: TRY004 - protocol rejection, not a caller type error
    unknown = sorted(set(data) - ALLOWED_KEYS)
    if unknown:
        raise ValueError(f"terminal reply has unknown keys: {', '.join(unknown)}")
    state = data.get("state")
    if state not in TERMINAL_STATES:
        raise ValueError("terminal reply state must be DONE or NEEDS_HUMAN")
    reason = data.get("reason")
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("terminal reply reason required")
    reason = " ".join(reason.split())
    if len(reason) > MAX_REASON_CHARS:
        raise ValueError("terminal reply reason exceeds 2000 characters")
    step = int(match.group(1))
    if "step" in data and data["step"] != step:
        raise ValueError("terminal reply step does not match its filename")
    pr = data.get("pr")
    if pr is not None and (isinstance(pr, bool) or not isinstance(pr, int) or pr <= 0):
        raise ValueError("terminal reply pr must be a positive pull request number")
    return TerminalReply(filename, step, str(state), reason, hashlib.sha256(raw).hexdigest(), pr)


def record_terminal_reply(download_dir: Path, reply: TerminalReply, content: str,
                          expected_step: int) -> bool:
    """Persist the reply as local evidence. Returns True for an idempotent replay.

    A new reply must carry exactly the next local step number. The same file
    with identical bytes may be submitted again; different bytes under an
    already used number are an identity conflict.
    """
    target = download_dir / reply.filename
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != reply.sha256:
            raise ValueError("terminal reply conflicts with an existing file of the same step")
        return True
    if reply.step != int(expected_step):
        raise ValueError(
            f"terminal reply step {reply.step} is not the expected step {int(expected_step)}"
        )
    download_dir.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(target)
    return False
