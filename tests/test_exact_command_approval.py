"""AGP_EXACT_COMMAND_APPROVAL_V1, AGP_MENTIONED_BRANCH_FACTS_V1, AGP_TRANSFER_BRANCH_LAGE_V1.

Live FILE_TRANSFER runs 2026-10-19/20: a `transfer remote-next <branch>` fitted neither „Push und
PR“ (push-current and pr-create only, so the approvals looped) nor should it need „Push, PR und
Merge“, whose limit to one command was only prose in the note; the facts listed no transfer
branch, so the remote side took an existing one for missing; and the Lage recommended
„Abschließen“ on the transfer branch, which would open a pull request with test orders.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agp_cockpit.core import guidance
from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.human_decision import (
    HumanDecisionStore,
    decision_mission_text,
    exact_approval_view,
    exact_commands_in,
)
from agp_cockpit.core.kit_command_catalog import KitCommandCatalog, approval_required_invocations
from agp_cockpit.core.merged_branch_guard import mentioned_branches, repository_facts
from test_human_decision import _bridge, mission, work_order

ROOT = Path(__file__).resolve().parents[1]
CATALOG = KitCommandCatalog.load(ROOT)
LIVE_QUESTION = (
    "Die angeforderte Gegenprobe agentic-kit transfer remote-next transfer/file-transfer-deny-20261020 "
    "--json ist im installierten Kit 1.1.2 (Manifest 390ff4b84aa2) als remote_effect=true klassifiziert. "
    "Erforderlich ist eine ausdrücklich auf diesen einen remote-next-Befehl begrenzte Freigabe."
)


# --- reading the command lines of a question -------------------------------------------------

@pytest.mark.parametrize("question,expected", [
    (LIVE_QUESTION, ["agentic-kit transfer remote-next transfer/file-transfer-deny-20261020 --json"]),
    ("Befehl: agentic-kit transfer push-current\nEs liegt keine Freigabe vor.",
     ["agentic-kit transfer push-current"]),
    ("Freigabe für `agentic-kit transfer remote-next transfer/x --json` und agentic-kit transfer push-current.",
     ["agentic-kit transfer remote-next transfer/x --json", "agentic-kit transfer push-current"]),
    ("agentic-kit transfer pr-create --base main --head feat/x danach",
     ["agentic-kit transfer pr-create --base main --head feat/x"]),
    ("agentic-kit transfer remote-next b-1 --allow-unlisted --json wurde abgelehnt",
     ["agentic-kit transfer remote-next b-1 --allow-unlisted --json"]),
    ("agentic-kit transfer remote-next --json ist der Befehl", ["agentic-kit transfer remote-next --json"]),
    ("agentic-kit frobnicate --x und agentic-kit transfer remote-next --frob", []),
    ('agentic-kit transfer pr-create --head feat/x --title "Titel"', []),   # value in quotes: not offered
    ("Keine Befehle hier.", []),
])
def test_the_question_yields_exactly_its_command_lines(question, expected):
    assert exact_commands_in(question, CATALOG) == expected


def test_the_view_offers_exact_and_flags_allow_unlisted():
    view = exact_approval_view("agentic-kit transfer remote-next b-1 --allow-unlisted --json", CATALOG)
    assert view["default_scope"] == "exact" and view["allow_unlisted"] == view["commands"]
    assert exact_approval_view("Bitte entscheiden.", CATALOG)["default_scope"] == "push_pr"


# --- the grant ----------------------------------------------------------------------------------

LINE = "agentic-kit transfer remote-next transfer/a-1 --json"


def _grant(tmp_path, exact, **kwargs):
    store = HumanDecisionStore(tmp_path)
    store.record(mission_id="m", task_id="T", decision="APPROVE", question="q", exact=exact, **kwargs)
    return store


def test_an_exact_grant_permits_only_its_lines(tmp_path):
    store = _grant(tmp_path, [LINE])
    wanted = ["agentic-kit transfer remote-next"]
    assert store.permits("T", wanted, ci_gate_active=False, invocations=[LINE])
    for other in (["agentic-kit transfer remote-next transfer/a-2 --json"],
                  [LINE.replace(" --json", " --allow-unlisted --json")],
                  [LINE, "agentic-kit transfer push-current"],
                  ["agentic-kit transfer remote-next <expr> --json"]):
        assert not store.permits("T", wanted, ci_gate_active=False, invocations=other), other
    assert not store.permits("T", wanted, ci_gate_active=False, invocations=None)
    assert not store.permits("T", wanted, ci_gate_active=False, invocations=[])


def test_allow_unlisted_needs_its_own_confirmation_and_empty_is_refused(tmp_path):
    flagged = LINE.replace(" --json", " --allow-unlisted --json")
    with pytest.raises(ValueError, match="--allow-unlisted"):
        _grant(tmp_path, [flagged])
    with pytest.raises(ValueError, match="at least one"):
        _grant(tmp_path, [])
    store = _grant(tmp_path, [flagged], confirm_allow_unlisted=True)
    assert store.current()["grant"]["exact"] == [flagged]


def test_computed_arguments_never_match_a_literal_line():
    source = ("import subprocess\nB = 'transfer/a-1'\n"
              "subprocess.run(['agentic-kit', 'transfer', 'remote-next', B, '--json'])\n")
    lines = approval_required_invocations(source, CATALOG)
    assert lines == ["agentic-kit transfer remote-next <expr> --json"]
    literal = "import subprocess\nsubprocess.run(['agentic-kit', 'transfer', 'remote-next', 'transfer/a-1', '--json'])\n"
    assert approval_required_invocations(literal, CATALOG) == [LINE]


def test_the_continuation_text_names_the_lines_and_forbids_additions():
    text = decision_mission_text(goal_text="g", decision="APPROVE", question=LIVE_QUESTION, note="",
                                 scope="exact", exact=[LINE])
    assert "APPROVED FOR EXACTLY THESE COMMAND LINES" in text and f"  {LINE}\n" in text
    assert "--allow-unlisted" in text and "refused locally" in text


# --- end to end through the bridge --------------------------------------------------------------

@pytest.fixture
def bridge(tmp_path):
    yield from _bridge(tmp_path)


def test_the_bridge_question_lists_the_line_and_an_exact_approval_runs_only_it(bridge):
    root, runtime, call = bridge
    first = mission(call, runtime)
    asked = call("/v1/file-loop/command", {"filename": "1480_push.py",
                                           "content": work_order(["transfer", "push-current"])})
    assert asked["state"] == "NEEDS_HUMAN"
    assert "Befehl: agentic-kit transfer push-current" in asked["human_reason"]
    record = call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE", "scope": "exact"})
    assert record["grant"]["exact"] == ["agentic-kit transfer push-current"]

    mission(call, runtime)
    changed = call("/v1/file-loop/command", {"filename": "1481_push.py",
                                             "content": work_order(["transfer", "push-current", "--again"])})
    assert changed["state"] == "NEEDS_HUMAN" and changed["terminal"] is True
    assert not (root / "Download" / "1481_push.py").exists()


def test_an_exact_approval_of_the_same_line_executes(bridge):
    root, runtime, call = bridge
    first = mission(call, runtime)
    call("/v1/file-loop/command", {"filename": "1480_push.py", "content": work_order(["transfer", "push-current"])})
    call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE", "scope": "exact"})
    mission(call, runtime)
    accepted = call("/v1/file-loop/command", {"filename": "1480_push.py",
                                              "content": work_order(["transfer", "push-current"])})
    assert accepted["replayed"] is False and accepted.get("terminal") is not True


# --- facts for named branches -------------------------------------------------------------------

def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def test_named_branches_get_facts_and_an_unfetched_one_is_not_called_missing(tmp_path):
    origin = tmp_path / "origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "T")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "commit", "--allow-empty", "-m", "init")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-u", "origin", "main")
    _git(repo, "switch", "-c", "transfer/known-1")
    _git(repo, "commit", "--allow-empty", "-m", "order")
    _git(repo, "push", "-u", "origin", "transfer/known-1")
    _git(repo, "switch", "main")
    goal = ("Der Branch transfer/known-1 existiert. Danach transfer/unfetched-2. "
            "Datei docs/validation/evidence/x.json, Ziel origin/main.")
    assert mentioned_branches(repo, goal) == ["transfer/known-1", "transfer/unfetched-2"]
    line = repository_facts(repo, None, mentioned_text=goal)
    assert "origin/transfer/known-1" in line and "equals local transfer/known-1" in line
    assert "transfer/unfetched-2: not known locally" in line and "do not create it" in line
    assert "docs/validation" not in line


# --- the Lage on a transfer branch --------------------------------------------------------------

def _facts(branch):
    return rs.RepoFacts(root="", is_git=True, branch=branch, head="b", origin_main="a", own_commits=2,
                        kit_version="1.1.2", workspace=True, gh_ok=True, branch_published=True)


def test_a_transfer_branch_recommends_no_finish_and_explains_the_way_back():
    state = rs.classify(_facts("transfer/file-transfer-full-20261020"))
    assert state.state == rs.IN_ARBEIT and state.recommended is None
    steps = guidance.steps(state)
    assert "Transfer-Branch" in steps[0] and "Branch wechseln" in steps[1] and "nur, wenn" in steps[2]
    work = rs.classify(_facts("feat/x"))
    assert work.recommended == rs.ABSCHLIESSEN
    assert guidance.steps(work)[0].startswith("„Abschließen“ klicken")
