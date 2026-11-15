"""Repository release policy enforced on work orders (AGP_RELEASE_POLICY_V1).

The owner decided on 2026-10-02 that agp-Cockpit is never published to PyPI or
Zenodo. Since 2026-10-05 (P11c, AGP_KIT_GITHUB_RELEASE_V1) the Kit's signed release
run also creates the GitHub Release entry of the repository
(``publication: github``); a work order still never runs ``gh release`` itself. The
policy lives in docs/planning/release_policy.json; work orders that would publish
otherwise are rejected as correctable violations.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

POLICY_PATH = Path("docs/planning/release_policy.json")
# Policies this module enforces: tag only, or tag plus the Kit-made GitHub Release entry.
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
        _located_invocations,
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
    lines: dict[str, list[int]] = {}
    for argv, line in _located_invocations(tree):
        program = _program(argv[0])
        words = [w for w in argv[1:] if not w.startswith("-")]
        if program == "agentic-kit":
            for name in forbidden_kit:
                if name.split()[1:] == words[:len(name.split()) - 1]:
                    used.add(name)
                    lines.setdefault(name, []).append(line)
        if program == "gh" and " ".join(words[:2]) in set(policy.get("forbidden_gh") or ()):
            found.append(f"line {line}: gh {' '.join(words[:2])} publishes a GitHub Release")
    found += [f"{name} is a publication step{_on_lines(lines.get(name))}" for name in sorted(used & forbidden_kit)]
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


def _on_lines(numbers: list[int] | None) -> str:
    return f" (line {', '.join(str(n) for n in sorted(set(numbers)))})" if numbers else ""


def _signed_release_violations(source: str, repository_root: Path, policy: dict,
                               used: set[str], catalog) -> list[str]:
    """AGP_SIGNED_PRIVATE_RELEASE_V1 (plan P11, owner 2026-10-04): the Kit's release
    route is allowed — dry run freely, live only signed, and only with the publication
    the policy names (P11c 2026-10-05: github = tag plus the Kit-made GitHub entry).

    AGP_RELEASE_RULE_CALLS_V1 (workflow-friction plan C1, V10): the rule reads the calls in the
    syntax tree, as ``destructive_execute_commands`` does, not the text. A flag in a docstring or a
    pull-request body no longer makes a dry run live; a live call is judged by its own flags (or by an
    execute flag standing free in the code, which can be appended at run time), and every rejection
    names the call and its line."""
    from agp_cockpit.core.kit_command_catalog import (
        EXECUTE_FLAGS,
        _located_invocations,
        _program,
        _subcommands,
        call_flags,
        call_may_execute,
        free_execute_flags,
        render_call,
    )
    signed = set((policy.get("signed_kit_commands") or {}).get("commands") or ())
    tree = ast.parse(source)
    calls: list[tuple[str, list[str], int]] = []
    for argv, line in _located_invocations(tree):
        if _program(argv[0]) != "agentic-kit":
            continue
        words = _subcommands(argv)
        calls += [(name, argv, line) for name in sorted(signed)
                  if words[:len(name.split()) - 1] == name.split()[1:]]
    names = set(used) | {name for name, _, _ in calls}
    if not names & signed:
        return []
    free = free_execute_flags(tree)
    found = []
    wanted = str(policy.get("publication") or "none")
    if _workspace_publication(repository_root) != wanted:
        where = "; ".join(f"line {line}: {render_call(argv)}" for _, argv, line in calls)
        found.append("the Kit's release route runs here only with the repository's release policy "
                     f"(.agentic/config.yaml publication: {wanted}, {POLICY_PATH})"
                     + (f" — {where}" if where else ""))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant) and isinstance(node.value, str) and "ENABLE_LIVE_PUBLISH" in node.value
                and not _is_docstring(tree, node)):
            found.append(f"line {node.lineno}: a live release-publish uses its signed approval, never the marker "
                         "file .agentic/release/ENABLE_LIVE_PUBLISH")
    required = {
        "agentic-kit release-publish": (
            EXECUTE_FLAGS, ("--execute", "--allow-execute", "--expected-signature"),
            ("a live release-publish needs --execute --allow-execute --expected-signature "
             "<the signature of its dry run>")),
        # AGP_RELEASE_RUN_AUTONOMY_V1 (owner 2026-10-08/13, KIT-GF-061): a signed release run records who
        # approved and the source of the consent; without them the Kit refuses an explicit policy anyway.
        "agentic-kit release run": (
            ("--execute",), ("--expected-signature", "--approved-by", "--consent-source"),
            ("a live release run needs --execute --expected-signature <the gate's signature> "
             "--approved-by <owner> --consent-source <the start click>")),
    }
    for name, argv, line in calls:
        if name not in required:
            continue
        live_flags, needed, text = required[name]
        if not call_may_execute(argv, free, live_flags) or set(needed) <= call_flags(argv):
            continue
        reason = ""
        if not call_flags(argv) & set(live_flags):
            standing = sorted({n for flag, n in free if flag in live_flags})
            reason = (f"; it counts as live because an execute flag stands outside every call{_on_lines(standing)} "
                      "and can be appended at run time")
        found.append(f"line {line}: {render_call(argv)}: {text}{reason}")
    return found


def _is_docstring(tree: ast.AST, constant: ast.AST) -> bool:
    return any(isinstance(node, ast.Expr) and node.value is constant for node in ast.walk(tree))


def _workspace_publication(repository_root: Path) -> str:
    try:
        import yaml
        data = yaml.safe_load((Path(repository_root) / ".agentic/config.yaml").read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError):
        return ""
    return str((data or {}).get("publication") or "") if isinstance(data, dict) else ""
