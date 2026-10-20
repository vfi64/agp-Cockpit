"""AGP_KIT_INVOCATION_GUARD_V1 (owner 2026-10-20, option a): every real Kit call of a work order
is checked against the approval before the Kit starts.

The approval is decided on the work order's source. A call the source analysis cannot read
(``[*BASE, "push-current"]``, a computed program name, a command assembled at run time) used
to run unchecked. While ``Download/run_next.py`` executes a work order, a small ``agentic-kit``
guard stands first on PATH. For each call it resolves the manifest command and decides, with
the same rules as the source analysis, whether the call needs an approval:

* a remote-effect command (an execute-gated one only with an execute flag);
* the signed ``--execute`` of a destructive or owner-decision route;
* the ``--execute`` of a route the Cockpit never runs (always refused).

Such a call runs only when the approval that admitted the work order covers its command name
and, for an exact approval (AGP_EXACT_COMMAND_APPROVAL_V1), its exact line. Otherwise the guard
prints ``AGP_KIT_GUARD_REFUSED`` and exits 126 without starting the Kit. Calls of an approved
Kit process (the Kit calling itself) pass. Every decision is appended to ``invocations.jsonl``.

The guard is not a sandbox: the work order is Python and could reach the Kit by a path. The
source rules (``kit_bypass_violations``) refuse those forms; the guard closes the dynamic gap.
"""

from __future__ import annotations

import json
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.core.kit_command_catalog import (
    DESTRUCTIVE_EXECUTE_COMMANDS,
    EXECUTE_FLAG,
    EXECUTE_FLAGS,
    EXECUTE_GATED_REMOTE_COMMANDS,
    FORBIDDEN_EXECUTE_COMMANDS,
    OWNER_DECISION_EXECUTE_COMMANDS,
    KitCommandCatalog,
)

REFUSED_RETURNCODE = 126
LOG_NAME = "invocations.jsonl"
FREE, REMOTE, REMOTE_ON_EXECUTE, EXECUTE, FORBIDDEN_EXECUTE = (
    "free", "remote", "remote_on_execute", "execute", "forbidden_execute")


@dataclass(frozen=True)
class KitApprovals:
    """What the approval that admitted a work order covers."""
    names: tuple[str, ...] = ()
    lines: tuple[str, ...] | None = None

    def as_dict(self) -> dict:
        return {"names": list(self.names), "lines": None if self.lines is None else list(self.lines)}


def requirement_table(catalog: KitCommandCatalog | None) -> dict[str, str]:
    """``"transfer push-current" -> "remote"`` for every manifest command."""
    table: dict[str, str] = {}
    for command in () if catalog is None else catalog.commands:
        path = " ".join(str(p) for p in command["path"])
        if path in FORBIDDEN_EXECUTE_COMMANDS:
            kind = FORBIDDEN_EXECUTE
        elif catalog.has_remote_effect(command):
            kind = REMOTE_ON_EXECUTE if path in EXECUTE_GATED_REMOTE_COMMANDS else REMOTE
        elif path in DESTRUCTIVE_EXECUTE_COMMANDS | OWNER_DECISION_EXECUTE_COMMANDS:
            kind = EXECUTE
        else:
            kind = FREE
        table[path] = kind
    return table


def build_policy(catalog: KitCommandCatalog | None, approvals: KitApprovals, *, real_kit: Path | None,
                 log_path: Path) -> dict:
    return {
        "schema_version": 1,
        "table": requirement_table(catalog),
        "approvals": approvals.as_dict(),
        "real_kit": "" if real_kit is None else str(real_kit),
        "log": str(log_path),
        "inner_token": secrets.token_hex(16),
        "execute_flag": EXECUTE_FLAG,
        "execute_flags": list(EXECUTE_FLAGS),
        "refused_returncode": REFUSED_RETURNCODE,
    }


# The guard runs as its own script with the Kit's interpreter (the packaged app carries no .py
# sources), so it is standard library only. ``decide`` is also imported by the tests.
SHIM_SOURCE = r'''
import json, os, sys, time

INNER = "AGP_KIT_GUARD_INNER"


def decide(policy, args):
    """(need, refusal): the approval name the call needs, and why it is refused ("" = runs)."""
    tokens = []
    for token in args:
        if token.startswith("-"):
            break
        tokens.append(token)
    path = ""
    for size in range(len(tokens), 0, -1):
        if " ".join(tokens[:size]) in policy["table"]:
            path = " ".join(tokens[:size])
            break
    if not path:
        return "", ""
    kind = policy["table"][path]
    qualified = "agentic-kit " + path
    executes = policy["execute_flag"] in args
    may_execute = any(flag in arg for arg in args for flag in policy["execute_flags"])
    need = ""
    if kind == "forbidden_execute" and executes:
        return qualified + " " + policy["execute_flag"], "the Cockpit never runs this execute"
    if kind == "remote" or (kind == "remote_on_execute" and may_execute):
        need = qualified
    elif kind == "execute" and executes:
        need = qualified + " " + policy["execute_flag"]
    if not need:
        return "", ""
    approvals = policy["approvals"]
    if need not in approvals["names"]:
        return need, "no approval of this work order covers " + need
    line = " ".join(["agentic-kit", *args])
    if approvals["lines"] is not None and line not in approvals["lines"]:
        return need, "the exact approval covers only: " + " | ".join(approvals["lines"])
    return need, ""


def _log(policy, record):
    try:
        with open(policy["log"], "a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass


def main(policy):
    args = sys.argv[1:]
    line = " ".join(["agentic-kit", *args])
    inner = os.environ.get(INNER) == policy["inner_token"]
    need, refusal = ("", "") if inner else decide(policy, args)
    record = {"time": time.time(), "line": line, "need": need, "inner": inner,
              "decision": "REFUSED" if refusal else "RUN"}
    if refusal:
        record["reason"] = refusal
        _log(policy, record)
        sys.stderr.write("AGP_KIT_GUARD_REFUSED: " + line + "\n  " + refusal + "\n"
                         "  The Kit did not start. Ask for an approval of exactly this call.\n")
        sys.exit(policy["refused_returncode"])
    _log(policy, record)
    real = policy["real_kit"]
    if not real:
        sys.stderr.write("AGP_KIT_GUARD: agentic-kit is not installed for this repository\n")
        sys.exit(127)
    env = dict(os.environ)
    env[INNER] = policy["inner_token"]
    try:
        os.execve(real, [real, *args], env)
    except OSError as exc:
        sys.stderr.write("AGP_KIT_GUARD: agentic-kit could not be started: %s\n" % exc)
        sys.exit(127)
'''


def install(directory: Path, policy: dict, *, interpreter: str) -> Path:
    """Write the guard as ``<directory>/agentic-kit`` and return ``directory`` (for PATH).

    ``agentic-kit`` is a POSIX shell launcher (a shebang cannot carry an interpreter path with
    spaces); it runs ``agp_kit_guard.py`` with ``interpreter``.
    """
    import shlex

    directory.mkdir(parents=True, exist_ok=True)
    Path(policy["log"]).parent.mkdir(parents=True, exist_ok=True)
    Path(policy["log"]).write_text("", encoding="utf-8")   # one log per run of the step
    guard = directory / "agp_kit_guard.py"
    guard.write_text(
        "# AGP_KIT_INVOCATION_GUARD_V1: generated by the Cockpit for one work order.\n"
        + SHIM_SOURCE
        + f"\nif __name__ == '__main__':\n    main(json.loads({json.dumps(json.dumps(policy))}))\n",
        encoding="utf-8",
    )
    launcher = directory / "agentic-kit"
    launcher.write_text(
        "#!/bin/sh\n# AGP_KIT_INVOCATION_GUARD_V1\n"
        f"exec {shlex.quote(interpreter)} -I {shlex.quote(str(guard))} \"$@\"\n",
        encoding="utf-8",
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return directory


def guard_interpreter(real_kit: Path | None, fallback: str) -> str:
    """The Kit's own interpreter (its entry point's shebang), else ``fallback``."""
    if real_kit is not None:
        from agp_cockpit.core.kit_installation import _interpreter
        parts = _interpreter(real_kit)
        if parts and len(parts) == 1 and Path(parts[0]).is_file() and os.access(parts[0], os.X_OK):
            return parts[0]
        sibling = real_kit.parent / "python"
        if sibling.is_file() and os.access(sibling, os.X_OK):
            return str(sibling)
    return fallback


def read_log(log_path: Path) -> list[dict]:
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records = []
    for line in lines:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def decide(policy: dict, args: list[str]) -> tuple[str, str]:
    """The guard's decision, from the same source the guard script runs."""
    namespace: dict = {}
    exec(compile(SHIM_SOURCE, "<agp-kit-guard>", "exec"), namespace)   # noqa: S102 - own constant
    return namespace["decide"](policy, args)
