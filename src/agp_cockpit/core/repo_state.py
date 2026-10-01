"""Repository state model and Lagebericht (plan P2).

AGP_REPO_STATE_V1: the Cockpit observes the active repository locally and
read-only (E0, started by the human, SCOPE_BOUNDARY §3) and derives one of
six states. The state decides which standard tasks are offered and which one
is recommended; the recommendation is a hint for the human, never a Kit
workflow chosen on behalf of the remote LLM (SCOPE_BOUNDARY §4).

Facts: git branch and HEAD, origin/main (``git ls-remote``), unexpected
working-tree changes (Kit-owned volatile paths excluded), the installed Kit
(``kit_installation``), the Kit workspace, ``gh auth status`` and, on main,
``agentic-kit transfer post-merge-check``. ``observe`` gathers them,
``classify`` is pure and fully tested. Without an installed Kit the state is
UNKLAR and tasks are blocked (no silent fallback to a repository copy).
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from agp_cockpit.core.ci_gate import gh_binary, tool_env

KEIN_KIT = "KEIN_KIT"
BEREIT = "BEREIT"
IN_ARBEIT = "IN_ARBEIT"
LAEUFT = "LÄUFT"
STOERUNG = "STÖRUNG"
UNKLAR = "UNKLAR"

# Verbs (plan "Standard tasks as lifecycle verbs").
LAGEBERICHT = "lagebericht"
ARBEIT_BEGINNEN = "arbeit_beginnen"
ARBEITEN = "arbeiten"
ABSCHLIESSEN = "abschliessen"
WIEDERHERSTELLEN = "wiederherstellen"
CHAT_WECHSELN = "chat_wechseln"
REPO_UEBERNEHMEN = "repo_uebernehmen"
RELEASE = "release"
PFLEGE = "pflege"

OFFERED = {
    KEIN_KIT: (LAGEBERICHT, REPO_UEBERNEHMEN),
    BEREIT: (LAGEBERICHT, ARBEIT_BEGINNEN, CHAT_WECHSELN, RELEASE, PFLEGE),
    IN_ARBEIT: (LAGEBERICHT, ARBEITEN, ABSCHLIESSEN, CHAT_WECHSELN),
    LAEUFT: (),
    STOERUNG: (LAGEBERICHT, WIEDERHERSTELLEN, CHAT_WECHSELN),
    UNKLAR: (LAGEBERICHT,),
}

# Paths the Kit itself rewrites; they are not the human's or the LLM's work.
KIT_VOLATILE_PREFIXES = (
    ".agentic/rule_ack/", ".agentic/transfer/", ".agentic/tmp/",
    ".agentic/state/handoff/transfer_handoff_reports/", ".agentic/state/handoff/transfer_runs/",
    "Download/", ".local/",
)
WORKSPACE_MARKERS = (".agentic/config.yaml", ".agentic/project.yaml")


@dataclass(frozen=True)
class RepoFacts:
    root: str
    is_git: bool = False
    branch: str = ""
    head: str = ""
    origin_main: str | None = None          # None: origin unreadable
    tracking_main: str = ""                 # last fetched refs/remotes/origin/main
    own_commits: int | None = None          # commits on HEAD not in origin/main
    changes: tuple[str, ...] = ()           # unexpected working-tree changes
    volatile_changes: tuple[str, ...] = ()
    kit_version: str | None = None          # None: no installed Kit
    workspace: bool = False
    gh_ok: bool | None = None               # None: gh not found
    post_merge: str | None = None           # PASS / NOT_PASS / None (not checked)
    post_merge_detail: str = ""
    task_running: bool = False


@dataclass(frozen=True)
class RepoState:
    state: str
    summary: str
    recommended: str | None
    offered: tuple[str, ...]
    reasons: tuple[str, ...] = ()
    facts: RepoFacts = field(default_factory=lambda: RepoFacts(root=""))

    def as_json(self) -> dict:
        data = asdict(self)
        data["facts"] = asdict(self.facts)
        return data


def _run(argv, root: Path, runner, timeout: int = 60):
    try:
        return runner(argv, cwd=str(root), env=tool_env(root), text=True, capture_output=True,
                      timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(argv, 127, "", f"{type(exc).__name__}: {exc}")


def _git(root: Path, runner, *args: str, raw: bool = False) -> str | None:
    completed = _run(["git", *args], root, runner)
    if completed.returncode != 0:
        return None
    # raw: porcelain lines start with a status column that may be a space
    # (" M path"); stripping it shifted the first path by one character.
    return completed.stdout if raw else completed.stdout.strip()


def observe(root: Path, *, runner=subprocess.run, task_running: bool = False,
            kit=None, network: bool = True) -> RepoFacts:
    """Read-only facts about the repository (E0)."""
    root = Path(root)
    if kit is None:
        from agp_cockpit.core.kit_installation import discover
        kit = discover(root)
    kit_version = (kit.version or "?") if kit is not None else None
    workspace = any((root / marker).is_file() for marker in WORKSPACE_MARKERS)
    if _git(root, runner, "rev-parse", "--is-inside-work-tree") != "true":
        return RepoFacts(root=str(root), kit_version=kit_version, workspace=workspace,
                         task_running=task_running)
    branch = _git(root, runner, "branch", "--show-current") or ""
    head = _git(root, runner, "rev-parse", "HEAD") or ""
    tracking = _git(root, runner, "rev-parse", "--verify", "-q", "refs/remotes/origin/main") or ""
    own = None
    if tracking:
        count = _git(root, runner, "rev-list", "--count", f"{tracking}..HEAD")
        own = int(count) if count and count.isdigit() else None
    changes, volatile = [], []
    status = _git(root, runner, "status", "--porcelain=v1", "--untracked-files=all", raw=True) or ""
    for line in status.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].split(" -> ")[-1].strip().strip('"')
        (volatile if path.startswith(KIT_VOLATILE_PREFIXES) else changes).append(path)
    origin_main = None
    if network:
        remote = _git(root, runner, "ls-remote", "origin", "refs/heads/main")
        if remote is not None:
            origin_main = remote.split()[0] if remote.split() else ""
    gh_ok = None
    gh = gh_binary(root)
    if gh:
        gh_ok = _run([gh, "auth", "status"], root, runner).returncode == 0
    post_merge, detail = None, ""
    if kit is not None and branch == "main" and workspace:
        check = _run([str(kit.binary), "transfer", "post-merge-check", "--main-branch", "main",
                      "--json"], root, runner, timeout=120)
        output = f"{check.stdout or ''}\n{check.stderr or ''}"
        post_merge = "PASS" if check.returncode == 0 and "NEEDS_" not in output and "BLOCKED" not in output \
            else "NOT_PASS"
        detail = output.strip()[-600:]
    return RepoFacts(root=str(root), is_git=True, branch=branch, head=head, origin_main=origin_main,
                     tracking_main=tracking, own_commits=own, changes=tuple(changes),
                     volatile_changes=tuple(volatile), kit_version=kit_version, workspace=workspace,
                     gh_ok=gh_ok, post_merge=post_merge, post_merge_detail=detail,
                     task_running=task_running)


def _state(name: str, summary: str, recommended: str | None, reasons, facts: RepoFacts) -> RepoState:
    return RepoState(name, summary, recommended, OFFERED[name], tuple(reasons), facts)


def classify(facts: RepoFacts) -> RepoState:
    """Pure decision: facts -> one of the six states and the recommendation."""
    if facts.task_running:
        return _state(LAEUFT, "Ein Task läuft. Neue Tasks erst nach seinem Ende.", None, (), facts)
    if not facts.is_git:
        return _state(UNKLAR, "Kein git-Repository.", LAGEBERICHT,
                      ("Der Ordner ist kein git-Repository.",), facts)
    if facts.kit_version is None:
        return _state(UNKLAR, "Agentic Project Kit ist nicht installiert.", LAGEBERICHT,
                      (("Weder <repo>/.venv/bin/agentic-kit noch agentic-kit im Pfad gefunden. "
                        "Kit installieren, dann Lagebericht aktualisieren."),), facts)
    if not facts.workspace:
        return _state(KEIN_KIT, "Das Repo steht noch nicht unter Kit-Kontrolle.", REPO_UEBERNEHMEN,
                      ("Keine Kit-Steuerschicht (.agentic/config.yaml) gefunden.",), facts)
    unclear = []
    if facts.origin_main is None:
        unclear.append("origin/main ist nicht lesbar (Netz oder Zugangsdaten).")
    elif facts.origin_main == "":
        unclear.append("origin hat keinen Branch main.")
    if facts.gh_ok is False:
        unclear.append("gh ist nicht angemeldet (gh auth login).")
    if unclear:
        return _state(UNKLAR, "Der Zustand ist nicht vollständig lesbar.", LAGEBERICHT, unclear, facts)
    if not facts.branch:
        return _state(STOERUNG, "Kein Branch ausgecheckt (detached HEAD).", WIEDERHERSTELLEN,
                      ("HEAD zeigt auf keinen Branch.",), facts)
    if facts.branch == "main":
        problems = []
        if facts.head != facts.origin_main:
            problems.append(f"main {facts.head[:8]} ist nicht synchron mit origin/main "
                            f"{(facts.origin_main or '')[:8]}.")
        if facts.changes:
            problems.append("Unerwartete Änderungen auf main: " + ", ".join(facts.changes[:5]))
        if facts.post_merge == "NOT_PASS":
            problems.append("Kit post-merge-check ist nicht PASS.")
        if problems:
            return _state(STOERUNG, "main ist nicht im sauberen Ausgangszustand.", WIEDERHERSTELLEN,
                          problems, facts)
        return _state(BEREIT, "main ist synchron und sauber; bereit für neue Arbeit.", ARBEIT_BEGINNEN,
                      (), facts)
    if facts.own_commits == 0 and facts.changes and facts.head == facts.origin_main:
        return _state(STOERUNG, f"Branch {facts.branch} enthält keine eigene Arbeit, aber offene "
                      "Änderungen (vermutlich Rest eines Abschlusses).", WIEDERHERSTELLEN,
                      ("Offene Änderungen: " + ", ".join(facts.changes[:5]),), facts)
    if facts.own_commits and not facts.changes:
        recommended = ABSCHLIESSEN
        summary = f"Arbeit auf {facts.branch}: {facts.own_commits} Commit(s), sauber; bereit zum Abschließen."
    else:
        recommended = ARBEITEN
        summary = f"Arbeit auf {facts.branch} läuft."
    return _state(IN_ARBEIT, summary, recommended, (), facts)


LABELS = {
    LAGEBERICHT: "Lagebericht", ARBEIT_BEGINNEN: "Arbeit beginnen", ARBEITEN: "Arbeiten",
    ABSCHLIESSEN: "Abschließen", WIEDERHERSTELLEN: "Wiederherstellen", CHAT_WECHSELN: "Chat wechseln",
    REPO_UEBERNEHMEN: "Repo übernehmen", RELEASE: "Release", PFLEGE: "Pflege",
}


def describe(state: RepoState) -> str:
    """Operator-facing Lagebericht (German)."""
    f = state.facts
    lines = [f"Zustand: {state.state} — {state.summary}"]
    if state.recommended:
        lines.append(f"Empfohlen: {LABELS[state.recommended]}")
    lines += [f"• {reason}" for reason in state.reasons]
    if f.is_git:
        sync = ("synchron" if f.branch == "main" and f.head == f.origin_main else
                f"origin/main {(f.origin_main or 'unbekannt')[:8]}")
        lines.append(f"Branch {f.branch or '(detached)'} @ {f.head[:8]} · {sync}"
                     + (f" · {f.own_commits} eigene Commit(s)" if f.own_commits else ""))
        lines.append(f"Änderungen: {len(f.changes)} offen" + (f", {len(f.volatile_changes)} Kit-intern"
                                                              if f.volatile_changes else ""))
    lines.append(f"Kit: {f.kit_version or 'nicht installiert'} · Kit-Steuerschicht: "
                 f"{'ja' if f.workspace else 'nein'} · gh: "
                 f"{'angemeldet' if f.gh_ok else 'nicht angemeldet' if f.gh_ok is False else 'nicht gefunden'}"
                 + (f" · post-merge-check: {f.post_merge}" if f.post_merge else ""))
    return "\n".join(lines)


def write_report(root: Path, state: RepoState) -> Path:
    target = Path(root) / ".local" / "agp-cockpit" / "state" / "repo-state.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(state.as_json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def lagebericht(root: Path, *, task_running: bool = False, runner=subprocess.run) -> RepoState:
    """Observe, classify and record (``.local/agp-cockpit/state/repo-state.json``)."""
    state = classify(observe(root, runner=runner, task_running=task_running))
    write_report(root, state)
    return state
