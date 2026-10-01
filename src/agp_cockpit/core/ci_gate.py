"""A task that pushed is complete only when its CI is green.

AGP_CI_GREEN_COMPLETION_V1 (live 2026-10-01, steps 1497-1500): the approved
push ran, the remote side declared DONE, the Cockpit accepted it, and the CI
run of the pushed commit (Agentic Gate #481) was red. A remote DONE is only a
request. Once a task has executed a push, the Cockpit verifies the CI itself
before it accepts DONE:

* the remote side names the pull request ("pr" in the DONE file);
* the Cockpit runs ``agentic-kit pr status <pr> --json`` on this machine (the
  Kit is the command authority; it fetches failed-run logs for red checks);
* green for exactly the local HEAD -> DONE (authority ``ci-verified``);
* red -> the DONE is rejected and the failure with its log excerpt goes back
  to the remote side as the next instruction (repair, commit, push, wait);
* pending / no PR / PR head behind HEAD -> the remote side is told to create
  the PR or wait with ``agentic-kit pr wait-ci``;
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
REPAIR_PUSH_COMMANDS = frozenset(
    {"agentic-kit transfer push-current", "agentic-kit transfer pr-create"}
)
LOG_EXCERPT_CHARS = 6_000
TOOL_DIRS = ("/opt/homebrew/bin", "/usr/local/bin")


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

    def activate(self, task_id: str, *, reason: str) -> dict:
        entry = self.get(task_id)
        if entry.get("required"):
            return entry
        return self._update(task_id, required=True, activated_by=reason, red_heads=[],
                            checks=0, pr=None, verified_head=None)

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
    kind: str            # green | red | pending | no-pr | behind | blocked
    summary: str
    log_excerpt: str = ""
    failed_checks: tuple[str, ...] = ()


def run_pr_status(repository_root: Path, kit_binary: Path, pr: int, *,
                  runner: Callable = subprocess.run) -> dict:
    argv = [str(kit_binary), "pr", "status", str(int(pr)), "--json", "--failed-log-lines", "80"]
    try:
        completed = runner(argv, cwd=str(repository_root), env=tool_env(repository_root),
                           text=True, capture_output=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"decision": "error", "error": f"{type(exc).__name__}: {exc}", "argv": argv}
    stdout = completed.stdout or ""
    start, end = stdout.find("{"), stdout.rfind("}")
    if completed.returncode != 0 or start < 0 or end < start:
        return {"decision": "error", "argv": argv, "returncode": completed.returncode,
                "error": (completed.stderr or stdout).strip()[-2000:] or "no JSON from agentic-kit pr status"}
    try:
        data = json.loads(stdout[start:end + 1])
    except json.JSONDecodeError as exc:
        return {"decision": "error", "argv": argv, "error": f"invalid JSON: {exc.msg}"}
    data["argv"] = argv
    return data


def git_value(repository_root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=str(repository_root), text=True,
                               capture_output=True, check=False)
    return completed.stdout.strip() if completed.returncode == 0 else ""


def evaluate(decision: dict, *, head: str) -> CiVerdict:
    kind = str(decision.get("decision") or "error")
    pr_head = str(decision.get("head_ref_oid") or "")
    if kind == "error":
        return CiVerdict("blocked", "CI status could not be read: " + str(decision.get("error") or "")[:500])
    if kind == "not-open":
        return CiVerdict("blocked", f"the pull request is not open (state {decision.get('state')})")
    if pr_head and head and pr_head != head:
        return CiVerdict("behind", f"the pull request head {pr_head[:12]} is not the local HEAD {head[:12]}")
    if kind == "green":
        return CiVerdict("green", "all required checks passed")
    if kind in {"pending", "no-checks", "stale"}:
        return CiVerdict("pending", f"CI is not finished ({kind})")
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


def write_evidence(repository_root: Path, *, head: str, pr: int | None, decision: dict,
                   verdict: CiVerdict) -> Path:
    target = Path(repository_root) / ".local" / "agp-cockpit" / "ci" / f"{head or 'unknown'}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps({"head": head, "pr": pr, "verdict": verdict.kind,
                                  "summary": verdict.summary, "kit_decision": decision},
                                 indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    return target


def continuation_prompt(verdict: CiVerdict, *, pr: int | None, head: str, branch: str,
                        next_step: int, entry: dict) -> str:
    red_left = MAX_RED_HEADS - len(entry.get("red_heads") or [])
    lines = [
        "AGP COCKPIT — DONE NOT ACCEPTED (local CI verification)",
        "",
        (
            "This task pushed commits. It is complete only when the CI of the pull request for "
            "the local HEAD is green; the Cockpit checks that itself with `agentic-kit pr status`. "
            f"Branch: {branch or '?'}; local HEAD: {head or '?'}; pull request: "
            f"{('#' + str(pr)) if pr else 'none named'}."
        ),
        f"Finding: {verdict.summary}.",
    ]
    if verdict.kind == "no-pr":
        lines.append(
            "Next: one work order that creates the pull request with "
            f"`agentic-kit transfer pr-create --head {branch or '<branch>'} --title \"<title>\" --json`, "
            "then waits with `agentic-kit pr wait-ci <pr> --expected-head-sha <HEAD> --timeout-seconds 540`, "
            "and records the PR number in its return bundle."
        )
    elif verdict.kind == "pending":
        lines.append(
            f"Next: one work order that waits with `agentic-kit pr wait-ci {pr} --expected-head-sha {head} "
            "--timeout-seconds 540` and records its full result."
        )
    elif verdict.kind == "behind":
        lines.append(
            "Next: push the local HEAD with `agentic-kit transfer push-current --branch "
            f"{branch or '<branch>'} --json`, then wait with `agentic-kit pr wait-ci {pr} "
            f"--expected-head-sha {head} --timeout-seconds 540`."
        )
    elif verdict.kind == "red":
        lines += [
            "",
            "Failed-run log excerpt (from the Kit):",
            verdict.log_excerpt or "(no log excerpt available)",
            "",
            (
                "Next: find the cause in the repository and fix it. Commit through "
                "`agentic-kit transfer commit`, push with `agentic-kit transfer push-current "
                f"--branch {branch or '<branch>'} --json`, then wait with `agentic-kit pr wait-ci "
                f"{pr} --expected-head-sha <new HEAD> --timeout-seconds 540`. You may split this "
                "into several work orders. Remaining repair attempts for red CI: "
                f"{max(red_left, 0)}."
            ),
        ]
    lines += [
        "",
        (
            f"Use exactly {next_step}_...py as the next attachment filename and {next_step} as "
            "STEP. When the CI is green, finish with the terminal file of the step then due "
            '(<step>_agp_terminal.json) containing {"state": "DONE", "reason": "...", '
            '"pr": <pull request number>}. Raw git push, git fetch and git pull stay forbidden.'
        ),
    ]
    return "\n".join(lines)
