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

AGP_KIT_INSTALLATION_AUTHORITY_V1 (plan P1): the manifest comes from the
installed Kit (``kit_installation``); the repository copy is a fallback.
Standard tasks (R2) must run at least one orchestrator per work order, and
their remote effects only through orchestrators. An orchestrator whose effect
the Cockpit does not know counts as remote effect (R3, fail closed).
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
# Orchestrators known to act only locally (read, local files, local branches).
# Every other orchestrator either has a known remote effect or an unknown one;
# both need an approval (AGP_UNKNOWN_EFFECT_ASKS_V1). A new Kit orchestrator
# therefore asks until it is classified here or the Kit declares its effect.
LOCAL_ORCHESTRATORS = frozenset({
    "artifact-gc", "chat session-start", "docs lifecycle sweep", "dpa final-closeout-check",
    "init", "post-release-doi-closeout", "release prepare", "release ready", "release-prep",
    "transfer chat-switch-complete", "work recover", "workspace adopt", "workspace dpa-intake",
    "workspace init", "workspace remove", "workspace upgrade",
})
COMMAND_RULES = (
    "Command authority (standing rules for every work order): "
    "use only agentic-kit commands listed in the attached agentic-kit-command-digest.json "
    "(generated from the manifest of the installed Kit); never reconstruct commands from memory. "
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
    source: str = str(MANIFEST)

    @classmethod
    def from_data(cls, data: dict, source: str) -> KitCommandCatalog:
        commands = tuple(c for c in data.get("commands", []) if isinstance(c, dict) and c.get("path"))
        return cls(str((data.get("meta") or {}).get("manifest_sha") or ""), commands, source)

    @classmethod
    def manifest_location(cls, root: Path) -> tuple[Path, str] | None:
        """The manifest file and a label: installed Kit first, repository copy as fallback."""
        from agp_cockpit.core.kit_installation import discover
        installation = discover(Path(root))
        if installation is not None:
            return installation.manifest_path, f"installed agentic-kit {installation.version}".strip()
        path = Path(root) / MANIFEST
        return (path, str(MANIFEST)) if path.is_file() else None

    @classmethod
    def load(cls, root: Path) -> KitCommandCatalog | None:
        location = cls.manifest_location(root)
        if location is None:
            return None
        path, source = location
        return cls.from_data(json.loads(path.read_text(encoding="utf-8")), source)

    def command(self, qualified_name: str) -> dict | None:
        for command in self.commands:
            if command.get("qualified_name") == qualified_name:
                return command
        return None

    @staticmethod
    def is_orchestrator(command: dict) -> bool:
        return command.get("surface") == "orchestrator"

    def effect_known(self, command: dict) -> bool:
        name = " ".join(str(p) for p in command["path"])
        return (not self.is_orchestrator(command) or name in REMOTE_EFFECT_COMMANDS
                or name in LOCAL_ORCHESTRATORS or command.get("safety") == "READ_ONLY")

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
        if not self.effect_known(command):
            return True   # AGP_UNKNOWN_EFFECT_ASKS_V1: fail closed
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
            "source": self.source,
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
                    **({} if self.effect_known(c) else {"effect": "unknown"}),
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


def kit_commands_used(source: str, catalog: KitCommandCatalog | None) -> list[dict]:
    """Manifest entries of every agentic-kit invocation in a work order."""
    if catalog is None:
        return []
    found: dict[str, dict] = {}
    for argv in _invocations(ast.parse(source)):
        if _program(argv[0]) != "agentic-kit":
            continue
        subcommands = []
        for token in argv[1:]:
            if token.startswith("-") or token == "<expr>":
                break
            subcommands.append(token)
        command = catalog.resolve(subcommands) if subcommands else None
        if command is not None:
            found[command["qualified_name"]] = command
    return [found[name] for name in sorted(found)]


def remote_effect_commands(source: str, catalog: KitCommandCatalog | None) -> list[str]:
    """Qualified names of remote-effect Kit commands used by a work order."""
    return [c["qualified_name"] for c in kit_commands_used(source, catalog)
            if catalog is not None and catalog.has_remote_effect(c)]


def unknown_effect_commands(source: str, catalog: KitCommandCatalog | None) -> list[str]:
    return [c["qualified_name"] for c in kit_commands_used(source, catalog)
            if catalog is not None and not catalog.effect_known(c)]


def orchestrator_violations(source: str, catalog: KitCommandCatalog | None) -> list[str]:
    """AGP_STANDARD_TASK_ORCHESTRATOR_V1 (R2) for work orders of standard tasks."""
    if catalog is None:
        return []
    used = kit_commands_used(source, catalog)
    violations = []
    if not any(catalog.is_orchestrator(c) for c in used):
        violations.append(
            "a standard task work order must run at least one agentic-kit orchestrator "
            f"(surface \"orchestrator\" in {catalog.source})"
        )
    for command in used:
        if catalog.has_remote_effect(command) and not catalog.is_orchestrator(command):
            violations.append(
                f"{command['qualified_name']} has a remote effect; in a standard task remote "
                "effects run only through an orchestrator"
            )
    return violations


def command_catalog_violations(source: str, catalog: KitCommandCatalog | None,
                               *, allow_remote_effects: bool = False,
                               require_orchestrator: bool = False) -> list[str]:
    tree = ast.parse(source)
    violations: list[str] = []
    if require_orchestrator:
        violations.extend(orchestrator_violations(source, catalog))
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
                    + f"' (not in {catalog.source})"
                )
    return sorted(set(violations))
