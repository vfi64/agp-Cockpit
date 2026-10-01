"""The repository's agentic-kit command manifest as command authority.

AGP_KIT_COMMAND_CATALOG_V1
`.agentic/INITIAL_LLM_PROMPT.md` makes `docs/reference/agentic-kit-commands.json`
the mandatory command reference and forbids reconstructing commands from
memory. The remote side cannot read the local repository, so the Cockpit

* sends a compact digest of the manifest with the mission start,
* states the standing command rules, and
* enforces them on every received work order (no prompt-only rule).

Enforced rules:
1. every agentic-kit command in a work order exists in the manifest;
2. no git push / fetch / pull (network git is never part of a work order);
3. no raw git/gh command for which the manifest names a Kit wrapper.
"""

from __future__ import annotations

import ast
import json
import shlex
from dataclasses import dataclass
from pathlib import Path

MANIFEST = Path("docs/reference/agentic-kit-commands.json")
SURFACE_ORDER = {"orchestrator": 0, "diagnostic": 1, "primitive": 2}
NETWORK_GIT = frozenset({"push", "fetch", "pull"})
# AGP_REMOTE_EFFECT_GATE_V1: Kit commands with an effect outside the local
# repository (push, fetch/pull, PR, merge, publish, remote branches). The
# manifest has no such classification yet; until the Kit provides one, this
# Cockpit list plus every command whose "replaces_raw" names git push or gh is
# authoritative. A test fails when an entry disappears from the manifest.
REMOTE_EFFECT_COMMANDS = frozenset({
    "github-create", "pr merge-if-green", "pr-closeout", "release-publish",
    "remote-branch-hygiene-apply", "remote-next",
    "transfer admin-refresh-pr", "transfer delete-merged-work-branch",
    "transfer evidence-pr-complete", "transfer fetch-origin", "transfer post-merge-complete",
    "transfer pr-closeout-complete", "transfer pr-complete", "transfer pr-create",
    "transfer pr-create-complete", "transfer pr-merge-safe", "transfer publish-last-report",
    "transfer pull-current", "transfer push-current", "transfer remote-next",
    "transfer remote-work-start", "transfer sync-main", "work finish",
})
COMMAND_RULES = (
    "Command authority (standing rules for every work order): "
    "use only agentic-kit commands listed in the attached agentic-kit-command-digest.json "
    "(generated from docs/reference/agentic-kit-commands.json); never reconstruct commands from memory. "
    "Prefer the most comprehensive orchestrator command (surface \"orchestrator\") that covers the task; "
    "use diagnostic or primitive commands only when no orchestrator fits. "
    "Never run git push, git fetch or git pull. "
    "Raw git/gh commands that have a Kit wrapper (\"replaces_raw\") are rejected; use the wrapper. "
    "Commands marked \"remote_effect\" (push, pull/fetch, PR, merge, publish) are rejected unless the "
    "human has explicitly approved exactly that step; ask with NEEDS_HUMAN first."
)


@dataclass(frozen=True)
class KitCommandCatalog:
    manifest_sha: str
    commands: tuple[dict, ...]

    @classmethod
    def load(cls, root: Path) -> KitCommandCatalog | None:
        path = Path(root) / MANIFEST
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        commands = tuple(c for c in data.get("commands", []) if isinstance(c, dict) and c.get("path"))
        return cls(str((data.get("meta") or {}).get("manifest_sha") or ""), commands)

    @property
    def paths(self) -> tuple[tuple[str, ...], ...]:
        return tuple(tuple(str(p) for p in c["path"]) for c in self.commands)

    def resolve(self, tokens: list[str]) -> dict | None:
        """Longest manifest command path that prefixes the given subcommand tokens."""
        best = None
        for command in self.commands:
            path = [str(p) for p in command["path"]]
            if tokens[: len(path)] == path and (best is None or len(path) > len(best["path"])):
                best = command
        return best

    def has_remote_effect(self, command: dict) -> bool:
        name = " ".join(str(p) for p in command["path"])
        if name in REMOTE_EFFECT_COMMANDS:
            return True
        return any(
            str(raw).startswith(("git push", "gh ")) for raw in command.get("replaces_raw") or []
        )

    def wrappers(self) -> list[tuple[str, str]]:
        pairs = []
        for command in self.commands:
            for raw in command.get("replaces_raw") or []:
                raw = " ".join(str(raw).split())
                if raw.split(" ", 1)[0] in {"git", "gh"}:
                    pairs.append((raw, command["qualified_name"]))
        return pairs

    def digest(self) -> dict:
        ordered = sorted(self.commands, key=lambda c: (SURFACE_ORDER.get(c.get("surface"), 3), c["qualified_name"]))
        return {
            "kind": "agentic_kit_command_digest",
            "source": str(MANIFEST),
            "manifest_sha": self.manifest_sha,
            "rules": COMMAND_RULES,
            "commands": [
                {
                    "command": c["qualified_name"],
                    "surface": c.get("surface"),
                    "safety": c.get("safety"),
                    "use": " ".join(str(c.get("when_to_use") or c.get("help") or "").split())[:200],
                    "options": [o for p in c.get("params", []) for o in (p.get("opts") or [])][:12],
                    "replaces_raw": list(c.get("replaces_raw") or []),
                    "remote_effect": self.has_remote_effect(c),
                }
                for c in ordered
            ],
        }

    def write_digest(self, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.digest(), ensure_ascii=False, indent=1) + "\n"
        if not target.is_file() or target.read_text(encoding="utf-8") != payload:
            temporary = target.with_suffix(".tmp")
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(target)
        return target


def _invocations(tree: ast.AST) -> list[list[str]]:
    """argv-like invocations written as string lists/tuples or command strings."""
    found: list[list[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
            values = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if values and len(values) == len(node.elts):
                found.append(values)
            elif node.elts and isinstance(node.elts[0], ast.Constant) and isinstance(node.elts[0].value, str):
                found.append([e.value if isinstance(e, ast.Constant) and isinstance(e.value, str) else "<expr>"
                              for e in node.elts])
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            text = node.value.strip()
            if text.startswith(("agentic-kit ", "git ", "gh ")):
                try:
                    found.append(shlex.split(text))
                except ValueError:
                    found.append(text.split())
    return found


def _program(token: str) -> str:
    return Path(str(token)).name


def remote_effect_commands(source: str, catalog: KitCommandCatalog | None) -> list[str]:
    """Qualified names of remote-effect Kit commands used by a work order."""
    if catalog is None:
        return []
    found = set()
    for argv in _invocations(ast.parse(source)):
        if _program(argv[0]) != "agentic-kit":
            continue
        subcommands = []
        for token in argv[1:]:
            if token.startswith("-") or token == "<expr>":
                break
            subcommands.append(token)
        command = catalog.resolve(subcommands) if subcommands else None
        if command is not None and catalog.has_remote_effect(command):
            found.add(command["qualified_name"])
    return sorted(found)


def command_catalog_violations(source: str, catalog: KitCommandCatalog | None,
                               *, allow_remote_effects: bool = False) -> list[str]:
    tree = ast.parse(source)
    violations: list[str] = []
    if not allow_remote_effects:
        violations.extend(
            f"{name} has a remote effect and requires an explicit human approval"
            for name in remote_effect_commands(source, catalog)
        )
    wrappers = catalog.wrappers() if catalog is not None else []
    for argv in _invocations(tree):
        program = _program(argv[0])
        args = [a for a in argv[1:]]
        if program == "git":
            network = sorted(NETWORK_GIT.intersection(args))
            if network:
                violations.append(f"git {network[0]} is not permitted in work orders")
                continue
            line = " ".join(["git", *args])
            for raw, wrapper in wrappers:
                if raw.startswith("git ") and (line == raw or line.startswith(raw + " ")):
                    violations.append(f"raw '{raw}' has a Kit wrapper; use {wrapper}")
        elif program == "gh":
            line = " ".join(["gh", *args])
            for raw, wrapper in wrappers:
                if raw.startswith("gh ") and (line == raw or line.startswith(raw + " ")):
                    violations.append(f"raw '{raw}' has a Kit wrapper; use {wrapper}")
        elif program == "agentic-kit" and catalog is not None:
            tokens = [a for a in args if a != "<expr>"]
            subcommands = []
            for token in tokens:
                if token.startswith("-"):
                    break
                subcommands.append(token)
            if subcommands and catalog.resolve(subcommands) is None:
                violations.append(
                    "unknown agentic-kit command 'agentic-kit " + " ".join(subcommands)
                    + f"' (not in {MANIFEST})"
                )
    return sorted(set(violations))
