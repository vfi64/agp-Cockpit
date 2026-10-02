"""Repository release policy enforced on work orders (AGP_RELEASE_POLICY_V1).

The owner decided on 2026-10-02 that agp-Cockpit is never published (no GitHub
Release, PyPI or Zenodo). The policy lives in docs/planning/release_policy.json;
work orders that would publish are rejected as correctable violations.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

POLICY_PATH = Path("docs/planning/release_policy.json")


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
    if not policy or policy.get("publication") != "none":
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
    strings = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
    for host in policy.get("forbidden_hosts") or ():
        if any(host in text for text in strings):
            found.append(f"contacts {host}")
    if not found:
        return []
    message = (f"release policy of this repository (AGP_RELEASE_POLICY_V1, {POLICY_PATH}): "
               f"no publication — {'; '.join(sorted(set(found)))}. "
               "A release here is private: version bump, changelog, annotated tag, local build.")
    return [message]
