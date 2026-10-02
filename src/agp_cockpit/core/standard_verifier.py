"""Local completion verifiers of standard tasks (AGP_STANDARD_VERIFIER_V1).

A remote DONE of a standard task with ``completion_contract.kind ==
KIND`` is only a request: the bridge runs the named verifier against the
local repository and accepts DONE only when it passes; otherwise the task
continues with the finding (bounded by MAX_CHECKS, then NEEDS_HUMAN).
Verifiers read local git state (and, for "recovered", the Cockpit's own
Lagebericht); they never call the remote side.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

KIND = "agp-standard-verifier-v1"
MAX_CHECKS = 3


def _git(root: Path, *args: str, runner=subprocess.run) -> subprocess.CompletedProcess | None:
    try:
        return runner(["git", *args], cwd=str(root), text=True, capture_output=True,
                      timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _out(done) -> str:
    return (done.stdout or "").strip() if done is not None and done.returncode == 0 else ""


def verify_work_started(root: Path, *, branch: str, runner=subprocess.run) -> tuple[bool, str]:
    current = _out(_git(root, "branch", "--show-current", runner=runner))
    if current != branch:
        return False, f"current branch is {current or '(none)'}, expected {branch}"
    contains = _git(root, "merge-base", "--is-ancestor", "origin/main", "HEAD", runner=runner)
    if contains is None or contains.returncode != 0:
        return False, f"{branch} does not contain the current origin/main"
    if _out(_git(root, "status", "--porcelain", runner=runner)):
        return False, "the worktree is not clean"
    return True, f"{branch} checked out from origin/main, worktree clean"


def verify_recovered(root: Path, *, lagebericht=None) -> tuple[bool, str]:
    from agp_cockpit.core import repo_state as rs
    observe = lagebericht or rs.lagebericht
    state = observe(root)
    if state.state in (rs.BEREIT, rs.IN_ARBEIT):
        return True, f"Lagebericht {state.state}: {state.summary}"
    return False, f"Lagebericht {state.state}: {state.summary}"


def verify(root: Path, contract: dict, **kw) -> tuple[bool, str]:
    name = str(contract.get("verifier") or "")
    params = dict(contract.get("params") or {})
    if name == "work-started":
        return verify_work_started(Path(root), branch=str(params.get("branch") or ""),
                                   runner=kw.get("runner", subprocess.run))
    if name == "recovered":
        return verify_recovered(Path(root), lagebericht=kw.get("lagebericht"))
    return False, f"unknown standard verifier {name!r}"


def contract_of(store, task_id: str) -> dict | None:
    """The task's verifier contract from its durable runtime contract."""
    record = store.runtime_contract(task_id) or {}
    try:
        scope = json.loads(record.get("scope_json") or "{}")
    except ValueError:
        return None
    contract = scope.get("completion_contract") if isinstance(scope, dict) else None
    return contract if isinstance(contract, dict) and contract.get("kind") == KIND else None


class VerifierChecks:
    """Bounded count of rejected DONE replies per task."""

    def __init__(self, runtime_root: Path) -> None:
        self.path = Path(runtime_root) / "standard-verifier.json"

    def bump(self, task_id: str) -> int:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8")) if self.path.is_file() else {}
        except (OSError, ValueError):
            data = {}
        data[task_id] = int(data.get(task_id, 0)) + 1
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
        return data[task_id]
