"""The Cockpit's own build revision follows a Kit adoption (AGP_KIT_ADOPT_BUILD_REVISION_V1).

Workflow-friction plan C2 (owner 2026-11-13, V7): since Kit 1.4.0 „Kit übernehmen“ leaves the
adoption line in the Unreleased section of CHANGELOG.md (Kit K4, curated workspaces). The Cockpit's
build-id rule (AGP_BUILD_ID_DERIVED_V1, tests/test_hygiene.py) then wants a rebuild id
``release-<version>-r<N>``; PR #436 needed a follow-up only for that. After the adoption verifier
passed, the Cockpit raises the revision itself, in the same branch, before „Abschließen“.

Only the Cockpit's own checkout carries both files; any other steered repository is left alone.
A revision that already names the current version stays as it is (the rule wants ``-r<N>``, not a
new N per adoption), so the step is idempotent.
"""

from __future__ import annotations

import re
from pathlib import Path

from agp_cockpit.core.release_hygiene import pending_entries

VERSION_FILE = "src/agp_cockpit/version.py"
EXTENSION_FILE = "chrome_extension/build_identity.js"
CHANGELOG_FILE = "CHANGELOG.md"

_VERSION = re.compile(r"""^(?:var\s+)?(?:AGP_)?APP_VERSION\s*=\s*["']([^"']+)["']""", re.MULTILINE)
_REVISION = re.compile(r"""(?:AGP_)?BUILD_REVISION\s*=\s*[(\[]\s*["']([^"']+)["']\s*,\s*(\d+)\s*[)\]]""")


class RevisionError(ValueError):
    """The build identity files cannot be aligned without a human look."""


def _one(pattern: re.Pattern, text: str, path: str, what: str) -> re.Match:
    found = list(pattern.finditer(text))
    if len(found) != 1:
        raise RevisionError(f"{path}: expected exactly one {what}, found {len(found)}")
    return found[0]


def _with_revision(text: str, match: re.Match, version: str) -> str:
    """``text`` with the revision of ``match`` set to (version, 1); quotes and layout stay."""
    (v_start, v_end), (n_start, n_end) = match.span(1), match.span(2)
    return text[:v_start] + version + text[v_end:n_start] + "1" + text[n_end:]


def align(root: Path) -> list[str]:
    """Raise the build revision to (APP_VERSION, 1) when CHANGELOG.md carries pending Unreleased
    entries and the revision still names an older version. Returns the changed paths."""
    root = Path(root)
    files = {path: root / path for path in (VERSION_FILE, EXTENSION_FILE)}
    if not all(path.is_file() for path in files.values()):
        return []
    changelog = root / CHANGELOG_FILE
    if not changelog.is_file() or not pending_entries(changelog.read_text(encoding="utf-8")):
        return []
    texts = {path: file.read_text(encoding="utf-8") for path, file in files.items()}
    versions = {_one(_VERSION, text, path, "APP_VERSION").group(1) for path, text in texts.items()}
    if len(versions) != 1:
        raise RevisionError(f"APP_VERSION differs between {VERSION_FILE} and {EXTENSION_FILE}: "
                            f"{', '.join(sorted(versions))}")
    version = versions.pop()
    revisions = {path: _one(_REVISION, text, path, "BUILD_REVISION") for path, text in texts.items()}
    current = {(match.group(1), int(match.group(2))) for match in revisions.values()}
    if len(current) != 1:
        raise RevisionError(f"BUILD_REVISION differs between {VERSION_FILE} and {EXTENSION_FILE}")
    base, number = current.pop()
    if base == version and number > 0:
        return []
    changed = []
    for path, match in revisions.items():
        files[path].write_text(_with_revision(texts[path], match, version), encoding="utf-8")
        changed.append(path)
    return changed
