"""A task that published work is complete only when GitHub is green.

AGP_CI_GREEN_COMPLETION_V1 (live 2026-10-01, steps 1497-1500): the approved
push ran, the remote side declared DONE, the Cockpit accepted it, and the CI
run of the pushed commit (Agentic Gate #481) was red. A remote DONE is only a
request. Once a task has executed a Kit command that publishes (push, PR,
merge lifecycle), the Cockpit verifies the result itself before it accepts
DONE, with the Kit as command authority:

* open pull request: ``agentic-kit pr status <pr> --json`` must report green
  for exactly the local HEAD;
* merge lifecycle (AGP_CI_LIFECYCLE_COMPLETION_V2, live 1501-1519): when a
  merging Kit command ran (or the PR is merged), DONE needs the PR merged, the
  local main equal to origin/main, ``agentic-kit transfer post-merge-check``
  PASS (handoff refresh and successor package current) and green CI for the
  origin/main head. The CI of a branch head has no Kit read command; that one
  read uses ``gh run list`` (documented Kit gap);
* anything else rejects the DONE and the finding, with the failed-run log
  excerpt, goes back to the remote side as the next instruction. The
  instruction names the goal, never a concrete Kit command: the remote side
  chooses from the command digest, orchestrators first;
* bounded: after MAX_RED_HEADS red commits or MAX_CHECKS rejected DONEs the
  mission ends with NEEDS_HUMAN and the exact reason.

Evidence of every check is written to ``.local/agp-cockpit/ci/<head>.json``.
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

MAX_RED_HEADS = 3          # repair attempts: distinct commits whose CI was red
MAX_CHECKS = 12            # rejected DONE replies per task (pending loops included)
REPAIR_BUDGET = 6          # remote-effect work orders an approval allows after the first one
LOG_EXCERPT_CHARS = 6_000
TOOL_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")

# Remote-effect Kit commands that publish work; one of them activates the gate.
PUBLISHING_COMMANDS = frozenset({
    "agentic-kit transfer push-current",
    "agentic-kit transfer pr-create",
    "agentic-kit transfer pr-create-complete",
    "agentic-kit transfer pr-complete",
    "agentic-kit transfer pr-closeout-complete",
    "agentic-kit transfer post-merge-complete",
    "agentic-kit transfer evidence-pr-complete",
    "agentic-kit transfer admin-refresh-pr",
    "agentic-kit work finish",
    "agentic-kit pr merge-if-green",
})
# Commands that merge; after one of them DONE needs the merged lifecycle.
MERGE_COMMANDS = frozenset({
    "agentic-kit transfer pr-create-complete",
    "agentic-kit transfer pr-complete",
    "agentic-kit transfer pr-closeout-complete",
    "agentic-kit transfer post-merge-complete",
    "agentic-kit work finish",
    "agentic-kit pr merge-if-green",
})
# What the repair budget of an approval may re-run without asking again.
REPAIR_PUSH_COMMANDS = frozenset(
    {"agentic-kit transfer push-current", "agentic-kit transfer pr-create"}
)
LIFECYCLE_COMMANDS = PUBLISHING_COMMANDS | frozenset({"agentic-kit transfer sync-main"})


def merge_expected(used, content: str) -> bool:
    """A merging command ran (``work finish --no-merge`` does not merge)."""
    merging = set(used) & MERGE_COMMANDS
    if not merging:
        return False
    return not (merging == {"agentic-kit work finish"} and "--no-merge" in content)


def tool_env(repository_root: Path, base: dict | None = None) -> dict:
    """Environment for local Kit runs.

    An app started from Finder/``open`` gets the minimal macOS PATH, without
    Homebrew; the Kit needs ``gh`` for every CI and PR query.
    """
    env = dict(os.environ if base is None else base)
    parts = [str(Path(repository_root) / ".venv" / "bin")]
    parts += [d for d in TOOL_DIRS if Path(d).is_dir()]
    parts += [p for p in env.get("PATH", "").split(os.pathsep) if p]
    seen: list[str] = []
    for part in parts:
        if part not in seen:
            seen.append(part)
    env["PATH"] = os.pathsep.join(seen)
    return env


class CiGateStore:
    def __init__(self, runtime_root: Path) -> None:
        self.path = Path(runtime_root) / "ci-gate.json"

    def _load(self) -> dict:
        if not self.path.is_file():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    def _save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, sort_keys=True, indent=1), encoding="utf-8")
        temporary.replace(self.path)

    def get(self, task_id: str) -> dict:
        return dict(self._load().get(task_id) or {})

    def required(self, task_id: str) -> bool:
        return bool(task_id) and bool(self.get(task_id).get("required"))

    def _update(self, task_id: str, **changes) -> dict:
        data = self._load()
        entry = dict(data.get(task_id) or {})
        entry.update(changes)
        data[task_id] = entry
        self._save(data)
        return entry

    def activate(self, task_id: str, *, reason: str, merge: bool = False) -> dict:
        entry = self.get(task_id)
        if entry.get("required"):
            if merge and not entry.get("merge_expected"):
                return self._update(task_id, merge_expected=True)
            return entry
        return self._update(task_id, required=True, activated_by=reason, red_heads=[],
                            checks=0, pr=None, verified_head=None, merge_expected=bool(merge))

    def record_check(self, task_id: str, *, head: str, pr: int | None, verdict: str) -> dict:
        entry = self.get(task_id)
        red_heads = list(entry.get("red_heads") or [])
        if verdict == "red" and head and head not in red_heads:
            red_heads.append(head)
        changes = {"checks": int(entry.get("checks") or 0) + 1, "red_heads": red_heads,
                   "last_head": head, "last_verdict": verdict}
        if pr:
            changes["pr"] = int(pr)
        if verdict == "green":
            changes["verified_head"] = head
        return self._update(task_id, **changes)


@dataclass(frozen=True)
class CiVerdict:
    kind: str  # green | red | pending | no-pr | behind | not-merged | unpublished | closeout | blocked
    summary: str
    log_excerpt: str = ""
    failed_checks: tuple[str, ...] = ()


Runner = Callable[..., object]


def _run(argv, repository_root: Path, runner: Runner, timeout: int = 180):
    try:
        return runner(argv, cwd=str(repository_root), env=tool_env(repository_root),
                      text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"{type(exc).__name__}: {exc}")


def _json_from(stdout: str):
    pairs = [("{", "}"), ("[", "]")]
    pairs.sort(key=lambda pair: (stdout.find(pair[0]) < 0, stdout.find(pair[0])))
    for opening, closing in pairs:
        start, end = stdout.find(opening), stdout.rfind(closing)
        if start < 0 or end < start:
            continue
        try:
            return json.loads(stdout[start:end + 1])
        except json.JSONDecodeError:
            continue
    return None


def run_pr_status(repository_root: Path, kit_binary: Path, pr: int, *,
                  runner: Runner = subprocess.run) -> dict:
    argv = [str(kit_binary), "pr", "status", str(int(pr)), "--json", "--failed-log-lines", "80"]
    completed = _run(argv, repository_root, runner)
    data = _json_from(completed.stdout or "")
    if completed.returncode != 0 or not isinstance(data, dict):
        return {"decision": "error", "argv": argv, "returncode": completed.returncode,
                "error": ((completed.stderr or completed.stdout or "").strip()[-2000:]
                          or "no JSON from agentic-kit pr status")}
    data["argv"] = argv
    return data


def git_value(repository_root: Path, *args: str, runner: Runner = subprocess.run) -> str:
    completed = _run(["git", *args], repository_root, runner, timeout=60)
    return (completed.stdout or "").strip() if completed.returncode == 0 else ""


def remote_refs(repository_root: Path, *, runner: Runner = subprocess.run) -> dict | None:
    """All refs of origin (branches, tags, pull/*), or None when unreadable.

    AGP_EFFECT_REFUND_V1 (live 1504-1513): a Kit run that the Kit itself
    blocked before any mutation consumed approval budget. Comparing the refs
    of origin before and after a run shows, independent of the remote side's
    own bundle, whether anything changed on GitHub (a push, a new pull
    request ref, a merge, a new branch).
    """
    completed = _run(["git", "ls-remote", "origin"], repository_root, runner, timeout=60)
    if completed.returncode != 0:
        return None
    refs = {}
    for line in (completed.stdout or "").splitlines():
        parts = line.split()
        if len(parts) == 2:
            refs[parts[1]] = parts[0]
    return refs


def evaluate(decision: dict, *, head: str) -> CiVerdict:
    """Open pull request: green for exactly the local HEAD."""
    kind = str(decision.get("decision") or "error")
    pr_head = str(decision.get("head_ref_oid") or "")
    if kind == "error":
        return CiVerdict("blocked", "CI status could not be read: " + str(decision.get("error") or "")[:500])
    if kind == "not-open":
        return CiVerdict("blocked", f"the pull request is not open (state {decision.get('state')})")
    if pr_head and head and pr_head != head:
        return CiVerdict("behind", f"the pull request head {pr_head[:12]} is not the local HEAD {head[:12]}")
    if kind == "green":
        return CiVerdict("green", "all required checks of the pull request passed")
    if kind in {"pending", "no-checks", "stale"}:
        return CiVerdict("pending", f"the pull request CI is not finished ({kind})")
    if kind == "red":
        failed = tuple(str(x) for x in decision.get("failed_checks") or ())
        parts = []
        for item in decision.get("failed_run_diagnostics") or ():
            if isinstance(item, dict):
                parts.append(f"## {item.get('check_name')} ({item.get('conclusion')}) {item.get('details_url') or ''}\n"
                             f"{item.get('log_excerpt') or item.get('error') or ''}")
        excerpt = "\n".join(parts)[-LOG_EXCERPT_CHARS:]
        return CiVerdict("red", "failed checks: " + (", ".join(failed) or "unknown"), excerpt, failed)
    return CiVerdict("blocked", f"CI status is {kind}")


FAILED_CONCLUSIONS = frozenset({"failure", "cancelled", "timed_out", "action_required", "startup_failure"})


def main_ci(repository_root: Path, sha: str, *, runner: Runner = subprocess.run) -> CiVerdict:
    """CI of a commit on main (no Kit read command exists for a branch head)."""
    argv = ["gh", "run", "list", "--commit", sha, "--limit", "50",
            "--json", "databaseId,status,conclusion,workflowName,event"]
    completed = _run(argv, repository_root, runner)
    runs = _json_from(completed.stdout or "")
    if completed.returncode != 0 or not isinstance(runs, list):
        return CiVerdict("blocked", "main CI could not be read: "
                         + (completed.stderr or completed.stdout or "").strip()[-400:])
    if not runs:
        return CiVerdict("pending", f"no CI run for main {sha[:12]} yet")
    failed = [r for r in runs if str(r.get("conclusion") or "").lower() in FAILED_CONCLUSIONS]
    if failed:
        parts = []
        for run in failed[:3]:
            log = _run(["gh", "run", "view", str(run.get("databaseId")), "--log-failed"],
                       repository_root, runner)
            tail = "\n".join((log.stdout or log.stderr or "").splitlines()[-80:])
            parts.append(f"## {run.get('workflowName')} ({run.get('conclusion')}) run "
                         f"{run.get('databaseId')}\n{tail}")
        names = tuple(str(r.get("workflowName")) for r in failed)
        return CiVerdict("red", f"main CI failed for {sha[:12]}: " + ", ".join(names),
                         "\n".join(parts)[-LOG_EXCERPT_CHARS:], names)
    if any(str(r.get("status") or "").lower() != "completed" for r in runs):
        return CiVerdict("pending", f"main CI for {sha[:12]} is not finished")
    return CiVerdict("green", f"main CI green for {sha[:12]}")


def verify_merged(repository_root: Path, kit_binary: Path, *, pr_decision: dict,
                  work_head: str = "", runner: Runner = subprocess.run) -> tuple[CiVerdict, dict]:
    """Merge lifecycle: PR merged with the local work, local main synced, Kit
    closeout PASS, main CI green."""
    facts: dict = {"pr_state": pr_decision.get("state"), "work_head": work_head,
                   "pr_head": pr_decision.get("head_ref_oid")}
    if str(pr_decision.get("decision") or "") == "error":
        return CiVerdict("blocked", "pull request state could not be read: "
                         + str(pr_decision.get("error") or "")[:400]), facts
    if str(pr_decision.get("state") or "") != "MERGED":
        return CiVerdict(
            "not-merged",
            "the task ran a merging Kit command but the pull request is not merged "
            f"(state {pr_decision.get('state')}, CI {pr_decision.get('decision')})",
        ), facts
    pr_head = str(pr_decision.get("head_ref_oid") or "")
    if work_head and pr_head and work_head != pr_head:
        contained = _run(["git", "merge-base", "--is-ancestor", work_head, pr_head],
                         repository_root, runner, timeout=60)
        if contained.returncode != 0:
            return CiVerdict("unpublished", f"the merged pull request (head {pr_head[:12]}) does not "
                             f"contain the local work {work_head[:12]}"), facts
    remote = git_value(repository_root, "ls-remote", "origin", "refs/heads/main", runner=runner).split()
    remote_main = remote[0] if remote else ""
    branch = git_value(repository_root, "branch", "--show-current", runner=runner)
    head = git_value(repository_root, "rev-parse", "HEAD", runner=runner)
    facts.update({"origin_main": remote_main, "branch": branch, "head": head})
    if not remote_main:
        return CiVerdict("blocked", "origin/main could not be read"), facts
    if branch != "main" or head != remote_main:
        return CiVerdict("behind", f"local {branch or '?'} {head[:12]} is not synchronized with "
                         f"origin/main {remote_main[:12]}"), facts
    argv = [str(kit_binary), "transfer", "post-merge-check", "--main-branch", "main", "--json"]
    check = _run(argv, repository_root, runner)
    output = f"{check.stdout or ''}\n{check.stderr or ''}"
    facts["post_merge_check"] = {"returncode": check.returncode, "output": output[-3000:]}
    if check.returncode != 0 or "NEEDS_" in output or "BLOCKED" in output:
        return CiVerdict("closeout", "the Kit post-merge check is not PASS (handoff refresh or "
                         "successor package not current)", output[-LOG_EXCERPT_CHARS:]), facts
    return main_ci(repository_root, remote_main, runner=runner), facts


def write_evidence(repository_root: Path, *, head: str, pr: int | None, decision: dict,
                   verdict: CiVerdict, facts: dict | None = None) -> Path:
    target = Path(repository_root) / ".local" / "agp-cockpit" / "ci" / f"{head or 'unknown'}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"head": head, "pr": pr, "verdict": verdict.kind,
                                  "summary": verdict.summary, "kit_decision": decision,
                                  "lifecycle": facts or {}},
                                 indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return target


_NEXT = {
    "no-pr": "Publish the work as a pull request against main and name it in the DONE file.",
    "pending": "Wait for the CI of the pull request (or of main after a merge) to finish.",
    "behind": ("Bring the published state in line: the pull request head must be the local HEAD "
               "(after a merge: local main synchronized with origin/main)."),
    "not-merged": ("Finish the lifecycle the task asks for: merge the pull request once it is green "
                   "and complete the post-merge closeout."),
    "closeout": ("Complete the post-merge closeout (handoff refresh, successor package refresh pull "
                 "request and its CI) until the Kit post-merge check passes."),
    "red": "Find the cause in the repository and fix it, commit, publish again and wait for the CI.",
    "unpublished": ("The local work is not part of the merged pull request: publish the remaining "
                    "commits and complete the lifecycle (pull request, CI, merge, closeout) again."),
}


def continuation_prompt(verdict: CiVerdict, *, pr: int | None, head: str, branch: str,
                        next_step: int, entry: dict) -> str:
    red_left = MAX_RED_HEADS - len(entry.get("red_heads") or [])
    lines = [
        "AGP COCKPIT — DONE NOT ACCEPTED (local verification)",
        "",
        (
            "This task published work. It is complete only when the Cockpit itself has verified "
            "GitHub: the pull request CI green for the local HEAD and, when a merge was part of "
            "the task, the pull request merged, local main synchronized, the Kit post-merge "
            f"check passing and main green. Branch: {branch or '?'}; local HEAD: {head or '?'}; "
            f"pull request: {('#' + str(pr)) if pr else 'none named'}."
        ),
        f"Finding: {verdict.summary}.",
    ]
    if verdict.log_excerpt:
        lines += ["", "Evidence (from the Kit / CI log):", verdict.log_excerpt, ""]
    lines.append("Goal of the next work order(s): " + _NEXT.get(verdict.kind, "Resolve the finding."))
    if verdict.kind == "red":
        lines.append(f"Remaining repair attempts for red CI: {max(red_left, 0)}.")
    lines += [
        "",
        (
            "Choose the Kit commands yourself from the attached command digest; prefer the most "
            "comprehensive orchestrator that covers the remaining lifecycle and use primitives only "
            "where no orchestrator fits. Raw git push, git fetch, git pull and gh stay forbidden."
        ),
        (
            f"Use exactly {next_step}_...py as the next attachment filename and {next_step} as "
            "STEP. When everything is verified, finish with the terminal file of the step then due "
            '(<step>_agp_terminal.json) containing {"state": "DONE", "reason": "...", '
            '"pr": <pull request number>}.'
        ),
    ]
    return "\n".join(lines)
