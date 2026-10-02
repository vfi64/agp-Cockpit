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

    def contract(self, repository_root: Path, inputs: dict | None = None) -> dict:
        root = repository_root.expanduser().resolve()
        return self.contract_factory(root, dict(inputs or {})) if self.inputs \
            else self.contract_factory(root)

    def prompt(self, repository_root: Path, inputs: dict | None = None) -> str:
        root = repository_root.expanduser().resolve()
        return self.prompt_factory(root, dict(inputs or {})) if self.inputs \
            else self.prompt_factory(root)

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
        return "Abschließen läuft nie von main aus (R4). Erst „Arbeit beginnen“."
    dirty = bool(_git_value(root, "status", "--porcelain"))
    found = relation(root, branch, "origin/main")
    if found == CHANGES or (dirty and found in (NO_COMMITS, None)):
        return None
    if found is None:
        return f"Branch {branch} ist mit origin/main nicht vergleichbar — erst Lagebericht/Wiederherstellen."
    return (f"Branch {branch} enthält nichts, was nicht schon in origin/main ist "
            "(bereits gemergt oder ohne eigene Änderungen) — nichts abzuschließen.")


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
        "constraints": ["Never from main.", "No force push.", "Merge only through the Kit's green-CI gates."],
    }


def _finish_prompt(root: Path) -> str:
    branch = _git_value(root, "branch", "--show-current")
    return f"""STANDARD TASK — ABSCHLIESSEN (finish the work branch)

Repository: {root}
Work branch: {branch}

Goal: publish the work branch, open its pull request, wait for green CI, merge it through the
Kit's gates and complete the Kit's post-merge lifecycle, so that local main equals origin/main.

The human approved exactly these effects by starting this standard task (publishing, pull
request, merge, post-merge closeout, main synchronization): do not ask NEEDS_HUMAN for them.
Any other remote effect still needs a decision. Never force-push; never merge red CI.
{_COMMON}
Completion is verified locally: DONE is accepted only after the Cockpit checked that the pull
request is merged with green CI, the post-merge check passes and main is green. Name the pull
request as "pr" in the DONE file. Run the lifecycle once; do not open another pull request for a
branch the facts report as already merged.
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
        "acceptance_criteria": ["The Cockpit's Lagebericht reports BEREIT or IN_ARBEIT."],
        "constraints": [
            "Diagnose first.",
            "Destructive steps (reset, deleting branches or files) only after NEEDS_HUMAN and approval.",
        ],
    }


def _recover_prompt(root: Path) -> str:
    return f"""STANDARD TASK — WIEDERHERSTELLEN (recover)

Repository: {root}

Goal: find out why the repository is not in a clean state (drift from origin/main, unexpected
changes, an interrupted publish/merge/post-merge lifecycle, a failing post-merge check) and
restore a clean, synchronized state: either a clean work branch that can be finished, or main
equal to origin/main with a passing post-merge check.

Start with the Kit's read-only recovery diagnosis. Destructive steps — discarding changes,
resetting branches, deleting branches or files — require NEEDS_HUMAN with a precise question
first. Remote effects ask as usual. If an interrupted lifecycle only needs to be completed
(for example an open, green pull request), say so in NEEDS_HUMAN instead of starting it.
{_COMMON}
Completion is verified locally: DONE is accepted only when the Cockpit's own Lagebericht reports
BEREIT or IN_ARBEIT.
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
                 "Der Start ist deine Freigabe für genau diese Wirkungen (nie von main, kein "
                 "Force-Push, Merge nur bei grüner CI). Jede andere Wirkung fragt weiterhin.\n\n"
                 "Jetzt abschließen?"),
        offers_recover_on_interrupt=True,
        follow_up="Chat wechseln",
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
