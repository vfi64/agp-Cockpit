"""Facts the Cockpit checks itself before the owner approves (AGP_DECISION_FACTS_V1).

Owner 2026-10-06 (Kit slice GF-050 B): the approval box showed only the remote
side's question; whether its claims about branch, commit and files were true had
to be checked in the terminal. The box now carries the repository's own facts,
read with read-only git (no fetch, no optional locks): branch, HEAD, commits
ahead of the last fetched origin/main, files changed with +/- lines, and
uncommitted changes. „Änderungen ansehen“ shows the same diff in full.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

BASE_REF = "refs/remotes/origin/main"
DIFF_LIMIT = 400_000          # characters shown in the diff window


@dataclass(frozen=True)
class WorkFacts:
    ok: bool
    branch: str = ""
    head: str = ""
    base: str = ""                       # merge base with origin/main
    commits: int | None = None           # commits on HEAD not in origin/main
    files: int = 0                       # files changed in those commits
    insertions: int = 0
    deletions: int = 0
    uncommitted: tuple[str, ...] = ()    # porcelain lines of the working tree
    error: str = ""


def _git(root: Path, runner, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    try:
        return runner(["git", *args], cwd=str(root), env=env, text=True, capture_output=True,
                      timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 127, "", f"{type(exc).__name__}: {exc}")


def _numstat(text: str) -> tuple[int, int, int]:
    files = insertions = deletions = 0
    for line in text.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        files += 1
        insertions += int(parts[0]) if parts[0].isdigit() else 0   # "-" for binary files
        deletions += int(parts[1]) if parts[1].isdigit() else 0
    return files, insertions, deletions


def observe(root: Path, *, runner=subprocess.run) -> WorkFacts:
    root = Path(root)
    head = _git(root, runner, "rev-parse", "HEAD")
    if head.returncode != 0:
        return WorkFacts(False, error="kein Git-Stand lesbar")
    branch = _git(root, runner, "branch", "--show-current").stdout.strip() or "(detached)"
    status = _git(root, runner, "status", "--porcelain")
    uncommitted = tuple(line for line in status.stdout.splitlines() if line.strip())
    base = _git(root, runner, "merge-base", "HEAD", BASE_REF)
    if base.returncode != 0:
        return WorkFacts(True, branch, head.stdout.strip(), uncommitted=uncommitted,
                         error="origin/main lokal nicht bekannt")
    base_sha = base.stdout.strip()
    count = _git(root, runner, "rev-list", "--count", f"{BASE_REF}..HEAD")
    commits = int(count.stdout.strip()) if count.returncode == 0 and count.stdout.strip().isdigit() else None
    files, insertions, deletions = _numstat(_git(root, runner, "diff", "--numstat", base_sha, "HEAD").stdout)
    return WorkFacts(True, branch, head.stdout.strip(), base_sha, commits, files, insertions,
                     deletions, uncommitted)


def facts_line(facts: WorkFacts) -> str:
    """One German line; every number comes from git, none from the remote side."""
    if not facts.ok:
        return f"Vom Cockpit geprüft: {facts.error}."
    parts = [f"Branch {facts.branch} @ {facts.head[:12]}"]
    if facts.base:
        commits = "?" if facts.commits is None else str(facts.commits)
        parts.append(f"{commits} Commit(s) vor origin/main")
        parts.append(f"{facts.files} Datei(en) (+{facts.insertions} −{facts.deletions})")
    else:
        parts.append(facts.error)
    parts.append(f"{len(facts.uncommitted)} nicht committete Änderung(en)" if facts.uncommitted
                 else "Arbeitsbaum sauber")
    return "Vom Cockpit geprüft: " + " · ".join(parts) + "."


def diff_text(root: Path, facts: WorkFacts, *, runner=subprocess.run, limit: int = DIFF_LIMIT) -> str:
    """The committed changes against origin/main, then the uncommitted ones (read-only)."""
    root = Path(root)
    sections = [facts_line(facts), ""]
    if facts.base:
        sections.append(f"=== Commits auf {facts.branch} seit origin/main ===")
        sections.append(_git(root, runner, "log", "--oneline", f"{BASE_REF}..HEAD").stdout.rstrip()
                        or "(keine)")
        sections.append("")
        sections.append(f"=== Änderungen {facts.base[:12]}..{facts.head[:12]} ===")
        sections.append(_git(root, runner, "diff", "--stat", facts.base, "HEAD").stdout.rstrip() or "(keine)")
        sections.append(_git(root, runner, "diff", facts.base, "HEAD").stdout.rstrip())
    if facts.uncommitted:
        sections.append("")
        sections.append("=== Nicht committet ===")
        sections.append("\n".join(facts.uncommitted))
        sections.append(_git(root, runner, "diff", "HEAD").stdout.rstrip())
    text = "\n".join(sections).rstrip() + "\n"
    if len(text) > limit:
        text = text[:limit] + f"\n…[gekürzt: {len(text) - limit} Zeichen mehr; vollständig mit git diff]\n"
    return text
