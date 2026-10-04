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
        "constraints": ["Never from main, except to complete an open Kit post-merge lifecycle "
                        "(AGP_FINISH_OPEN_FOLLOWUP_V1).", "No force push.",
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
{_COMMON}
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
        "acceptance_criteria": ["The Cockpit's Lagebericht reports BEREIT or IN_ARBEIT."],
        "constraints": [
            "Diagnose first.",
            "Destructive steps only through Kit routes, dry run first, the signed execute only after "
            "NEEDS_HUMAN and approval (AGP_DESTRUCTIVE_EXECUTE_GATE_V1).",
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
Completion is verified locally: DONE is accepted only when the Cockpit's own Lagebericht reports
BEREIT or IN_ARBEIT.
"""


# --- P11 Release -----------------------------------------------------------------

_VERSION = __import__("re").compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def _release_scope() -> frozenset[str]:
    """AGP_RELEASE_APPROVAL_SCOPE_V1: the start click approves the release branch and
    its pull-request lifecycle; the live tag publication is not in the scope and
    always asks (with the signature of its dry run)."""
    return frozenset(_finish_scope() | WORK_START_SCOPE)


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


def _release_precheck(root: Path, inputs: dict) -> str | None:
    version = str(inputs.get("version") or "").strip()
    wanted = _version_tuple(version)
    if wanted is None:
        return "Version im Format X.Y.Z angeben (z. B. 0.1.1)."
    if _publication(root) != "none":
        return ("Der Release-Button macht nur private Releases: .agentic/config.yaml muss "
                "publication: none deklarieren.")
    if _git_value(root, "branch", "--show-current") != "main":
        return "Release startet nur auf main (Zustand BEREIT)."
    if _git_value(root, "status", "--porcelain"):
        return "main hat ungesicherte Änderungen — erst abschließen oder wiederherstellen."
    head = _git_value(root, "rev-parse", "HEAD")
    if not head or head != _git_value(root, "rev-parse", "--verify", "-q", "refs/remotes/origin/main"):
        return "main ist nicht synchron mit origin/main — erst Lagebericht/Wiederherstellen."
    if _git_value(root, "rev-parse", "--verify", "--quiet", f"refs/tags/v{version}"):
        return f"Tag v{version} existiert schon — andere Version wählen."
    current = _version_tuple(_current_version(root))
    if current is not None and wanted < current:
        return f"Version {version} ist kleiner als die aktuelle {_current_version(root)}."
    if _current_version(root) == version:
        # AGP_RELEASE_RESUME_PHASE2_V1 (live 2026-10-04, release 0.1.1): phase 1 is merged and only
        # the tag is missing. The squash-merged release branch may still exist (origin/release/<v>
        # stayed after #204); it is not reused, the task skips to the tag.
        return None
    branch = f"release/{version}"
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


def _release_contract(root: Path, inputs: dict) -> dict:
    version = str(inputs.get("version") or "").strip()
    return {
        "title": f"Standard Task: Release {version}",
        "goal": (f"Private release {version}: release branch with the Kit's release preparation, "
                 "merged with green CI, then the annotated tag pushed through the Kit's signed private "
                 "release route after the owner's approval."),
        "repository_root": str(root),
        "completion_contract": _verifier("released", version=version),
        "acceptance_criteria": [
            f"Release pull request for {version} merged with green CI; main green.",
            f"Annotated tag v{version} on origin; its commit is in origin/main; pyproject names {version}.",
        ],
        "constraints": ["publication: none — no GitHub Release, PyPI or Zenodo.",
                        "The live tag publication only with the owner's approval of its signed plan.",
                        "No force push; no marker file."],
    }


# AGP_RELEASE_CHANGELOG_SUMMARY_V1 (live 2026-10-04, release 0.1.1): the changelog entry was a
# one-line stub and the Unreleased section stayed; step 2 names the summary source.
def _release_prompt(root: Path, inputs: dict) -> str:
    version = str(inputs.get("version") or "").strip()
    prepared = _current_version(root) == version
    phase_one = (f"""Phase 1 is already done: main names version {version} (prepared and merged earlier) and
the tag is missing. Skip to phase 2.""" if prepared else f"""Phase 1 — release branch:
1. Start the work branch release/{version} from the current origin/main through the Kit's
   work-start route.
2. Run the Kit's release preparation for version {version} in write mode (it updates the version
   anchors declared in .agentic/config.yaml and the changelog). Its changelog summary lines name
   the user-visible changes since the previous release tag: the entries of the CHANGELOG.md
   "Unreleased" section, completed from the merged pull requests since that tag — never a
   one-line stub such as "Prepare release". Then empty the Unreleased section in the same branch.
3. If the repository has docs/planning/RELEASE_POLICY.md, perform the release-branch steps it names
   in the same branch (agp-Cockpit: set the build identity in src/agp_cockpit/version.py and
   chrome_extension/build_identity.js to release-{version}); the repository's tests check them.
4. Finish the branch through the Kit's pull-request lifecycle: green CI, merge, post-merge closeout,
   local main equal to origin/main.""")
    return f"""STANDARD TASK — RELEASE {version} (private release)

Repository: {root}
Version: {version} · tag v{version} · publication: none (no GitHub Release, PyPI or Zenodo)

{phase_one}

Phase 2 — tag publication (always asks):
5. On main, run the Kit's private release publication as a dry run. Then stop with NEEDS_HUMAN and
   state the version, the tag, the target commit, the planned actions and the approval signature
   of the dry run, so the owner can approve exactly that plan.
6. After the approval, run the live publication with that signature (the Kit's execute options
   with the expected signature); it creates and pushes only the annotated tag. Never create the
   marker file .agentic/release/ENABLE_LIVE_PUBLISH. If HEAD changed since the dry run, start again
   at step 5.

The human approved by starting this task the release branch and its pull-request lifecycle
(starting the branch, publishing, pull request, merge, post-merge closeout, main synchronization): do not
ask NEEDS_HUMAN for them. The live tag publication is not approved yet and always asks.
Never force-push; never merge red CI.
{_COMMON}
Completion is verified locally: DONE is accepted only after the Cockpit checked that the release
pull request is merged with green CI, main is green, the annotated tag v{version} is on origin, its
commit is in origin/main and pyproject.toml at the tag names {version}. Name the release pull
request as "pr" in the DONE file.
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
        description="Privates Release: Release-Branch über das Kit, Merge, dann der signierte Tag-Push nach Freigabe.",
        contract_factory=_release_contract,
        prompt_factory=_release_prompt,
        effect="github",
        inputs=("version",),
        precheck=_release_precheck,
        approved_scope=_release_scope(),
        ci_gate_merge=True,
        confirm=("„Release“ erstellt ein privates Release:\n"
                 "Release-Branch · Release-Vorbereitung des Kits · Pull Request · grüne CI · Merge · "
                 "Post-Merge-Abschluss.\n\n"
                 "Der Start gibt genau diese Wirkungen frei. Der Push des Tags fragt danach noch "
                 "einmal: Du siehst Version, Tag, Ziel-Commit und die Signatur des Probelaufs und "
                 "gibst genau diesen Plan frei. Kein GitHub Release, kein PyPI, kein Zenodo.\n\n"
                 "Nennt main die Version schon (Release-Branch gemergt, Tag fehlt), entfällt der "
                 "Release-Branch: Es folgt nur der Tag.\n\n"
                 "Jetzt starten?"),
        offers_recover_on_interrupt=True,
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
