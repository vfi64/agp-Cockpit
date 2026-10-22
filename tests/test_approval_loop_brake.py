"""AGP_DESTRUCTIVE_EXACT_LINE_V1, AGP_SIGNATURE_BOUND_APPROVAL_V1, AGP_APPROVAL_LOOP_BRAKE_V1.

Live 2026-10-22, Kit repository, steps 65-82: a free task had to discard one uncommitted file with
`agentic-kit work discard-changes --execute --expected-signature <preview signature> --json`. The
approval question named only `agentic-kit work discard-changes --execute` (the destructive line was
dropped), the owner approved that shortened line, no work order could match it, and the Cockpit asked
the same question eighteen times until the owner did the step locally.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_human_decision import _bridge, mission

from agp_cockpit.core.human_decision import (
    HumanDecisionStore,
    approval_loop_question,
    exact_commands_in,
)
from agp_cockpit.core.kit_command_catalog import (
    KitCommandCatalog,
    approval_required_invocations,
    computed_argument_violations,
)

ROOT = Path(__file__).resolve().parents[1]
CATALOG = KitCommandCatalog.load(ROOT)
SIGNATURE = "d037edcbac3e873e16ef561c728327a3fe12a680fdc7f54178f17cfc2d653b9c"
LINE = f"agentic-kit work discard-changes --execute --expected-signature {SIGNATURE} --json"
DISCARD = ["work", "discard-changes", "--execute", "--expected-signature", SIGNATURE, "--json"]


def _order(kit_args) -> str:
    return (
        "import argparse, subprocess\nfrom pathlib import Path\n"
        f"KIT = {json.dumps(['agentic-kit', *kit_args])}\n"
        'RETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n    p = argparse.ArgumentParser()\n"
        '    p.add_argument("--self-test", action="store_true")\n    p.parse_args()\n'
        "    subprocess.run(KIT)\n"
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n    main()\n'
    )


def test_a_destructive_execute_keeps_its_literal_line():
    source = f"import subprocess\nsubprocess.run({json.dumps(['agentic-kit', *DISCARD])})\n"
    assert approval_required_invocations(source, CATALOG) == [LINE]
    assert exact_commands_in(f"Befehl: {LINE}\nEs liegt keine Freigabe vor.", CATALOG) == [LINE]
    preview = "import subprocess\nsubprocess.run(['agentic-kit', 'work', 'discard-changes', '--json'])\n"
    assert approval_required_invocations(preview, CATALOG) == []   # the preview needs no approval


def test_a_computed_signature_is_rejected_with_the_preview_route():
    source = ("import subprocess, sys\nS = sys.argv[1]\nsubprocess.run(['agentic-kit', 'work', "
              "'discard-changes', '--execute', '--expected-signature', S, '--json'])\n")
    [violation] = computed_argument_violations(source, CATALOG)
    assert "run the preview" in violation and "write the signature it reported literally" in violation
    other = ("import subprocess, sys\nB = sys.argv[1]\n"
             "subprocess.run(['agentic-kit', 'transfer', 'remote-next', B, '--json'])\n")
    assert "run the preview" not in computed_argument_violations(other, CATALOG)[0]


@pytest.fixture
def bridge(tmp_path):
    for root, runtime, call in _bridge(tmp_path):
        manifest = root / "docs/reference/agentic-kit-commands.json"
        data = json.loads(manifest.read_text())
        data["commands"].append(CATALOG.resolve(["work", "discard-changes"]))
        manifest.write_text(json.dumps(data))
        yield root, runtime, call


def test_the_question_shows_the_signed_line_and_its_exact_approval_runs(bridge):
    _root, runtime, call = bridge
    first = mission(call, runtime)
    asked = call("/v1/file-loop/command", {"filename": "1480_discard.py", "content": _order(DISCARD)})
    assert asked["state"] == "NEEDS_HUMAN" and f"Befehl: {LINE}" in asked["human_reason"]
    record = call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE", "scope": "exact"})
    assert record["grant"]["exact"] == [LINE]

    mission(call, runtime)
    accepted = call("/v1/file-loop/command", {"filename": "1481_discard.py", "content": _order(DISCARD)})
    assert accepted.get("terminal") is not True and accepted["replayed"] is False


def test_the_same_request_after_an_unused_approval_stops_the_mission(bridge):
    root, runtime, call = bridge
    first = mission(call, runtime)
    call("/v1/file-loop/command", {"filename": "1480_discard.py", "content": _order(DISCARD)})
    # "push and PR" does not cover the discard: the approval cannot be used
    call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE", "scope": "push_pr"})
    mission(call, runtime)
    stopped = call("/v1/file-loop/command", {"filename": "1481_discard.py", "content": _order(DISCARD)})
    assert stopped["state"] == "BLOCKED" and stopped["terminal"] is True
    assert "Freigabe-Schleife gestoppt" in stopped["human_reason"] and LINE in stopped["human_reason"]
    assert call("/v1/status")["mission"]["state"] == "BLOCKED"
    assert not (root / "Download" / "1481_discard.py").exists()


def test_a_changed_request_or_a_used_approval_asks_normally(tmp_path):
    store = HumanDecisionStore(tmp_path)
    wanted = ["agentic-kit work discard-changes --execute"]
    assert approval_loop_question(tmp_path, "T", wanted, [LINE], filename="1.py", now=1) == ""
    store.record(mission_id="m1", task_id="T", decision="APPROVE", question="q", now=2)
    other = LINE.replace(SIGNATURE, "0" * 64)
    assert approval_loop_question(tmp_path, "T", wanted, [other], filename="2.py", now=3) == ""
    store.record(mission_id="m2", task_id="T", decision="APPROVE", question="q", now=4)
    store.consume("T", "sha", used=wanted)
    assert approval_loop_question(tmp_path, "T", wanted, [other], filename="3.py", now=5) == ""   # used
    store.record(mission_id="m3", task_id="T", decision="REJECT", question="q", now=6)
    assert approval_loop_question(tmp_path, "T", wanted, [other], filename="4.py", now=7) == ""   # rejected
    store.record(mission_id="m4", task_id="T", decision="APPROVE", question="q", now=8)
    assert "Freigabe-Schleife" in approval_loop_question(tmp_path, "T", wanted, [other], filename="5.py", now=9)
    assert approval_loop_question(tmp_path, "U", wanted, [other], filename="6.py", now=10) == ""   # other task


def test_the_invocation_guard_runs_the_approved_signed_line_and_nothing_else(tmp_path):
    from agp_cockpit.core.kit_command_catalog import approval_required_commands
    from agp_cockpit.core.kit_invocation_guard import KitApprovals, build_policy, decide

    source = f"import subprocess\nsubprocess.run({json.dumps(['agentic-kit', *DISCARD])})\n"
    approvals = KitApprovals(tuple(approval_required_commands(source, CATALOG)), (LINE,))
    policy = build_policy(CATALOG, approvals, real_kit=None, log_path=tmp_path / "log.jsonl")
    assert decide(policy, DISCARD) == ("agentic-kit work discard-changes --execute", "")
    other = [*DISCARD[:4], "0" * 64, "--json"]
    assert "covers only" in decide(policy, other)[1]
    assert decide(policy, ["work", "discard-changes", "--json"]) == ("", "")   # the preview is free
