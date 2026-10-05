"""Repository release policy enforced on work orders (AGP_RELEASE_POLICY_V1).

The owner decided on 2026-10-02 that agp-Cockpit is never published to PyPI or
Zenodo. Since 2026-10-05 (P11c, AGP_KIT_GITHUB_RELEASE_V1) the Kit's signed release
run also creates the GitHub Release entry of the private repository
(``publication: github``); a work order still never runs ``gh release`` itself. The
policy lives in docs/planning/release_policy.json; work orders that would publish
otherwise are rejected as correctable violations.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

POLICY_PATH = Path("docs/planning/release_policy.json")
# Policies this module enforces: private tag only, or tag plus the Kit-made GitHub entry.
RESTRICTED_PUBLICATIONS = ("none", "github")


def load(repository_root: Path | None) -> dict | None:
    if repository_root is None:
        return None
    path = Path(repository_root) / POLICY_PATH
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def violations(source: str, repository_root: Path | None, catalog=None) -> list[str]:
    policy = load(repository_root)
    if not policy or policy.get("publication") not in RESTRICTED_PUBLICATIONS:
        return []
    from agp_cockpit.core.kit_command_catalog import (
        _invocations,
        _program,
        kit_commands_used,
    )

    found: list[str] = []
    forbidden_kit = set(policy.get("forbidden_kit_commands") or ())
    if catalog is not None:
        used = {c["qualified_name"] for c in kit_commands_used(source, catalog)}
    else:
        used = set()
    tree = ast.parse(source)
    for argv in _invocations(tree):
        program = _program(argv[0])
        words = [w for w in argv[1:] if not w.startswith("-")]
        if program == "agentic-kit":
            used.update(name for name in forbidden_kit
                        if name.split()[1:] == words[:len(name.split()) - 1])
        if program == "gh" and " ".join(words[:2]) in set(policy.get("forbidden_gh") or ()):
            found.append(f"gh {' '.join(words[:2])} publishes a GitHub Release")
    found += [f"{name} is a publication step" for name in sorted(used & forbidden_kit)]
    found += _signed_release_violations(source, repository_root, policy, used, catalog)
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    for host in policy.get("forbidden_hosts") or ():
        if any(host in text for text in strings):
            found.append(f"contacts {host}")
    if not found:
        return []
    entry = ("the GitHub Release entry only through the Kit's signed release run"
             if policy.get("publication") == "github" else "no GitHub Release")
    message = (f"release policy of this repository (AGP_RELEASE_POLICY_V1, {POLICY_PATH}): "
               f"{'; '.join(sorted(set(found)))}. "
               f"A release here: version bump, changelog, annotated tag, {entry}; no PyPI, no Zenodo.")
    return [message]


def _signed_release_violations(source: str, repository_root: Path, policy: dict,
                               used: set[str], catalog) -> list[str]:
    """AGP_SIGNED_PRIVATE_RELEASE_V1 (plan P11, owner 2026-10-04): the Kit's release
    route is allowed — dry run freely, live only signed, and only with the publication
    the policy names (P11c 2026-10-05: github = tag plus the Kit-made GitHub entry)."""
    signed = set((policy.get("signed_kit_commands") or {}).get("commands") or ())
    names = set(used)
    if catalog is None:   # without a catalog: a literal invocation still counts
        names |= {name for name in signed if name.split()[1] in source}
    if not names & signed:
        return []
    from agp_cockpit.core.kit_command_catalog import _may_execute
    found = []
    wanted = str(policy.get("publication") or "none")
    if _workspace_publication(repository_root) != wanted:
        found.append("agentic-kit release-publish runs here only with the repository's release policy "
                     f"(.agentic/config.yaml publication: {wanted}, {POLICY_PATH})")
    if "ENABLE_LIVE_PUBLISH" in source:
        found.append("a live release-publish uses its signed approval, never the marker file "
                     ".agentic/release/ENABLE_LIVE_PUBLISH")
    if _may_execute(source) and not all(flag in source for flag in (
            "--execute", "--allow-execute", "--expected-signature")):
        found.append("a live release-publish needs --execute --allow-execute --expected-signature "
                     "<the signature of its dry run>")
    return found


def _workspace_publication(repository_root: Path) -> str:
    try:
        import yaml
        data = yaml.safe_load((Path(repository_root) / ".agentic/config.yaml").read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError):
        return ""
    return str((data or {}).get("publication") or "") if isinstance(data, dict) else ""
