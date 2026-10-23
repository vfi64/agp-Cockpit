"""Standard tasks — declarative definitions (plan P5, AGP_STANDARD_TASK_FRAMEWORK_V1).

A standard task declares what it must achieve, not how: goal text for the
remote side (Kit commands are chosen from the digest, orchestrators first),
its input fields, a local precheck that blocks an invalid start, the scope of
remote effects its start click approves (R4; None = every remote effect asks)
and the local verifier that decides completion (``completion_contract``).
The UI, the bridge and the tests read these definitions only from here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agp_cockpit.core.standard_verifier import KIND as VERIFIER_KIND


def _no_precheck(_root: Path, _inputs: dict) -> str | None:
    return None


@dataclass(frozen=True)
class StandardTask:
    """A stable, user-facing task template backed by a local contract."""

    key: str
    label: str
    description: str
    contract_factory: Callable[..., dict]
    prompt_factory: Callable[..., str]
    effect: str = "local"                         # local | github
    inputs: tuple[str, ...] = ()
    precheck: Callable[[Path, dict], str | None] = _no_precheck
    approved_scope: frozenset[str] | None = None  # remote effects approved by the start click
    ci_gate_merge: bool = False                   # DONE needs the merged, green lifecycle
    confirm: str = ""                             # explicit start dialog (the approval, R4)
    offers_recover_on_interrupt: bool = False     # R6
    follow_up: str = ""                           # verb offered after DONE
    notes: tuple[str, ...] = field(default=())
    # AGP_RELEASE_RESUME_SCOPE_V1: a task may narrow its start-click scope by its inputs.
    scope_factory: Callable[[Path, dict], frozenset[str] | None] | None = None

    def contract(self, repository_root: Path, inputs: dict | None = None) -> dict:
        root = repository_root.expanduser().resolve()
        return self.contract_factory(root, dict(inputs or {})) if self.inputs \
            else self.contract_factory(root)

    def prompt(self, repository_root: Path, inputs: dict | None = None) -> str:
        root = repository_root.expanduser().resolve()
        return self.prompt_factory(root, dict(inputs or {})) if self.inputs \
            else self.prompt_factory(root)

    def scope(self, repository_root: Path, inputs: dict | None = None) -> frozenset[str] | None:
        """The remote effects the start click approves for these inputs."""
        if self.scope_factory is None:
            return self.approved_scope
        return self.scope_factory(repository_root.expanduser().resolve(), dict(inputs or {}))

    def check(self, repository_root: Path, inputs: dict | None = None) -> str | None:
        """Block reason, or None when the task may start."""
        return self.precheck(repository_root.expanduser().resolve(), dict(inputs or {}))


def _chat_switch_contract(repository_root: Path) -> dict:
    return {
        "title": "Standard Task: Chat wechseln",
        "goal": (
            "Create and validate a complete successor handoff package for the "
            "currently configured repository without starting further product work."
        ),
        "repository_root": str(repository_root),
        "completion_contract": {"kind": "verified-successor-handoff-v1"},
        "acceptance_criteria": [
            "The canonical successor handoff package is generated.",
            "All required handoff files exist and validation_report.json is PASS.",
            "A detailed successor prompt is produced with absolute paths.",
            "No further development work starts after a PASS result.",
        ],
        "constraints": [
            "Use the repository's current Agentic Project Kit authority and contracts.",
            "The local authority must explicitly allow both git and agentic-kit.",
            "Do not change product files during handoff preparation.",
            "Fail closed on missing or invalid handoff evidence.",
        ],
    }


def _chat_switch_prompt(repository_root: Path) -> str:
    return f"""CHAT SWITCH STANDARD TASK

Prepare a complete, validated successor handoff for the Agentic Project Kit-managed repository at:
{repository_root}

This is a standard Cockpit task. Use the repository's current authoritative Kit route for chat switching. Prefer the installed route `agentic-kit transfer chat-switch-complete --json` when it is available; consult the current command authority only when that route is unavailable or fails.

Complete the handoff in one coherent local work order whenever possible. Capture the current branch, HEAD, worktree, installed Kit version, development state, open risks, established decisions, relevant runtime and log paths, and the next safe step. Generate the canonical successor package and verify these files:

- execution_contract.json
- successor_context.yaml
- validation_report.json
- source_manifest.json
- successor_prompt.md

Evaluate validation_report.json and continue only when it is PASS. Create a separate continuation brief only for repository-specific or volatile information that does not belong in the canonical package. Create a detailed start prompt containing the absolute repository path, absolute package and file paths, required reading order, current state, next step, diagnostics, and the rule that the successor must make no repository changes during initial handoff intake.

Pass on the communication contract: exactly one newly numbered Download/*.py work order per local step, no reused number, execution through run_next.py, exactly one canonical *_return_bundle.json per execution, complete result evaluation before the next work order, and large coherent steps.

Every start of this task requires a fresh local run with a new work order, even if an earlier handoff was completed in this conversation; an earlier result never completes a new start.

The attached Python file is the executable local work order. It must execute the authorized Kit command during its real run (for this task: `agentic-kit transfer chat-switch-complete --json`), capture its return code/stdout/stderr, validate the required handoff files and validation report, and write exactly one canonical return bundle into Download/. Printing a JSON object that merely describes an argv/cwd command is not execution evidence and is an invalid work order. `--self-test` must validate structure without running the Kit command or mutating the repository.

Keep the attached Python work order deliberately small: at most 80 source lines and 16 KiB, with no long comments, embedded logs, recursive Download scans, or prose outside the attachment. Before attaching it, verify that the complete file parses, has a `main()` plus `if __name__ == "__main__"`, accepts `--self-test`, executes the Kit command during the real run, and writes the one return bundle. A truncated or incomplete attachment is worse than a short diagnostic response and must not be submitted.

Write exactly one canonical JSON completion result into the local return bundle for this standard task, using exactly these keys: "status" (PASS, BLOCKED or FAIL), "package_path", "validation_status", "continuation_brief_path", "detailed_start_prompt_path" (a file Download/<this step>_*.md), "next_action", and "execution" with "argv", "cwd" and "returncode" of the Kit command. The Cockpit independently validates a successful package and ends this task after confirmed result delivery. When asked to acknowledge the final result, acknowledge only; do not produce another work order. Visible JSON is not an executable command or completion authority. On PASS, do not start further development in this chat.
"""


# --- shared remote-side text --------------------------------------------------

_COMMON = """
Choose every agentic-kit command yourself from the attached command digest of the installed
Kit: the most comprehensive orchestrator that covers the goal in one run; primitives only where
no orchestrator fits. Exactly one newly numbered Download/<step>_*.py work order per local
step, executed through run_next.py, one canonical return bundle per execution; evaluate each
result completely before the next work order. Use the Cockpit-verified repository facts in each
continuation instead of re-running commands to check a result.
CI that never ran (AGP_CI_NOT_STARTED_V1): when every failed check of a pull request ended
without running — no job log ("log not found"), zero duration, cancelled or never acquired by a
runner — the cause is GitHub (runner, Actions quota or billing), not the code. Re-run them only
through the Kit (AGP_CI_RERUN_ROUTE_V1, Kit 1.0.23, KIT-GF-062): `agentic-kit pr rerun-checks --pr
<n>` plans for free and refuses real test failures; its signed --execute re-runs workflows and
needs the owner's approval. Raw gh stays forbidden: if the Kit refuses or no approval is open, stop
with NEEDS_HUMAN that names the pull request, the run and „Re-run all jobs“ on GitHub;
never ask for more tool authority.
"""


def _git_value(root: Path, *args: str) -> str:
    import subprocess
    try:
        done = subprocess.run(["git", *args], cwd=str(root), text=True, capture_output=True,
                              timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (done.stdout or "").strip() if done.returncode == 0 else ""


def _verifier(name: str, **params) -> dict:
    return {"kind": VERIFIER_KIND, "verifier": name, "params": params}


# --- P6 Abschließen -----------------------------------------------------------

# AGP_FINISH_APPROVAL_SCOPE_V1 (R4): the effect classes the start click of
# "Abschließen" approves — publishing, pull request, merge, post-merge closeout
# and main synchronization; any other remote effect still asks.
def _finish_scope() -> frozenset[str]:
    from agp_cockpit.core.ci_gate import LIFECYCLE_COMMANDS
    return frozenset(LIFECYCLE_COMMANDS | {"agentic-kit transfer pr-merge-safe",
                                           "agentic-kit transfer pull-current"})


def _finish_precheck(root: Path, _inputs: dict) -> str | None:
    from agp_cockpit.core.merged_branch_guard import CHANGES, NO_COMMITS, relation
    branch = _git_value(root, "branch", "--show-current")
    if not branch:
        return "Kein Branch ausgecheckt (detached HEAD) — Abschließen braucht einen Arbeitsbranch."
    if branch in ("main", "master"):
        if _main_followup_open(root):
            return None   # AGP_FINISH_OPEN_FOLLOWUP_V1: complete the open post-merge lifecycle
        return ("Abschließen läuft nie von main aus (R4), außer um einen offenen Post-Merge-Abschluss "
                "des Kits zu Ende zu bringen. Erst „Arbeit beginnen“.")
    dirty = bool(_git_value(root, "status", "--porcelain"))
    found = relation(root, branch, "origin/main")
    if found == CHANGES or (dirty and found in (NO_COMMITS, None)):
        return None
    if found is None:
        return f"Branch {branch} ist mit origin/main nicht vergleichbar — erst Lagebericht/Wiederherstellen."
    return (f"Branch {branch} enthält nichts, was nicht schon in origin/main ist "
            "(bereits gemergt oder ohne eigene Änderungen) — nichts abzuschließen.")


def _main_followup_open(root: Path) -> bool:
    """AGP_FINISH_OPEN_FOLLOWUP_V1: main is clean, equals its tracking ref
    origin/main, and the Kit's post-merge check is not PASS."""
    from agp_cockpit.core.repo_state import WORKSPACE_MARKERS
    if not any((Path(root) / marker).is_file() for marker in WORKSPACE_MARKERS):
        return False
    if _git_value(root, "status", "--porcelain"):
        return False
    head = _git_value(root, "rev-parse", "HEAD")
    if not head or head != _git_value(root, "rev-parse", "--verify", "-q", "refs/remotes/origin/main"):
        return False
    from agp_cockpit.core.kit_installation import discover
    from agp_cockpit.core.repo_state import post_merge_check
    kit = discover(Path(root))
    return kit is not None and post_merge_check(Path(root), kit)[0] == "NOT_PASS"


def _finish_contract(root: Path) -> dict:
    branch = _git_value(root, "branch", "--show-current")
    return {
        "title": "Standard Task: Abschließen",
        "goal": (f"Finish the work branch {branch}: publish it, pull request, green CI, merge, "
                 "complete post-merge lifecycle, then local main equal to origin/main."),
        "repository_root": str(root),
        "completion_contract": {"kind": "ci-merged-lifecycle-v2"},
        "acceptance_criteria": [
            "Pull request merged with green CI for its head (verified by the Cockpit).",
            "Kit post-merge lifecycle complete; local main equals origin/main; main green.",
        ],
        "constraints": [("Never from main, except to complete an open Kit post-merge lifecycle "
                         "(AGP_FINISH_OPEN_FOLLOWUP_V1)."), "No force push.",
                        "Merge only through the Kit's green-CI gates."],
    }


def _finish_prompt(root: Path) -> str:
    branch = _git_value(root, "branch", "--show-current")
    if branch in ("main", "master"):
        return _finish_followup_prompt(root)
    return f"""STANDARD TASK — ABSCHLIESSEN (finish the work branch)

Repository: {root}
Work branch: {branch}

Goal: publish the work branch, open its pull request, wait for green CI, merge it through the
Kit's gates and complete the Kit's post-merge lifecycle, so that local main equals origin/main.

The human approved exactly these effects by starting this standard task (publishing, pull
request, merge, post-merge closeout, main synchronization): do not ask NEEDS_HUMAN for them.
Any other remote effect still needs a decision. Never force-push; never merge red CI.
{_pr_category_rule(root)}{_COMMON}
Completion is verified locally: DONE is accepted only after the Cockpit checked that the pull
request is merged with green CI, the post-merge check passes and main is green. Name the pull
request as "pr" in the DONE file. Run the lifecycle once; do not open another pull request for a
branch the facts report as already merged.
"""


def _finish_followup_prompt(root: Path) -> str:
    return f"""STANDARD TASK — ABSCHLIESSEN (complete the open post-merge lifecycle on main)

Repository: {root}
Branch: main (clean, equal to origin/main; AGP_FINISH_OPEN_FOLLOWUP_V1)

Situation: the last pull request is merged, but the Kit's post-merge check is not PASS — the
Kit's post-merge lifecycle is incomplete, typically because its own follow-up pull request
(successor-package or handoff refresh) is still open or its CI was re-run.

Goal: complete exactly that lifecycle with the Kit's closeout orchestrator from the command digest, so
that the follow-up pull request is merged with green CI, the post-merge check passes and local
main equals origin/main. Do not commit anything, do not start a work branch and do not open a
pull request for main; if the Kit reuses its existing follow-up pull request, that is expected.

The human approved exactly these effects by starting this standard task (merge of the Kit's
follow-up pull request, post-merge closeout, main synchronization): do not ask NEEDS_HUMAN for
them. Any other remote effect still needs a decision. Never force-push; never merge red CI.
{_COMMON}
Completion is verified locally: DONE is accepted only after the Cockpit checked that the
follow-up pull request is merged with green CI, the post-merge check passes and main is green.
Name that pull request as "pr" in the DONE file. Run the closeout once.
"""


# --- P7 Arbeit beginnen -------------------------------------------------------

WORK_KINDS = ("feat", "fix", "docs", "chore", "refactor", "test")
_NAME = __import__("re").compile(r"^[a-z0-9][a-z0-9-]{1,48}[a-z0-9]$")
WORK_START_SCOPE = frozenset({
    "agentic-kit transfer remote-work-start", "agentic-kit transfer sync-main",
    "agentic-kit transfer pull-current", "agentic-kit work start",
})


def work_branch(inputs: dict) -> str:
    return f"{inputs.get('kind', '')}/{inputs.get('name', '')}"


def _work_start_precheck(root: Path, inputs: dict) -> str | None:
    kind, name = str(inputs.get("kind") or ""), str(inputs.get("name") or "")
    if kind not in WORK_KINDS:
        return f"Art muss eine von {', '.join(WORK_KINDS)} sein."
    if not _NAME.match(name):
        return "Name: 3–50 Zeichen, nur a–z, 0–9 und Bindestrich, nicht am Anfang oder Ende."
    branch = work_branch(inputs)
    for ref in (branch, f"origin/{branch}"):
        if _git_value(root, "rev-parse", "--verify", "--quiet", ref):
            return f"Branch {branch} existiert schon ({ref}) — anderen Namen wählen."
    if _git_value(root, "status", "--porcelain"):
        return "Das Arbeitsverzeichnis hat ungesicherte Änderungen — erst abschließen oder wiederherstellen."
    return None


def _work_start_contract(root: Path, inputs: dict) -> dict:
    branch = work_branch(inputs)
    return {
        "title": f"Standard Task: Arbeit beginnen ({branch})",
        "goal": (f"Start new work on branch {branch} from the current origin/main with confirmed "
                 "Kit rules and a clean worktree; no product changes."),
        "repository_root": str(root),
        "completion_contract": _verifier("work-started", branch=branch),
        "acceptance_criteria": [f"Current branch is {branch}.", "It contains the current origin/main.",
                                "The worktree is clean."],
        "constraints": ["No product changes.", "No pull request."],
    }


def _work_start_prompt(root: Path, inputs: dict) -> str:
    branch = work_branch(inputs)
    return f"""STANDARD TASK — ARBEIT BEGINNEN (start new work)

Repository: {root}
New work branch: {branch} (kind: {inputs.get('kind')})

Goal: synchronize main with origin/main, confirm the Kit's rules for this workspace, and create
and check out the new work branch {branch} from the current origin/main. The worktree must be
clean afterwards. Make no product changes and open no pull request.

The human approved by starting this task exactly the synchronization with origin and the
creation of the work branch through the Kit's work-start route. Any other remote effect still
needs a decision.
{_COMMON}
Completion is verified locally: DONE is accepted only when the current branch is {branch}, it
contains the current origin/main and the worktree is clean.
"""


# --- P8 Wiederherstellen (diagnosis first) -------------------------------------

def _recover_contract(root: Path) -> dict:
    return {
        "title": "Standard Task: Wiederherstellen",
        "goal": ("Diagnose drift or an interrupted lifecycle and restore a clean, synchronized "
                 "repository state; destructive steps only after a human decision."),
        "repository_root": str(root),
        "completion_contract": _verifier("recovered"),
        "acceptance_criteria": [("The Cockpit's Lagebericht reports BEREIT, a work branch with own "
                                 "work, or main with only the Kit's post-merge follow-up open.")],
        "constraints": [
            "Diagnose first.",
            ("Destructive steps only through Kit routes, dry run first, the signed execute only after "
             "NEEDS_HUMAN and approval (AGP_DESTRUCTIVE_EXECUTE_GATE_V1)."),
        ],
    }


def _recover_prompt(root: Path) -> str:
    return f"""STANDARD TASK — WIEDERHERSTELLEN (recover)

Repository: {root}

Goal: find out why the repository is not in a clean state (drift from origin/main, unexpected
changes, an interrupted publish/merge/post-merge lifecycle, a failing post-merge check) and
restore a clean, synchronized state: either a clean work branch that can be finished, or main
equal to origin/main with a passing post-merge check.

Start with the Kit's read-only recovery and divergence diagnosis. Repair only through Kit
routes from the command digest, which cover: main only behind origin/main, a detached HEAD
without own commits, discarding changes on a work branch, and — since Kit 1.0.14 — the
non-lossy rescue of main with uncommitted changes or with commits that are not on origin/main
(KIT-GF-033): it first saves everything on a new rescue branch and only then realigns main with
origin/main. Destructive routes always run as a dry run first; report the planned actions, the
rescue branch and the dry-run signature in NEEDS_HUMAN, and run the signed execute only after the
human's approval (the Cockpit refuses the execute without one). Never run raw git that changes
the repository (reset, checkout, switch, clean, restore, branch -f/-D, stash). If the Kit
refuses a case, stop with NEEDS_HUMAN, state the diagnosis and leave the repair to the human.
Remote effects ask as usual. If an interrupted lifecycle only needs to be completed (for example
an open, green pull request), say so in NEEDS_HUMAN instead of starting it. After a rescue, name
the rescue branch in DONE so the human can continue the saved work on it.
{_COMMON}
A work branch without own commits and without changes is a leftover, not work: after removing
its changes, return to main through the Kit's main synchronization route.
Completion is verified locally: DONE is accepted only when the Cockpit's own Lagebericht reports
BEREIT, a work branch with own work, or main with only the Kit's post-merge follow-up open.
"""


# --- P11 Release -----------------------------------------------------------------

_VERSION = __import__("re").compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def _release_scope() -> frozenset[str]:
    """AGP_RELEASE_APPROVAL_SCOPE_V1: the start click approves the release branch and
    its pull-request lifecycle; the live tag publication is not in the scope and
    always asks (with the signature of its dry run)."""
    return frozenset(_finish_scope() | WORK_START_SCOPE)


# AGP_RELEASE_RESUME_SCOPE_V1 (proposal 7, owner 2026-10-04: yes): when main already names the
# version (phase 1 merged, only the tag missing), the start click approves only bringing main
# up to date; branch, push and pull-request effects are not needed and not granted. The tag
# push asks as always (signed dry run, NEEDS_HUMAN).
RELEASE_RESUME_SCOPE = frozenset({"agentic-kit transfer sync-main", "agentic-kit transfer pull-current"})


# AGP_RELEASE_RUN_AUTONOMY_V1 (owner 2026-10-08 „vollautonom“, 2026-10-13 „1b“): a workspace that
# declares release.approval: upfront releases through the Kit's orchestrator alone. The start click
# approves exactly that run (it syncs main, prepares, merges the release pull request, tags and
# publishes); the Kit records the consent at gate B4 and refuses any later gate whose version, tag or
# target commit differs (KIT-GF-061). Its own sync routes stay in scope for a resumed run.
RELEASE_RUN_SCOPE = frozenset({"agentic-kit release run", "agentic-kit transfer sync-main",
                               "agentic-kit transfer pull-current"})


def release_config(root: Path) -> dict:
    try:
        import yaml
        data = yaml.safe_load((Path(root) / ".agentic/config.yaml").read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError):
        return {}
    release = (data or {}).get("release") if isinstance(data, dict) else None
    return release if isinstance(release, dict) else {}


def release_run_route(root: Path) -> bool:
    """AGP_RELEASE_RUN_AUTONOMY_V1: the workspace consents up front, so the Kit's release run carries it."""
    return release_config(root).get("approval") == "upfront"


# AGP_RELEASE_GATE_PATHS_V1 (2026-10-13, release 0.2.5): gate B4 of the Kit's release run lists the paths
# its release branch commits. Besides the release files the Kit's preparation writes, the Kit's own branch
# completion refreshes its handoff state under .agentic/state/. Any other path is a difference.
RELEASE_FILES = ("CHANGELOG.md", "pyproject.toml")
KIT_STATE_PREFIX = ".agentic/state/"


def release_gate_files(root: Path) -> tuple[str, ...]:
    """The release files of gate B4: changelog, project version and every declared version anchor."""
    anchors = release_config(root).get("version_anchors")
    paths = [str(a.get("path")) for a in anchors if isinstance(a, dict) and a.get("path")] \
        if isinstance(anchors, list) else []
    return tuple(dict.fromkeys([*RELEASE_FILES, *paths]))


def release_gate_differences(root: Path, paths: list[str]) -> list[str]:
    """The paths of a B4 gate outside the release files and the Kit's own state (empty: the gate fits)."""
    allowed = set(release_gate_files(root))
    return [p for p in paths if p not in allowed and not p.startswith(KIT_STATE_PREFIX)]


def _release_branch(root: Path, version: str) -> str:
    prefix = str(release_config(root).get("branch_prefix") or "") if release_run_route(root) else ""
    return f"{prefix or 'release/'}{version}"


def _release_scope_for(root: Path, inputs: dict) -> frozenset[str]:
    version = str(inputs.get("version") or "").strip()
    if release_run_route(root):
        return RELEASE_RUN_SCOPE          # a stopped run resumes from the Kit's own state
    if version and version == _current_version(root):
        return RELEASE_RESUME_SCOPE
    return _release_scope()


def _version_tuple(text: str) -> tuple[int, ...] | None:
    match = _VERSION.match(str(text or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None


def _current_version(root: Path) -> str:
    import re
    try:
        text = (Path(root) / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return ""
    found = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return found.group(1) if found else ""


def _publication(root: Path) -> str:
    from agp_cockpit.core.release_policy import _workspace_publication
    return _workspace_publication(root)


# AGP_KIT_GITHUB_RELEASE_V1 (P11c, owner 2026-10-05): the Release button handles the private
# tag (publication: none) and the tag plus the Kit-made GitHub Release entry (github); never
# PyPI or Zenodo.
RELEASE_PUBLICATIONS = ("none", "github")


def _pr_category_rule(root: Path) -> str:
    """AGP_PR_RELEASE_CATEGORY_V1 + AGP_PR_CATEGORY_ROUTES_V1: the remote side must give every new
    pull request a category, and the prompt names how (live 2026-10-22: #374 lost it four times)."""
    from agp_cockpit.core.release_hygiene import (
        CATEGORY_HINT,
        CATEGORY_OPTION,
        github_releases_declared,
    )
    if not github_releases_declared(root):
        return ""
    suggested = suggested_category(root)
    return (f"Every pull request you create needs a release-note category (one of {CATEGORY_HINT}): pass "
            f"{CATEGORY_OPTION} <category> to the Kit route that creates it, or a --body with a line "
            "'release-note-category: <category>'. A work order without it is rejected before it runs."
            + (f" The branch changes only {suggested[1]}: use {CATEGORY_OPTION} \"{suggested[0]}\"."
               if suggested else "") + "\n")


def suggested_category(root: Path) -> tuple[str, str] | None:
    """The category when the changed paths decide it alone: documentation only → Docs, tests only →
    Tests / Gates. Anything else is the remote side's choice."""
    names = set(_git_value(root, "diff", "--name-only", "origin/main...HEAD").splitlines())
    names |= set(_git_value(root, "diff", "--name-only", "HEAD").splitlines())        # uncommitted, tracked
    names |= set(_git_value(root, "ls-files", "--others", "--exclude-standard").splitlines())   # new files
    names.discard("")
    if not names:
        return None
    if all(name.endswith(".md") or name.startswith("docs/") for name in names):
        return "Docs", "documentation"
    if all(name.startswith("tests/") for name in names):
        return "Tests / Gates", "tests"
    return None


def _release_precheck(root: Path, inputs: dict) -> str | None:
    version = str(inputs.get("version") or "").strip()
    wanted = _version_tuple(version)
    if wanted is None:
        return "Version im Format X.Y.Z angeben (z. B. 0.1.1)."
    if _publication(root) not in RELEASE_PUBLICATIONS:
        return ("Der Release-Button macht nur Releases ohne PyPI und Zenodo: .agentic/config.yaml muss "
                "publication: none oder publication: github deklarieren.")
    if _git_value(root, "branch", "--show-current") != "main":
        return "Release startet nur auf main (Zustand BEREIT)."
    if _git_value(root, "status", "--porcelain"):
        return "main hat ungesicherte Änderungen — erst abschließen oder wiederherstellen."
    head = _git_value(root, "rev-parse", "HEAD")
    if not head or head != _git_value(root, "rev-parse", "--verify", "-q", "refs/remotes/origin/main"):
        return "main ist nicht synchron mit origin/main — erst Lagebericht/Wiederherstellen."
    if _git_value(root, "rev-parse", "--verify", "--quiet", f"refs/tags/v{version}"):
        return f"Tag v{version} existiert schon — andere Version wählen."
    # AGP_RELEASE_KIT_MATCHES_CI_V1 (live 2026-10-22, release 0.3.2 #378): the release preparation
    # synchronizes AGENTS.md and the command reference with the installed Kit; with 1.1.4 installed
    # and 1.1.5 in the CI it wrote the 1.1.4 manifest back, and the tag carries it.
    from agp_cockpit.core.system_check import kit_ci_mismatch
    mismatch = kit_ci_mismatch(root)
    if mismatch:
        return (f"Release gesperrt: {mismatch}. Die Release-Vorbereitung schreibt die Befehlsreferenz mit "
                "dem lokalen Kit — erst das lokale Kit auf die CI-Version bringen (kit update), dann Release.")
    current = _version_tuple(_current_version(root))
    if current is not None and wanted < current:
        return f"Version {version} ist kleiner als die aktuelle {_current_version(root)}."
    if _current_version(root) == version and not release_run_route(root):
        # AGP_RELEASE_RESUME_PHASE2_V1 (live 2026-10-04, release 0.1.1): phase 1 is merged and only
        # the tag is missing. The squash-merged release branch may still exist (origin/release/<v>
        # stayed after #204); it is not reused, the task skips to the tag.
        return None
    branch = _release_branch(root, version)
    for ref in (branch, f"origin/{branch}"):
        if _git_value(root, "rev-parse", "--verify", "--quiet", ref):
            return f"Branch {branch} existiert schon ({ref})."
    return None


def release_resume_version(root: Path) -> str:
    """AGP_RELEASE_RESUME_PHASE2_V1: the version main already names whose tag is still
    missing (phase 1 merged, tag not pushed), else ""."""
    current = _current_version(root)
    if _version_tuple(current) is None:
        return ""
    if _git_value(root, "rev-parse", "--verify", "--quiet", f"refs/tags/v{current}"):
        return ""
    return current


def _release_publication_text(root: Path) -> tuple[str, str]:
    """(constraint, what the live run publishes) for the repository's publication."""
    if _publication(root) == "github":
        return (("publication: github — the Kit's signed run creates the annotated tag and the GitHub "
                 "Release entry; no PyPI or Zenodo; never gh release in a work order."),
                "the annotated tag and the GitHub Release entry (title and notes from the Kit)")
    return ("publication: none — no GitHub Release, PyPI or Zenodo.", "only the annotated tag")


def _release_contract(root: Path, inputs: dict) -> dict:
    version = str(inputs.get("version") or "").strip()
    constraint, _ = _release_publication_text(root)
    github = _publication(root) == "github"
    run = release_run_route(root)
    return {
        "title": f"Standard Task: Release {version}",
        "goal": (f"Release {version} through the Kit's release run under the owner's up-front consent: "
                 "release branch with the Kit's preparation, merged with green CI, annotated tag and "
                 "publication, each gate only while it matches this release." if run else
                 f"Private release {version}: release branch with the Kit's release preparation, "
                 "merged with green CI, then the annotated tag pushed through the Kit's signed private "
                 "release route after the owner's approval."),
        "repository_root": str(root),
        "completion_contract": _verifier("released", version=version),
        "acceptance_criteria": [
            f"Release pull request for {version} merged with green CI; main green.",
            f"Annotated tag v{version} on origin; its commit is in origin/main; pyproject names {version}.",
        ] + ([f"GitHub Release entry v{version} exists and is not a draft."] if github else []),
        "constraints": [constraint,
                        ("The start click is the consent; the Kit's release run records it and stops on "
                         "any gate that differs from this release." if run else
                         "The live tag publication only with the owner's approval of its signed plan."),
                        "No force push; no marker file."],
    }


def _release_approval_text(prepared: bool) -> str:
    if prepared:   # AGP_RELEASE_RESUME_SCOPE_V1
        return ("The human approved by starting this task only bringing main up to date (main "
                "synchronization); no branch, push or pull request is needed or approved. The live tag "
                "publication is not approved yet and always asks.")
    return ("The human approved by starting this task the release branch and its pull-request lifecycle\n"
            "(starting the branch, publishing, pull request, merge, post-merge closeout, main synchronization): "
            "do not\nask NEEDS_HUMAN for them. The live tag publication is not approved yet and always asks.")


# AGP_RELEASE_CHANGELOG_SUMMARY_V1 (live 2026-10-04, release 0.1.1): the changelog entry was a
# one-line stub and the Unreleased section stayed; step 2 names the summary source.
def _release_prompt(root: Path, inputs: dict) -> str:
    version = str(inputs.get("version") or "").strip()
    if release_run_route(root):
        return _release_run_prompt(root, version)
    prepared = _current_version(root) == version
    phase_one = (f"""Phase 1 is already done: main names version {version} (prepared and merged earlier) and
the tag is missing. Skip to phase 2.""" if prepared else f"""Phase 1 — release branch:
1. Start the work branch release/{version} from the current origin/main through the Kit's
   work-start route.
2. Run the Kit's release preparation for version {version} in write mode (it updates the version
   anchors declared in .agentic/config.yaml and writes the "## v{version}" section of the
   changelog, which is also the text of the GitHub Release entry). Its summary lines name the
   user-visible changes since the previous release tag: the entries of the CHANGELOG.md
   "Unreleased" section that no version section carries yet, each passed verbatim (the text after
   "- "), completed from the merged pull requests since that tag — never a one-line stub such as
   "Prepare release". Summary lines go to the Kit as a JSON file (--summary-lines-from <file>.json
   holding a JSON list of strings); a text file is rejected (AGP_RELEASE_SUMMARY_JSON_V1). Reading
   CHANGELOG.md to build them is fine, but never write CHANGELOG.md, pyproject.toml,
   docs/releases/versions.json or the build identity yourself on the release branch: only the Kit
   writes the release state, and running its preparation again replaces its own section
   (AGP_RELEASE_KIT_OWNED_FILES_V1). The Kit removes from "Unreleased" exactly the entries it
   carries into the version section (KIT-GF-060, Kit 1.0.21). The Cockpit creates the release pull
   request only with exactly one "## v{version}" section (AGP_RELEASE_CHANGELOG_GATE_V1).
3. If the repository has docs/planning/RELEASE_POLICY.md, perform the release-branch steps it names
   in the same branch. agp-Cockpit has none left: its build identity follows the version the Kit
   writes (AGP_BUILD_ID_DERIVED_V1: src/agp_cockpit/version.py and chrome_extension/build_identity.js
   then name exactly release-{version}); its tests check it and the Cockpit rejects the release pull
   request otherwise (AGP_RELEASE_BUILD_ID_GATE_V1).
4. Finish the branch through the Kit's pull-request lifecycle: green CI, merge, post-merge closeout,
   local main equal to origin/main.""")
    constraint, published = _release_publication_text(root)
    return f"""STANDARD TASK — RELEASE {version}

Repository: {root}
Version: {version} · tag v{version} · {constraint}
{_pr_category_rule(root)}
{phase_one}

Phase 2 — tag publication (always asks):
5. On main, run the Kit's release publication as a dry run. Then stop with NEEDS_HUMAN and
   state the version, the tag, the target commit, the planned actions and the approval signature
   of the dry run, so the owner can approve exactly that plan.
6. After the approval, run the live publication with that signature (the Kit's execute options
   with the expected signature); it publishes {published}. Never create the
   marker file .agentic/release/ENABLE_LIVE_PUBLISH. If HEAD changed since the dry run, start again
   at step 5.

{_release_approval_text(prepared)}
Never force-push; never merge red CI.
{_COMMON}
Completion is verified locally: DONE is accepted only after the Cockpit checked that the release
pull request is merged with green CI, main is green, the annotated tag v{version} is on origin, its
commit is in origin/main and pyproject.toml at the tag names {version}{' and the GitHub Release entry exists' if _publication(root) == 'github' else ''}.
Name the release pull request as "pr" in the DONE file.
"""


def release_approver(root: Path) -> str:
    """Who consents: the local git user (the one who clicks), else the owner of origin."""
    import re
    name = _git_value(root, "config", "user.name")
    if name:
        return name
    match = re.search(r"github\.com[:/]([^/:]+)/", _git_value(root, "remote", "get-url", "origin") or "")
    return match.group(1) if match else "owner"


def _release_run_prompt(root: Path, version: str) -> str:
    """AGP_RELEASE_RUN_AUTONOMY_V1: the whole release is one Kit orchestrator under up-front consent."""
    import datetime
    constraint, published = _release_publication_text(root)
    branch = _release_branch(root, version)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")   # noqa: DTZ005 - the owner's local time
    consent = f"AGP Cockpit start click: Release {version} ({stamp})"
    approver = release_approver(root)
    github = _publication(root) == "github"
    files = ", ".join(release_gate_files(root))
    return f"""STANDARD TASK — RELEASE {version}

Repository: {root}
Version: {version} · tag v{version} · branch {branch} · {constraint}

The whole release is one run of the Kit's end-to-end release orchestrator, chosen from the command
digest (AGP_RELEASE_RUN_AUTONOMY_V1): it synchronizes main, checks readiness, prepares {branch},
merges the release pull request after green CI, creates the annotated tag and publishes {published}.
This workspace declares release.approval: upfront: the owner's start click is the consent for exactly
this release; the Kit records it once at gate B4 and lets later gates pass only while version, tag and
target commit match the consented plan (KIT-GF-061). The start click approves this orchestrator and
the Kit's main synchronization only; any other remote effect asks.
1. Summary lines: read the "Unreleased" section of CHANGELOG.md and hand every entry that no version
   section carries yet to the orchestrator verbatim (the text after "- "), one summary-line option
   each — never a one-line stub such as "Prepare release". Never write CHANGELOG.md, pyproject.toml,
   docs/releases/versions.json or the build identity yourself (AGP_RELEASE_KIT_OWNED_FILES_V1): the Kit's
   preparation writes them, removes the carried entries from "Unreleased" (KIT-GF-060) and the build
   identity follows the version (AGP_BUILD_ID_DERIVED_V1).
2. Plan: run the orchestrator for version {version} with those summary lines and JSON output, without
   its execute option. It stops at gate B4 with AWAITING_APPROVAL, the gate and its approval
   signature. Continue only when the gate names version {version} and branch {branch}, and its paths
   are only the release files ({files}) and the Kit's own state under {KIT_STATE_PREFIX} (the
   Kit's branch completion refreshes the handoff there; AGP_RELEASE_GATE_PATHS_V1). Any other path, or
   another version or branch: stop with NEEDS_HUMAN and name it.
3. Execute: run it again with its execute option, the expected signature of that gate, --approved-by
   "{approver}" and --consent-source "{consent}". Do not ask NEEDS_HUMAN for this consent.
4. If it stops at another gate with AWAITING_APPROVAL, pass that gate the same way only when it names
   version {version}, tag v{version} and the consented target commit.
5. Stop with NEEDS_HUMAN on FAIL, BLOCKED, a recovery offer (D2R) or any difference from this release;
   never work around a Kit blocker and never run the Kit's single release, publication or pull-request
   steps yourself for this release. A stopped run resumes from the Kit's own state when the
   orchestrator is started again for {version}.
Never force-push; never merge red CI; never gh release.
{_COMMON}
Completion is verified locally: DONE is accepted only after the Cockpit checked that the release
pull request is merged with green CI, main is green, the annotated tag v{version} is on origin, its
commit is in origin/main and pyproject.toml at the tag names {version}{' and the GitHub Release entry exists' if github else ''}.
Name the release pull request as "pr" in the DONE file (the run's B4 result names it).
"""


# --- P10a Pflege (maintenance) ---------------------------------------------------

def maintenance_branch(today: str | None = None) -> str:
    import datetime
    return f"chore/pflege-{today or datetime.date.today().isoformat()}"   # noqa: DTZ011 - the owner's local day


def _maintain_precheck(root: Path, _inputs: dict) -> str | None:
    if _git_value(root, "branch", "--show-current") != "main":
        return "Pflege startet nur auf main (Zustand BEREIT)."
    if _git_value(root, "status", "--porcelain"):
        return "main hat ungesicherte Änderungen — erst abschließen oder wiederherstellen."
    head = _git_value(root, "rev-parse", "HEAD")
    if not head or head != _git_value(root, "rev-parse", "--verify", "-q", "refs/remotes/origin/main"):
        return "main ist nicht synchron mit origin/main — erst Lagebericht/Wiederherstellen."
    branch = maintenance_branch()
    for ref in (branch, f"origin/{branch}"):
        if _git_value(root, "rev-parse", "--verify", "--quiet", ref):
            return f"Branch {branch} existiert schon ({ref}) — erst abschließen; Pflege einmal pro Tag."
    return None


def _maintain_contract(root: Path) -> dict:
    branch = maintenance_branch()
    return {
        "title": "Standard Task: Pflege",
        "goal": ("Maintain the repository's Kit control layer with the Kit's own maintenance routes: "
                 f"dry runs on main first; only if a route proposes a change, branch {branch} with the "
                 "changes left for Abschließen."),
        "repository_root": str(root),
        "completion_contract": _verifier("maintained", branch=branch),
        "acceptance_criteria": [
            "Nothing to maintain: main unchanged, clean, equal to origin/main.",
            f"Otherwise: {branch} contains origin/main and carries the maintenance changes.",
        ],
        "constraints": ["No pull request (Abschließen publishes).",
                        "The documentation lifecycle sweep is reported, never executed.",
                        "No managed-CI template update (KIT-GF-042); no Kit installation change."],
    }


def _maintain_prompt(root: Path) -> str:
    branch = maintenance_branch()
    return f"""STANDARD TASK — PFLEGE (maintenance of the Kit control layer)

Repository: {root}
Maintenance branch, only if needed: {branch}

1. On main, read-only: run the Kit's maintenance orchestrators as dry runs — the workspace schema
   upgrade, the transient-artifact garbage collection in each of its collection modes (one mode
   per invocation) and the documentation lifecycle sweep.
2. If neither the schema upgrade nor the garbage collection proposes a change: stop with DONE,
   stay on main and change nothing.
3. Otherwise start {branch} from the current origin/main through the Kit's work-start route and
   run exactly the proposing routes in execute mode there. Leave the resulting changes on the
   branch; do not publish it and open no pull request — the human finishes it with Abschließen.
4. The DONE file has only the keys "state", "reason" and "step" (AGP_K07_TERMINAL_REPLY_FILE_V1).
   Its "reason" states the outcome ("nothing to maintain" or the changed paths) and the
   documentation lifecycle sweep: the number of findings and their finding codes.
   Never execute the sweep: its actions are the
   owner's decisions (the Cockpit asks for any execute of it). Never run the managed-CI template
   update in execute mode (KIT-GF-042) and do not change the Kit installation or its version pins.

The human approved by starting this task only the synchronization with origin and the creation of
the maintenance branch through the Kit's work-start route. Any other remote effect still needs a
decision.
{_COMMON}
Completion is verified locally: DONE is accepted only when either main is unchanged, clean and
equal to origin/main, or {branch} is checked out, contains origin/main and carries changes.
"""


STANDARD_TASKS: tuple[StandardTask, ...] = (
    StandardTask(
        key="chat-switch",
        label="Chat wechseln",
        description="Erzeugt und validiert den vollständigen Nachfolge-Handoff.",
        contract_factory=_chat_switch_contract,
        prompt_factory=_chat_switch_prompt,
    ),
    StandardTask(
        key="finish",
        label="Abschließen",
        description="Veröffentlicht den Arbeitsbranch: Pull Request, grüne CI, Merge, Post-Merge, main synchron.",
        contract_factory=_finish_contract,
        prompt_factory=_finish_prompt,
        effect="github",
        precheck=_finish_precheck,
        approved_scope=_finish_scope(),
        ci_gate_merge=True,
        confirm=("„Abschließen“ veröffentlicht den aktuellen Arbeitsbranch und mergt ihn nach main:\n"
                 "Push · Pull Request · grüne CI · Merge · Post-Merge-Abschluss des Kits.\n\n"
                 "Der Start ist deine Freigabe für genau diese Wirkungen (von main nur, um einen "
                 "offenen Post-Merge-Abschluss des Kits zu Ende zu bringen; kein Force-Push, Merge "
                 "nur bei grüner CI). Jede andere Wirkung fragt weiterhin.\n\n"
                 "Jetzt abschließen?"),
        offers_recover_on_interrupt=True,
        # AGP_NO_CHAT_SWITCH_FOLLOW_UP_V1 (owner 2026-10-02): no follow-up; „Chat
        # wechseln“ only writes the handoff package and opens no new chat, so after
        # Abschließen the recommendation follows the repository state.
    ),
    StandardTask(
        key="work-start",
        label="Arbeit beginnen",
        description="Synchronisiert main und legt einen neuen Arbeitsbranch an.",
        contract_factory=_work_start_contract,
        prompt_factory=_work_start_prompt,
        effect="github",
        inputs=("kind", "name"),
        precheck=_work_start_precheck,
        approved_scope=WORK_START_SCOPE,
    ),
    StandardTask(
        key="release",
        label="Release",
        description=("Release über das Kit: Release-Branch, Merge, Tag und GitHub-Release-Eintrag; mit "
                     "release.approval: upfront in einem Lauf (agentic-kit release run), sonst fragt der "
                     "Tag-Push noch einmal."),
        contract_factory=_release_contract,
        prompt_factory=_release_prompt,
        effect="github",
        inputs=("version",),
        precheck=_release_precheck,
        approved_scope=_release_scope(),
        scope_factory=_release_scope_for,
        ci_gate_merge=True,
        # AGP_RELEASE_RUN_AUTONOMY_V1: with release.approval: upfront the click is the whole consent.
        confirm=("„Release“ erstellt ein Release über das Kit:\n"
                 "Release-Branch · Release-Vorbereitung des Kits · Pull Request · grüne CI · Merge · "
                 "annotierter Tag · GitHub-Release-Eintrag. Kein PyPI, kein Zenodo.\n\n"
                 "Deklariert das Repo release.approval: upfront (agp-Cockpit seit 2026-10-13), ist dieser "
                 "Klick deine Zustimmung zu genau diesem Release: Das Kit hält sie fest und stoppt bei "
                 "jedem Fehler oder jeder Abweichung von Version, Tag oder Ziel-Commit. Ohne diese "
                 "Deklaration fragt der Tag-Push noch einmal mit Version, Tag, Ziel-Commit und Signatur.\n\n"
                 "Ein angehaltener Kit-Lauf setzt beim nächsten Start dort fort, wo er stand; ohne "
                 "Deklaration entfällt der Release-Branch, wenn main die Version schon nennt (nur noch Tag).\n\n"
                 "Jetzt starten?"),
        offers_recover_on_interrupt=True,
    ),
    StandardTask(
        key="maintain",
        label="Pflege",
        description="Pflegt die Kit-Steuerschicht mit den Kit-Routen; Änderungen gehen über „Abschließen“ ins Repo.",
        contract_factory=_maintain_contract,
        prompt_factory=_maintain_prompt,
        effect="local",
        precheck=_maintain_precheck,
        approved_scope=WORK_START_SCOPE,
        confirm=("„Pflege“ prüft die Kit-Steuerschicht mit den Pflege-Routen des Kits "
                 "(Schema-Upgrade, Aufräumen von Übertragungsresten, Dokument-Aktualität) — erst als Probelauf.\n\n"
                 "Gibt es nichts zu tun, bleibt alles, wie es ist. Sonst legt sie einen Branch "
                 "chore/pflege-<Datum> an und lässt die Änderungen dort; veröffentlicht wird erst mit "
                 "„Abschließen“.\n\nDer Start gibt nur die Synchronisierung mit origin und den Branch frei. "
                 "Dokument-Hinweise werden nur berichtet; die CI-Vorlage und die Kit-Version bleiben unberührt.\n\n"
                 "Jetzt starten?"),
    ),
    StandardTask(
        key="recover",
        label="Wiederherstellen",
        description="Diagnostiziert und stellt einen sauberen Zustand her; Eingriffe nur nach Freigabe.",
        contract_factory=_recover_contract,
        prompt_factory=_recover_prompt,
    ),
)
BY_KEY = {task.key: task for task in STANDARD_TASKS}


def standard_tasks() -> tuple[StandardTask, ...]:
    return STANDARD_TASKS
