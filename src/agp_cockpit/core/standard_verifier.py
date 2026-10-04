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


def verify_released(root: Path, *, version: str, runner=subprocess.run) -> tuple[bool, str]:
    """AGP_RELEASE_VERIFIER_V1 (plan P11): the annotated tag v<version> exists locally
    and on origin (same object), its commit is in origin/main, pyproject.toml at the
    tag names the version, and the worktree is clean."""
    tag = f"v{version}"
    if not _out(_git(root, "rev-parse", "--verify", "--quiet", f"{tag}^{{tag}}", runner=runner)):
        return False, f"no annotated tag {tag}"   # ^{tag} resolves only an annotated tag
    local = _out(_git(root, "rev-parse", f"refs/tags/{tag}", runner=runner))
    remote = _out(_git(root, "ls-remote", "--tags", "origin", f"refs/tags/{tag}", runner=runner))
    if not remote or remote.split()[0] != local:
        return False, f"tag {tag} is not on origin (or differs from the local tag)"
    contained = _git(root, "merge-base", "--is-ancestor", f"{tag}^{{commit}}", "origin/main", runner=runner)
    if contained is None or contained.returncode != 0:
        return False, f"the commit of {tag} is not in origin/main"
    pyproject = _out(_git(root, "show", f"{tag}:pyproject.toml", runner=runner))
    if f'version = "{version}"' not in pyproject:
        return False, f"pyproject.toml at {tag} does not name version {version}"
    if _out(_git(root, "status", "--porcelain", runner=runner)):
        return False, "the worktree is not clean"
    return True, f"tag {tag} on origin at {local[:12]}, release commit in origin/main"


def verify_maintained(root: Path, *, branch: str, runner=subprocess.run) -> tuple[bool, str]:
    """AGP_MAINTENANCE_VERIFIER_V1 (plan P10a): nothing to maintain (main unchanged,
    clean, equal to origin/main) or the maintenance branch from origin/main with changes."""
    current = _out(_git(root, "branch", "--show-current", runner=runner))
    dirty = bool(_out(_git(root, "status", "--porcelain", runner=runner)))
    if current == "main":
        head = _out(_git(root, "rev-parse", "HEAD", runner=runner))
        origin = _out(_git(root, "rev-parse", "--verify", "-q", "refs/remotes/origin/main", runner=runner))
        if dirty:
            return False, "main has uncommitted changes; maintenance changes belong on " + branch
        if not head or head != origin:
            return False, "main differs from origin/main"
        return True, "nothing to maintain: main unchanged, clean and equal to origin/main"
    if current != branch:
        return False, f"current branch is {current or '(none)'}, expected main or {branch}"
    contains = _git(root, "merge-base", "--is-ancestor", "origin/main", "HEAD", runner=runner)
    if contains is None or contains.returncode != 0:
        return False, f"{branch} does not contain the current origin/main"
    ahead = _out(_git(root, "rev-list", "--count", "origin/main..HEAD", runner=runner))
    if not dirty and ahead in ("", "0"):
        return False, f"{branch} carries no changes; a maintenance without changes stays on main"
    return True, f"maintenance changes on {branch}; finish them with Abschließen"


def verify(root: Path, contract: dict, **kw) -> tuple[bool, str]:
    name = str(contract.get("verifier") or "")
    params = dict(contract.get("params") or {})
    if name == "work-started":
        return verify_work_started(Path(root), branch=str(params.get("branch") or ""),
                                   runner=kw.get("runner", subprocess.run))
    if name == "released":
        return verify_released(Path(root), version=str(params.get("version") or ""),
                               runner=kw.get("runner", subprocess.run))
    if name == "maintained":
        return verify_maintained(Path(root), branch=str(params.get("branch") or ""),
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
