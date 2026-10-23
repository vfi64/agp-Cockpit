"""Release hygiene enforced on work orders (Release slice, 2026-10-05).

AGP_PR_RELEASE_CATEGORY_V1: with ``publication: github`` the Kit blocks a release while a
merged pull request has no release-note category (between 0.1.1 and 0.2.0, 5 of 13 pull
request titles were unclassified). Every pull request a work order creates therefore carries
a line ``release-note-category: <category>`` in its body, which the Kit reads before the
title. AGP_PR_CATEGORY_ROUTES_V1 (live 2026-10-22, PR #374 and #380): ``agentic-kit work finish
--execute`` was refused here as unable to set a body (KIT-GF-048), long after the Kit gave it
``--body`` and ``--release-note-category``; the work orders took detours and forgot the category
four times. Every pull-request route of the Kit now passes with a literal ``--release-note-category
<category>`` or a ``--body`` carrying the category line; a repository without ``publication:`` is
treated with the Kit's default (``github+pypi+zenodo``), so the Kit repository is covered as well.

AGP_RELEASE_CHANGELOG_GATE_V1: on a release branch the pull request is created only once the
Kit's release preparation wrote the version section, and only one of them.

AGP_RELEASE_KIT_OWNED_FILES_V1 (owner 2026-10-08, release 0.2.3): the release state —
CHANGELOG.md (DPA class ``release_state``), pyproject.toml and docs/releases/versions.json — is
written on a release branch only by the Kit's release preparation. Release 0.2.3 needed 14 extra
steps because a work order moved the Unreleased entries by regex (duplicate section, missing date,
missing blank line); the earlier rule that Unreleased must be empty before the release pull
request asked for exactly that hand edit and is withdrawn. The Kit's release-prep copies the
Unreleased entries but leaves them in place (KIT-GF-060); until it consumes them, the first work
slice after a release removes the released entries (AGP_UNRELEASED_NOT_RELEASED_V1, a test).
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
CATEGORY_OPTION = "--release-note-category"
# agentic_project_kit.workspace.DEFAULT_PUBLICATION_POLICY; a test compares it with the installed Kit.
KIT_DEFAULT_PUBLICATION = "github+pypi+zenodo"
CATEGORY_LINE = re.compile(r"release-note-category\s*:\s*([^\n]+)", re.IGNORECASE)
CATEGORY_HINT = ("Added, Changed, Fixed, Docs, Tests / Gates, Governance, Transfer / Handoff, "
                 "Release, Breaking")


def _publication(root: Path) -> str:
    from agp_cockpit.core.release_policy import _workspace_publication
    return _workspace_publication(root)


def _effective_publication(root: Path) -> str:
    """The Kit's publication policy: the configured one, or the Kit's default when the key is absent."""
    if not (Path(root) / ".agentic/config.yaml").is_file():
        return ""
    return _publication(root) or KIT_DEFAULT_PUBLICATION


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
    if _effective_publication(root).startswith("github"):
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
    calls = _kit_calls(source)
    creating = [argv for argv in calls if _creates_pull_request(argv)
                or (tuple(_words(argv)[:2]) == WORK_FINISH and "--execute" in argv)]
    if not creating:
        return []
    categories = [match.group(1).strip().lower()
                  for text in _strings(source) for match in CATEGORY_LINE.finditer(text)]
    valid = [c for c in categories if _known(c)]
    missing = []
    for argv in creating:
        option = _option_value(argv, CATEGORY_OPTION)
        if option is not None:
            if not _known(option):
                missing.append(f"{CATEGORY_OPTION} {option!r} is not a category")
            continue
        if any(token == "--body" or token.startswith("--body=") for token in argv) and valid:
            continue
        missing.append(" ".join(["agentic-kit", *_words(argv)[:2]]) + " has no category")
    if not missing:
        return []
    return ["every pull request needs a release-note category for the Kit's release notes "
            f"(AGP_PR_RELEASE_CATEGORY_V1): pass {CATEGORY_OPTION} <one of {CATEGORY_HINT}> to "
            "agentic-kit work finish or transfer pr-create(-complete), or a --body with a line "
            f"'release-note-category: <category>' ({'; '.join(missing)})"
            + (f"; not a category: {', '.join(sorted(set(categories)))}" if categories and not valid else "")]


def _known(category: str) -> bool:
    return re.sub(r"\s+", " ", str(category).strip().lower()) in RELEASE_NOTE_CATEGORIES


def _option_value(argv: list[str], option: str) -> str | None:
    """The literal value of ``option`` in an argv, ``<expr>`` for a computed one, None when absent."""
    for index, token in enumerate(argv):
        if token == option:
            return argv[index + 1] if index + 1 < len(argv) else ""
        if token.startswith(option + "="):
            return token.split("=", 1)[1]
    return None


def unreleased_entries(changelog_text: str) -> list[str]:
    """Non-empty lines of the CHANGELOG.md "Unreleased" section."""
    match = re.search(r"^## Unreleased[^\n]*\n(.*?)(?=^## |\Z)", changelog_text, re.MULTILINE | re.DOTALL)
    if not match:
        return []
    return [line for line in match.group(1).splitlines() if line.strip()]


def wrapped_entry_lines(changelog_text: str) -> list[str]:
    """AGP_ONE_LINE_CHANGELOG_V1 (release 0.2.1, #252): lines of the Unreleased section that do
    not start an entry ("- "): a wrapped bullet broke the Kit's changelog consistency check."""
    return [line for line in unreleased_entries(changelog_text) if not line.startswith("- ")]


def released_entries(changelog_text: str) -> set[str]:
    """Bullet lines of every version section (``## v<x.y.z>``)."""
    found: set[str] = set()
    for match in re.finditer(r"^## v\d+\.\d+\.\d+[^\n]*\n(.*?)(?=^## |\Z)", changelog_text, re.MULTILINE | re.DOTALL):
        found.update(line for line in match.group(1).splitlines() if line.startswith("- "))
    return found


def pending_entries(changelog_text: str) -> list[str]:
    """Unreleased entries that no version section carries yet (KIT-GF-060: release-prep copies the
    entries into the version section and leaves them under Unreleased)."""
    released = released_entries(changelog_text)
    return [line for line in unreleased_entries(changelog_text) if line not in released]


# AGP_BUILD_ID_DERIVED_V1: version.py and build_identity.js carry Kit version anchors; on a release
# branch their build id follows the version, nothing is set by hand.
KIT_OWNED_RELEASE_FILES = ("CHANGELOG.md", "pyproject.toml", "docs/releases/versions.json",
                           "src/agp_cockpit/version.py", "chrome_extension/build_identity.js")
_WRITE_METHODS = ("write_text", "write_bytes")


def _literal_paths(node: ast.AST) -> set[str]:
    return {sub.value for sub in ast.walk(node) if isinstance(sub, ast.Constant) and isinstance(sub.value, str)
            for path in KIT_OWNED_RELEASE_FILES if sub.value.endswith(path) or sub.value == Path(path).name}


def kit_owned_writes(source: str) -> list[str]:
    """Kit-owned release files this work order writes itself (write_text/write_bytes or open(..., 'w'/'a'/'x')
    on a path built from their name, directly or through a variable)."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    named: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and _literal_paths(node.value):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    named.setdefault(target.id, set()).update(_literal_paths(node.value))

    def paths_of(expr: ast.AST) -> set[str]:
        found = set(_literal_paths(expr))
        for sub in ast.walk(expr):
            if isinstance(sub, ast.Name) and sub.id in named:
                found |= named[sub.id]
        return found

    written: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in _WRITE_METHODS:
            written |= paths_of(func.value)
        elif isinstance(func, ast.Name) and func.id == "open" and node.args:
            mode = node.args[1] if len(node.args) > 1 else next(
                (kw.value for kw in node.keywords if kw.arg == "mode"), None)
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str) and set(mode.value) & set("wax"):
                written |= paths_of(node.args[0])
    return sorted({path for path in KIT_OWNED_RELEASE_FILES for value in written
                   if value.endswith(path) or value == Path(path).name})


def kit_owned_file_violations(source: str, repository_root: Path, *, runner=subprocess.run) -> list[str]:
    """AGP_RELEASE_KIT_OWNED_FILES_V1 — on release/<v> only the Kit writes the release state."""
    written = kit_owned_writes(source)
    if not written or not _branch(repository_root, runner=runner).startswith("release/"):
        return []
    return [(f"this release work order writes {', '.join(written)} itself; on a release branch the release "
             "state is written only by the Kit's release preparation (agentic-kit release prepare / "
             "release-prep --summary-lines-from <file>.json), which also replaces its own version section "
             "when run again. Reading CHANGELOG.md to build the summary lines is fine "
             "(AGP_RELEASE_KIT_OWNED_FILES_V1)")]


def _branch(root: Path, runner=subprocess.run) -> str:
    try:
        done = runner(["git", "branch", "--show-current"], cwd=str(root), text=True,
                      capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (done.stdout or "").strip() if done.returncode == 0 else ""


def changelog_violations(source: str, repository_root: Path, *, runner=subprocess.run) -> list[str]:
    """AGP_RELEASE_CHANGELOG_GATE_V1 — the release pull request needs exactly one version section
    written by the Kit; AGP_ONE_LINE_CHANGELOG_V1 — every pull request needs one-line Unreleased
    entries."""
    calls = _kit_calls(source)
    if not any(_creates_pull_request(argv) or tuple(_words(argv)[:2]) == WORK_FINISH for argv in calls):
        return []
    try:
        text = (Path(repository_root) / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return []
    found = []
    wrapped = wrapped_entry_lines(text)
    if wrapped:
        found.append("CHANGELOG.md: every Unreleased entry must be one line starting with '- '; join "
                     f"these continuation lines into their entry in an earlier work order: {wrapped[:3]} "
                     "(AGP_ONE_LINE_CHANGELOG_V1)")
    branch = _branch(repository_root, runner=runner)
    if not branch.startswith("release/"):
        return found
    version = branch.split("/", 1)[1]
    sections = len(re.findall(rf"^## v{re.escape(version)}\b", text, re.MULTILINE))
    if not sections:
        found.append(f"CHANGELOG.md has no section '## v{version}' yet; run the Kit's release preparation "
                     "first (AGP_RELEASE_CHANGELOG_GATE_V1)")
    elif sections > 1:
        found.append(f"CHANGELOG.md has {sections} sections '## v{version}'; restore CHANGELOG.md from "
                     "origin/main through the Kit and run the Kit's release preparation once more — it "
                     "writes exactly one section (AGP_RELEASE_CHANGELOG_GATE_V1)")
    found.extend(build_id_violations(repository_root, version))
    return found


BUILD_ID_FILES = ("src/agp_cockpit/version.py", "chrome_extension/build_identity.js")


def build_id_violations(repository_root: Path, version: str) -> list[str]:
    """AGP_RELEASE_BUILD_ID_GATE_V1 (live 2026-10-07, release 0.2.2, step 1853): the release work
    order wrote "release-0.2.2-r12" (the old rebuild counter kept); the CI turned red only after
    commit, push and pull request. Since AGP_BUILD_ID_DERIVED_V1 (2026-10-09) the build id follows
    the version the Kit's release preparation writes, so release-<version> needs no hand edit; the
    gate stays as the check that the derivation holds. Repositories without these files (not the
    Cockpit) are not affected."""
    from agp_cockpit.version import build_id_from_text
    expected = f"release-{version}"
    found = []
    for rel in BUILD_ID_FILES:
        try:
            actual = build_id_from_text((Path(repository_root) / rel).read_text(encoding="utf-8"))
        except OSError:
            continue
        if actual != expected:
            found.append(f"{rel}: the build id is {actual or 'missing'!r}, expected {expected!r}; the Kit's "
                         "release preparation sets the version and the build id follows it — run it for "
                         f"{version} and never edit the build id on a release branch "
                         "(AGP_RELEASE_BUILD_ID_GATE_V1, AGP_BUILD_ID_DERIVED_V1)")
    return found


def summary_violations(source: str) -> list[str]:
    """AGP_RELEASE_SUMMARY_JSON_V1 (live 2026-10-07, release 0.2.2, step 1851): the release work
    order handed the Kit's release preparation a text file; `--summary-lines-from` reads only a
    JSON list of strings (or {"summary_lines": [...]}) and the step failed with rc 2."""
    calls = [argv for argv in _kit_calls(source) if "--summary-lines-from" in argv]
    if not calls:
        return []
    named = [argv[argv.index("--summary-lines-from") + 1] for argv in calls
             if argv.index("--summary-lines-from") + 1 < len(argv)]
    texts = [value for value in named if value != "<expr>" and not value.lower().endswith(".json")]
    texts += [value for value in _strings(source)
              if "summary" in value.lower() and value.lower().endswith((".txt", ".md"))]
    if not texts:
        return []
    return [(f"--summary-lines-from reads only a JSON file (a list of strings, or {{\"summary_lines\": [...]}}); "
             f"this work order names {sorted(set(texts))[:2]} — write the summary lines as JSON "
             "(AGP_RELEASE_SUMMARY_JSON_V1)")]


def violations(source: str, repository_root: Path) -> list[str]:
    return (category_violations(source, repository_root) + changelog_violations(source, repository_root)
            + summary_violations(source) + kit_owned_file_violations(source, repository_root))


def manual_github_release_command(root: Path, version: str) -> str:
    """AGP_MANUAL_GITHUB_RELEASE_HINT_V1 (owner 2026-10-06, release 0.2.1: „Release erscheint
    nicht auf GitHub — warum?“): with ``publication: none`` the signed run pushes only the tag;
    while KIT-GF-049 blocks the Kit's GitHub route the owner creates the entry himself. The
    Cockpit never runs it (no Cockpit-local workaround for a missing Kit route); it names the
    command with the title template and the changelog section as notes."""
    if not version or _publication(root) != "none" or not github_releases_declared(root):
        return ""
    import shlex
    try:
        import yaml
        data = yaml.safe_load((Path(root) / ".agentic/config.yaml").read_text(encoding="utf-8")) or {}
        template = str(((data.get("release") or {}).get("github_release_title_template")) or "")
        title = template.format(version=version)
    except (OSError, ValueError, ImportError, KeyError, IndexError, AttributeError):
        return ""
    notes = f".local/agp-cockpit/tmp/notes-{version}.md"
    section = re.escape(f"v{version}").replace("/", r"\/")
    extract = f"awk '/^## {section}( |$)/{{f=1;next}} /^## /{{f=0}} f' CHANGELOG.md > {notes}"
    return (f"cd {shlex.quote(str(root))} && mkdir -p .local/agp-cockpit/tmp && {extract} && "
            f"gh release create v{version} --verify-tag --title {shlex.quote(title)} --notes-file {notes}")
