"""Guard against a second pull request for an already merged branch.

AGP_MERGED_BRANCH_GUARD_V1 (live 2026-10-02, steps 1573/1574): step 1573 ran
``transfer pr-create-complete --post-merge-complete`` successfully (PR #147
merged, refresh #148, post-merge PASS). The remote side could not see that
in its own bundle and ran the same command again as a "recheck"; the Kit
opened PR #149 for the squash-merged branch and merged an empty commit after a
second CI round.

A branch "adds nothing" to its base when every path it changed since the merge
base is identical in the base. Plain ``git diff`` on local refs, no network,
any git version; when a ref is missing or git fails the answer is unknown and
nothing is blocked (fail-open: the Kit still decides).
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

PR_OPENING_PREFIX = "pr-create"


def _git(root: Path, runner, *args: str) -> subprocess.CompletedProcess | None:
    try:
        return runner(["git", *args], cwd=str(root), text=True, capture_output=True,
                      timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _value(argv: list[str], flag: str) -> str | None:
    for index, word in enumerate(argv):
        if word == flag and index + 1 < len(argv):
            return argv[index + 1]
        if word.startswith(flag + "="):
            return word.split("=", 1)[1]
    return None


def pr_openings(source: str) -> list[tuple[str | None, str]]:
    """(head, base) of every ``agentic-kit transfer pr-create*`` invocation;
    head None means the current branch."""
    from agp_cockpit.core.kit_command_catalog import _invocations, _program

    found = []
    for argv in _invocations(ast.parse(source)):
        if not argv or _program(argv[0]) != "agentic-kit" or "transfer" not in argv:
            continue
        words = [w for w in argv[1:] if not w.startswith("-")]
        if len(words) < 2 or words[0] != "transfer" or not words[1].startswith(PR_OPENING_PREFIX):
            continue
        head = _value(argv, "--head")
        base = _value(argv, "--base") or "main"
        if head in (None, "current"):
            head = None
        if head == "<expr>" or base == "<expr>":
            continue
        found.append((head, base))
    return found


def current_branch(root: Path, *, runner=subprocess.run) -> str | None:
    completed = _git(root, runner, "branch", "--show-current")
    name = (completed.stdout or "").strip() if completed and completed.returncode == 0 else ""
    return name or None


NO_COMMITS = "no own commits"
MERGED = "adds nothing to origin/main (already merged)"
CHANGES = "has changes not in origin/main"


def resolve(root: Path, branch: str, *, runner=subprocess.run) -> str | None:
    """The local branch, else its remote-tracking ref (live 1574: the Kit had
    deleted the local branch after the merge, ``origin/<branch>`` remained)."""
    for ref in (branch, f"origin/{branch}"):
        completed = _git(root, runner, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        if completed is not None and completed.returncode == 0:
            return ref
    return None


def relation(root: Path, branch: str, base: str = "origin/main", *,
             runner=subprocess.run) -> str | None:
    """NO_COMMITS, MERGED or CHANGES of ``branch`` against ``base``; None when
    unknown."""
    ref = resolve(root, branch, runner=runner)
    if ref is None:
        return None
    merge_base = _git(root, runner, "merge-base", base, ref)
    if merge_base is None or merge_base.returncode != 0 or not merge_base.stdout.strip():
        return None
    count = _git(root, runner, "rev-list", "--count", f"{base}..{ref}")
    if count is not None and count.returncode == 0 and count.stdout.strip() == "0":
        return NO_COMMITS
    changed = _git(root, runner, "diff", "--name-only", merge_base.stdout.strip(), ref)
    if changed is None or changed.returncode != 0:
        return None
    paths = [line for line in changed.stdout.splitlines() if line.strip()]
    if not paths:
        return MERGED
    compared = _git(root, runner, "diff", "--quiet", base, ref, "--", *paths)
    if compared is None or compared.returncode not in (0, 1):
        return None
    return MERGED if compared.returncode == 0 else CHANGES


def adds_nothing(root: Path, branch: str, base: str = "origin/main", *,
                 runner=subprocess.run) -> bool | None:
    """True when ``branch`` changes nothing that ``base`` does not already
    contain; None when unknown."""
    found = relation(root, branch, base, runner=runner)
    return None if found is None else found in (NO_COMMITS, MERGED)


FORCE_SCOPES = ("transfer", "work", "pr")


def force_violations(source: str) -> list[str]:
    """AGP_NO_FORCE_V1 (R4): no force option on publishing Kit commands."""
    from agp_cockpit.core.kit_command_catalog import _invocations, _program

    found = []
    for argv in _invocations(ast.parse(source)):
        if not argv or _program(argv[0]) != "agentic-kit":
            continue
        words = [w for w in argv[1:] if not w.startswith("-")]
        if words and words[0] in FORCE_SCOPES and any(w.startswith("--force") for w in argv[1:]):
            found.append(f"force option on agentic-kit {' '.join(words[:2])} is never allowed "
                         "(AGP_NO_FORCE_V1)")
    return sorted(set(found))


def _worktree_clean(root: Path, runner) -> bool:
    status = _git(root, runner, "status", "--porcelain")
    return status is not None and status.returncode == 0 and not status.stdout.strip()


def violations(source: str, repository_root: Path | None, *, runner=subprocess.run) -> list[str]:
    """Only MERGED blocks: a branch without own commits, or the current branch
    with uncommitted changes, may still get commits from the same work order
    before it opens the pull request."""
    if repository_root is None:
        return []
    root = Path(repository_root)
    openings = pr_openings(source)
    if not openings:
        return []
    current = current_branch(root, runner=runner)
    found = []
    for head, base in openings:
        branch = head or current
        if not branch or branch == base:
            continue
        if relation(root, branch, f"origin/{base}", runner=runner) != MERGED:
            continue
        if branch == current and not _worktree_clean(root, runner):
            continue
        found.append(
            f"merged-branch guard (AGP_MERGED_BRANCH_GUARD_V1): every change of {branch} is "
            f"already in origin/{base} — its pull request is merged. Do not open another pull "
            "request for it; if the lifecycle after the merge is complete, return DONE."
        )
    return found


# AGP_REPOSITORY_FACTS_V1: the continuation after every local step carries
# facts the Cockpit read itself, so the remote side never has to re-run a
# remote-effect command to find out whether a pull request is merged.

def _short(root: Path, runner, ref: str) -> str | None:
    completed = _git(root, runner, "rev-parse", "--short=12", "--verify", "--quiet", ref)
    value = (completed.stdout or "").strip() if completed and completed.returncode == 0 else ""
    return value or None


def _pull_requests(root: Path, branch: str, gh: str | None, runner) -> str | None:
    if not gh:
        return None
    try:
        completed = runner([gh, "pr", "list", "--head", branch, "--state", "all", "--limit", "5",
                            "--json", "number,state"], cwd=str(root), text=True,
                           capture_output=True, timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    try:
        import json
        items = json.loads(completed.stdout or "[]")
    except ValueError:
        return None
    return ", ".join(f"#{i.get('number')} {i.get('state')}" for i in items if isinstance(i, dict)) or "none"


def repository_facts(root: Path, command_source: str | None = None, *,
                     runner=subprocess.run, gh: str | None = None) -> str | None:
    """One line of locally verified facts, or None outside a git work tree."""
    root = Path(root)
    head = _short(root, runner, "HEAD")
    if head is None:
        return None
    branch = current_branch(root, runner=runner) or "(detached)"
    origin_main = _short(root, runner, "origin/main")
    main = _short(root, runner, "main")
    clean = _worktree_clean(root, runner)
    parts = [f"current branch {branch} at {head}",
             f"origin/main {origin_main or 'unknown'}",
             f"main equals origin/main: {'yes' if main and main == origin_main else 'no'}",
             f"worktree clean: {'yes' if clean else 'no'}"]
    merged = []
    heads = []
    if command_source:
        try:
            heads = [h or branch for h, _ in pr_openings(command_source)]
        except SyntaxError:
            heads = []
    if branch not in ("main", "(detached)"):
        heads.append(branch)
    for name in dict.fromkeys(heads):
        if name in ("main", "(detached)"):
            continue
        found = relation(root, name, "origin/main", runner=runner)
        pulls = _pull_requests(root, name, gh, runner)
        parts.append(f"{name} {found or 'not comparable (ref missing)'}"
                     + (f" (pull requests: {pulls})" if pulls else ""))
        if found == MERGED:
            merged.append(name)
    line = "Cockpit-verified repository facts (local git): " + "; ".join(parts) + "."
    if merged:
        line += (" A pull request for " + ", ".join(merged) + " is not needed again; "
                 "never re-run a remote-effect command to check a result.")
    return line
