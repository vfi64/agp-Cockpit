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
import re
import shlex
from dataclasses import dataclass
from pathlib import Path

MANIFEST = Path("docs/reference/agentic-kit-commands.json")
SURFACE_ORDER = {"orchestrator": 0, "diagnostic": 1, "primitive": 2}
NETWORK_GIT = frozenset({"push", "fetch", "pull"})
# AGP_REMOTE_EFFECT_GATE_V1: Kit commands with an effect outside the local
# repository (push, fetch/pull, PR, merge, publish, remote branches). Since Kit
# 1.0.20 (KIT-GF-057) the manifest declares every one of them itself; the list
# stays as a second source (a command is remote when either says so) and a test
# fails when the manifest understates one again. "pr-closeout" (evaluates a JSON
# file) and "transfer publish-last-report" (writes the local outbox) left the
# list with 1.0.20: the Kit showed both implementations to be local only.
REMOTE_EFFECT_COMMANDS = frozenset({
    "github-create", "pr merge-if-green", "release-publish",
    "remote-branch-hygiene-apply", "remote-next",
    "transfer admin-refresh-pr", "transfer delete-merged-work-branch",
    "transfer evidence-pr-complete", "transfer fetch-origin", "transfer post-merge-complete",
    "transfer pr-closeout-complete", "transfer pr-complete", "transfer pr-create",
    "transfer pr-create-complete", "transfer pr-merge-safe",
    "transfer pull-current", "transfer push-current", "transfer remote-next",
    "transfer remote-work-start", "transfer sync-main", "work finish",
})
# Orchestrators known to act only locally (read, local files, local branches).
# Every other orchestrator either has a known remote effect or an unknown one;
# both need an approval (AGP_UNKNOWN_EFFECT_ASKS_V1). A new Kit orchestrator
# therefore asks until it is classified here or the Kit declares its effect.
LOCAL_ORCHESTRATORS = frozenset({
    "artifact-gc", "chat session-start", "docs lifecycle sweep", "dpa final-closeout-check",
    "init", "release prepare", "release ready", "release-prep",
    "transfer chat-switch-complete", "work recover", "work rescue", "workspace adopt",
    "workspace dpa-intake", "workspace init", "workspace remove", "workspace upgrade",
})
# AGP_MANIFEST_REMOTE_EFFECTS_V1 (Kit 1.0.19 manifest, owner 2026-10-07): the Kit declares
# ``remote_effects`` per command. A declared write effect makes a command remote even when
# the Cockpit lists it as local (post-release-doi-closeout: release_publish). The Cockpit's
# own list stays in force as well, so a command is remote when either source says so (Kit
# 1.0.19 said "none" for three commands that merge, delete or pull, KIT-GF-057, fixed in 1.0.20).
# An orchestrator the Cockpit has not classified still asks even when the manifest declares
# only reads (AGP_UNKNOWN_EFFECT_ASKS_V1): post-release-doi-closeout went from
# release_publish (1.0.19) to network_read (1.0.20) and keeps asking.
READ_ONLY_EFFECTS = frozenset({"none", "network_read"})
# AGP_DESTRUCTIVE_EXECUTE_GATE_V1 (plan P8, owner 2026-10-03): Kit routes whose
# dry run is local and read-only but whose signed ``--execute`` rewrites local
# history or discards files. The dry run runs freely; the execute needs an open
# human approval exactly like a remote effect, and its consumption is never
# refunded (nothing changes on origin, but the local repository does).
DESTRUCTIVE_EXECUTE_COMMANDS = frozenset({"work rescue", "work discard-changes"})
# AGP_OWNER_DECISION_EXECUTE_V1 (plan P10a, owner 2026-10-04): local routes whose
# execute applies decisions that belong to the owner (documentation lifecycle:
# defer or confirm a document). Gated exactly like a destructive execute.
OWNER_DECISION_EXECUTE_COMMANDS = frozenset({"docs lifecycle sweep"})
# AGP_CI_UPDATE_GUARD_V1 (KIT-GF-042): the Kit's managed-CI template update would
# replace the Cockpit's customized CI (pytest and Playwright jobs). Its execute is
# rejected outright; the Kit pin in both workflow files is updated by hand (P10b).
# Kept after Kit 1.0.18 (GF-E063), which now blocks a customized template itself:
# here ci-update can only block, so the rejection saves a remote turn and still
# guards against a Kit regression.
FORBIDDEN_EXECUTE_COMMANDS = frozenset({"workspace ci-update"})
EXECUTE_FLAG = "--execute"
# AGP_RELEASE_DRY_RUN_FREE_V1 (plan P11): remote-effect orchestrators whose dry run
# only reads (``release-publish --dry-run`` prints the plan and its approval
# signature). Only an invocation that may execute needs an open approval; when the
# work order mentions an execute flag anywhere, every invocation counts as one
# (fail closed against flags appended at run time).
# Kit 1.0.23 (KIT-GF-062): ``pr rerun-checks`` plans a rerun of never-started checks for free; only
# its signed --execute re-runs workflows (AGP_CI_RERUN_ROUTE_V1).
EXECUTE_GATED_REMOTE_COMMANDS = frozenset({"release-publish", "pr rerun-checks"})
EXECUTE_FLAGS = ("--execute", "--no-dry-run", "--allow-execute", "--expected-signature")
COMMAND_RULES = (
    "Command authority (standing rules for every work order): "
    "use only agentic-kit commands listed in the attached agentic-kit-command-digest.json "
    "(generated from the manifest of the installed Kit); never reconstruct commands from memory. "
    "Prefer the most comprehensive orchestrator command (surface \"orchestrator\") that covers the task; "
    "use diagnostic or primitive commands only when no orchestrator fits. "
    "Never run git push, git fetch or git pull. "
    "Raw git/gh commands that have a Kit wrapper (\"replaces_raw\") are rejected; use the wrapper. "
    "Commands marked \"remote_effect\" (push, pull/fetch, PR, merge, publish) or \"effect\": \"unknown\" "
    "run only with an open human approval; without one the Cockpit does not execute the work order and "
    "asks the human itself. The same holds for the signed --execute of work rescue and "
    "work discard-changes (their dry run is free). Do not work around this. "
    "\"commands\" lists the orchestrators completely; diagnostic and primitive commands are rows of "
    "\"compact\" (columns in \"compact_columns\", no options): read their options with "
    "`agentic-kit <command> --help` inside a work order."
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

    @staticmethod
    def declared_effects(command: dict) -> tuple[str, ...]:
        """The manifest's write effects of ``command`` (empty: none declared)."""
        effects = command.get("remote_effects")
        if not isinstance(effects, list):
            return ()
        return tuple(str(e) for e in effects if str(e) not in READ_ONLY_EFFECTS)

    def has_remote_effect(self, command: dict) -> bool:
        name = " ".join(str(p) for p in command["path"])
        if name in REMOTE_EFFECT_COMMANDS or self.declared_effects(command):
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
        """AGP_DIGEST_COMPACT_V1: orchestrators complete, the rest as a compact table."""
        ordered = sorted(self.commands, key=lambda c: (SURFACE_ORDER.get(c.get("surface"), 3), c["qualified_name"]))
        full, compact, replaces = [], [], {}
        for c in ordered:
            use = " ".join(str(c.get("when_to_use") or c.get("help") or "").split())
            effect = self.has_remote_effect(c) if self.effect_known(c) else "unknown"
            if c.get("surface") == "orchestrator":
                full.append({
                    "command": c["qualified_name"],
                    "surface": c.get("surface"),
                    "safety": c.get("safety"),
                    "use": use[:200],
                    "options": [o for p in c.get("params", []) for o in (p.get("opts") or [])][:12],
                    "replaces_raw": list(c.get("replaces_raw") or []),
                    "remote_effect": self.has_remote_effect(c),
                    **({} if self.effect_known(c) else {"effect": "unknown"}),
                })
                continue
            if use.startswith(f"Run {c['qualified_name']}"):
                use = ""          # the Kit's boilerplate help says nothing beyond the name
            compact.append([c["qualified_name"], c.get("surface"), effect, use[:80]])
            if c.get("replaces_raw"):
                replaces[c["qualified_name"]] = list(c["replaces_raw"])
        return {
            "kind": "agentic_kit_command_digest",
            "format": "compact-v1",
            "source": self.source,
            "manifest_sha": self.manifest_sha,
            "rules": COMMAND_RULES,
            "commands": full,
            "compact_columns": ["command", "surface", "remote_effect", "use"],
            "compact": compact,
            "compact_replaces_raw": replaces,
        }

    def write_digest(self, target: Path) -> Path:
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.digest(), ensure_ascii=False, separators=(",", ":")) + "\n"
        if not target.is_file() or target.read_text(encoding="utf-8") != payload:
            temporary = target.with_suffix(".tmp")
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(target)
        return target


# AGP_TOOL_LIST_NOT_INVOCATION_V1 (live 1569/1570/1583): a return bundle's
# ``"allowed_tools": ["agentic-kit", "git"]`` was read as the command
# ``agentic-kit git`` and rejected the work order. A list made only of program
# names is a tool list, not an invocation.
TOOL_NAMES = frozenset({"agentic-kit", "git", "gh", "python", "python3", "pytest", "ruff", "node", "npm"})


def _is_tool_list(values: list[str]) -> bool:
    return len(values) >= 2 and all(Path(v).name in TOOL_NAMES for v in values)


def _invocations(tree: ast.AST) -> list[list[str]]:
    """argv-like invocations written as string lists/tuples or command strings."""
    found: list[list[str]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple)) and node.elts:
            values = [e.value for e in node.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if values and len(values) == len(node.elts) and _is_tool_list(values):
                continue
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


def _may_execute(source: str) -> bool:
    """Any execute-related flag anywhere in the work order counts (the Kit itself
    executes only with --execute, --allow-execute and a matching signature)."""
    return any(flag in source for flag in EXECUTE_FLAGS)


def remote_effect_commands(source: str, catalog: KitCommandCatalog | None) -> list[str]:
    """Qualified names of remote-effect Kit commands used by a work order."""
    if catalog is None:
        return []
    found = []
    for command in kit_commands_used(source, catalog):
        if not catalog.has_remote_effect(command):
            continue
        path = " ".join(str(p) for p in command["path"])
        if path in EXECUTE_GATED_REMOTE_COMMANDS and not _may_execute(source):
            continue   # AGP_RELEASE_DRY_RUN_FREE_V1
        found.append(command["qualified_name"])
    return found


def destructive_execute_commands(source: str, catalog: KitCommandCatalog | None) -> list[str]:
    """``<qualified name> --execute`` for every destructive execute in a work order."""
    if catalog is None:
        return []
    found: set[str] = set()
    for argv in _invocations(ast.parse(source)):
        if _program(argv[0]) != "agentic-kit" or EXECUTE_FLAG not in argv[1:]:
            continue
        subcommands = []
        for token in argv[1:]:
            if token.startswith("-") or token == "<expr>":
                break
            subcommands.append(token)
        command = catalog.resolve(subcommands) if subcommands else None
        gated = DESTRUCTIVE_EXECUTE_COMMANDS | OWNER_DECISION_EXECUTE_COMMANDS
        if command is not None and " ".join(str(p) for p in command["path"]) in gated:
            found.add(f"{command['qualified_name']} {EXECUTE_FLAG}")
    return sorted(found)


def forbidden_execute_violations(source: str) -> list[str]:
    """AGP_CI_UPDATE_GUARD_V1: executes the Cockpit never runs (independent of a catalog)."""
    found = []
    for argv in _invocations(ast.parse(source)):
        if _program(argv[0]) != "agentic-kit":
            continue
        words = [w for w in argv[1:] if not w.startswith("-")]
        for name in FORBIDDEN_EXECUTE_COMMANDS:
            parts = name.split()
            hidden = "<expr>" in argv[1:] and EXECUTE_FLAG in source   # flag passed via a variable
            if words[:len(parts)] == parts and (EXECUTE_FLAG in argv[1:] or hidden):
                found.append(f"agentic-kit {name} --execute would replace the customized CI workflow "
                             "(KIT-GF-042); its dry run is allowed, the Kit pin is updated by hand")
    return found


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
SHA_FLAGS = ("--expected-head-sha",)


def short_head_sha_violations(source: str) -> list[str]:
    """AGP_FULL_HEAD_SHA_V1 (live 2026-10-05, step 1780): the Kit refuses a short head SHA
    for guarded pull-request actions only after the run; reject it before (correctable)."""
    found = []
    for argv in _invocations(ast.parse(source)):
        if _program(argv[0]) != "agentic-kit":
            continue
        for index, token in enumerate(argv):
            flag, _, inline = token.partition("=")
            if flag not in SHA_FLAGS:
                continue
            value = inline if inline else (argv[index + 1] if index + 1 < len(argv) else "")
            if value and value != "<expr>" and not FULL_SHA.match(value):
                found.append(f"{flag} {value} is not a full 40-character commit SHA; the Kit refuses short "
                             "SHAs for guarded pull-request actions (AGP_FULL_HEAD_SHA_V1) — pass the full "
                             "head SHA from the Cockpit-verified repository facts")
    return found


def approval_required_commands(source: str, catalog: KitCommandCatalog | None) -> list[str]:
    """Everything a work order may run only with an open human approval."""
    return sorted(set(remote_effect_commands(source, catalog))
                  | set(destructive_execute_commands(source, catalog)))


def approval_required_invocations(source: str, catalog: KitCommandCatalog | None) -> list[str]:
    """AGP_EXACT_COMMAND_APPROVAL_V1: the literal command lines of every approval-relevant
    agentic-kit invocation, ``agentic-kit`` plus its arguments joined by single spaces.

    A computed argument stays ``<expr>`` and an argument with whitespace stays as it is, so
    neither can equal an approved line: an exact approval never covers what the Cockpit
    cannot read literally.
    """
    if catalog is None:
        return []
    needed = set(approval_required_commands(source, catalog))
    lines = []
    for argv in _invocations(ast.parse(source)):
        if not argv or _program(argv[0]) != "agentic-kit":
            continue
        subcommands = []
        for token in argv[1:]:
            if token.startswith("-") or token == "<expr>":
                break
            subcommands.append(token)
        command = catalog.resolve(subcommands) if subcommands else None
        if command is not None and command["qualified_name"] in needed:
            lines.append(" ".join(["agentic-kit", *argv[1:]]))
    return sorted(dict.fromkeys(lines))


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
        violations.extend(
            f"{name} changes local history or files and requires an explicit human approval"
            for name in destructive_execute_commands(source, catalog)
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
