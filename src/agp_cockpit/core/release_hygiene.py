"""Release hygiene enforced on work orders (Release slice, 2026-10-05).

AGP_PR_RELEASE_CATEGORY_V1: with ``publication: github`` the Kit blocks a release while a
merged pull request has no release-note category (between 0.1.1 and 0.2.0, 5 of 13 pull
request titles were unclassified). Every pull request a work order creates therefore carries
a line ``release-note-category: <category>`` in its body, which the Kit reads before the
title. ``agentic-kit work finish`` cannot set a pull-request body (KIT-GF-048), so a work order
creates pull requests with ``agentic-kit transfer pr-create(-complete) --body``.

AGP_RELEASE_CHANGELOG_GATE_V1: on a release branch the pull request is created only after
every entry of the CHANGELOG.md "Unreleased" section was moved into the version section
(release 0.1.1 and 0.2.0: the prompt asked for it, the work order skipped it).
"""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

# The Kit's release-note categories (agentic_project_kit.release_notes._normalize_category;
# tests/test_release_hygiene.py compares this list with the installed Kit).
RELEASE_NOTE_CATEGORIES = (
    "added", "changed", "fixed", "governance", "transfer", "handoff", "transfer / handoff",
    "docs", "documentation", "tests", "tests / gates", "release", "breaking", "known issues",
)
PR_CREATING = (("transfer", "pr-create"), ("transfer", "pr-create-complete"))
WORK_FINISH = ("work", "finish")
CATEGORY_LINE = re.compile(r"release-note-category\s*:\s*([^\n]+)", re.IGNORECASE)
CATEGORY_HINT = ("Added, Changed, Fixed, Docs, Tests / Gates, Governance, Transfer / Handoff, "
                 "Release, Breaking")


def _publication(root: Path) -> str:
    from agp_cockpit.core.release_policy import _workspace_publication
    return _workspace_publication(root)


def _kit_calls(source: str) -> list[list[str]]:
    from agp_cockpit.core.kit_command_catalog import _invocations, _program
    calls = []
    for argv in _invocations(ast.parse(source)):
        if _program(argv[0]) == "agentic-kit":
            calls.append(argv)
    return calls


def _words(argv: list[str]) -> list[str]:
    words = []
    for token in argv[1:]:
        if token.startswith("-") or token == "<expr>":
            break
        words.append(token)
    return words


def _strings(source: str) -> list[str]:
    return [node.value for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.Constant) and isinstance(node.value, str)]


def _creates_pull_request(argv: list[str]) -> bool:
    return tuple(_words(argv)[:2]) in PR_CREATING


def github_releases_declared(root: Path) -> bool:
    """The Kit publishes (or is about to publish) GitHub Release entries here:
    ``publication: github*`` or a ``release.github_release_title_template``. The
    template alone already collects categorized pull requests for the switch (P11c)."""
    if _publication(root).startswith("github"):
        return True
    try:
        import yaml
        data = yaml.safe_load((Path(root) / ".agentic/config.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, ValueError, ImportError):
        return False
    release = data.get("release") if isinstance(data, dict) else None
    return isinstance(release, dict) and bool(str(release.get("github_release_title_template") or "").strip())


def category_violations(source: str, repository_root: Path) -> list[str]:
    """AGP_PR_RELEASE_CATEGORY_V1 — only where the Kit publishes GitHub entries."""
    if not github_releases_declared(repository_root):
        return []
    found: list[str] = []
    calls = _kit_calls(source)
    if any(tuple(_words(argv)[:2]) == WORK_FINISH and "--execute" in argv for argv in calls):
        found.append("agentic-kit work finish --execute cannot give its pull request a release-note "
                     "category (KIT-GF-048); commit with the Kit, then create the pull request with "
                     "agentic-kit transfer pr-create-complete --body containing a line "
                     f"'release-note-category: <one of {CATEGORY_HINT}>'")
    creating = [argv for argv in calls if _creates_pull_request(argv)]
    if not creating:
        return found
    categories = [match.group(1).strip().lower()
                  for text in _strings(source) for match in CATEGORY_LINE.finditer(text)]
    valid = [c for c in categories if re.sub(r"\s+", " ", c) in RELEASE_NOTE_CATEGORIES]
    if any(not any(token == "--body" or token.startswith("--body=") for token in argv) for argv in creating) \
            or not valid:
        found.append("every pull request needs a release-note category for the Kit's release notes "
                     "(AGP_PR_RELEASE_CATEGORY_V1): pass --body with a line "
                     f"'release-note-category: <one of {CATEGORY_HINT}>'"
                     + (f"; not a category: {', '.join(sorted(set(categories)))}" if categories and not valid else ""))
    return found


def unreleased_entries(changelog_text: str) -> list[str]:
    """Non-empty lines of the CHANGELOG.md "Unreleased" section."""
    match = re.search(r"^## Unreleased[^\n]*\n(.*?)(?=^## |\Z)", changelog_text, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    return [line for line in match.group(1).splitlines() if line.strip()]


def _branch(root: Path, runner=subprocess.run) -> str:
    try:
        done = runner(["git", "branch", "--show-current"], cwd=str(root), text=True,
                      capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (done.stdout or "").strip() if done.returncode == 0 else ""


def changelog_violations(source: str, repository_root: Path, *, runner=subprocess.run) -> list[str]:
    """AGP_RELEASE_CHANGELOG_GATE_V1 — the release pull request needs a moved changelog."""
    branch = _branch(repository_root, runner=runner)
    if not branch.startswith("release/"):
        return []
    calls = _kit_calls(source)
    if not any(_creates_pull_request(argv) or tuple(_words(argv)[:2]) == WORK_FINISH for argv in calls):
        return []
    version = branch.split("/", 1)[1]
    try:
        text = (Path(repository_root) / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return []
    found = []
    if unreleased_entries(text):
        found.append(f"CHANGELOG.md: move every entry of the Unreleased section into '## v{version}' "
                     "and leave Unreleased empty in an earlier work order, then create the release pull "
                     "request (AGP_RELEASE_CHANGELOG_GATE_V1)")
    if not re.search(rf"^## v{re.escape(version)}\b", text, re.MULTILINE):
        found.append(f"CHANGELOG.md has no section '## v{version}' yet; run the Kit's release preparation "
                     "first (AGP_RELEASE_CHANGELOG_GATE_V1)")
    return found


def violations(source: str, repository_root: Path) -> list[str]:
    return category_violations(source, repository_root) + changelog_violations(source, repository_root)
