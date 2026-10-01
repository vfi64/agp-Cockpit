"""AGP_HUMAN_DECISION_V1 + AGP_REMOTE_EFFECT_GATE_V1: a remote-effect Kit
command runs only after an explicit, one-shot human approval of that task."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.ci_gate import REPAIR_BUDGET
from agp_cockpit.core.human_decision import (
    GRANT_TTL_SECONDS,
    HumanDecisionStore,
    decision_mission_text,
)
from agp_cockpit.core.kit_command_catalog import (
    REMOTE_EFFECT_COMMANDS,
    KitCommandCatalog,
    command_catalog_violations,
)
from agp_cockpit.core.start_request import StartRequestStore
from agp_cockpit.core.task_contract import LocalTaskContract

ROOT = Path(__file__).resolve().parents[1]


def work_order(kit_args: list[str]) -> str:
    return (
        "import argparse, subprocess\nfrom pathlib import Path\n"
        f"KIT = {json.dumps(['agentic-kit', *kit_args])}\n"
        'RETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n    p = argparse.ArgumentParser()\n"
        '    p.add_argument("--self-test", action="store_true")\n    p.parse_args()\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n    main()\n'
    )


def test_every_listed_remote_effect_command_exists_in_the_manifest():
    catalog = KitCommandCatalog.load(ROOT)
    names = {" ".join(c["path"]) for c in catalog.commands}
    assert REMOTE_EFFECT_COMMANDS <= names, sorted(REMOTE_EFFECT_COMMANDS - names)
    push = catalog.resolve(["transfer", "push-current"])
    assert catalog.has_remote_effect(push)
    assert not catalog.has_remote_effect(catalog.resolve(["transfer", "divergence-status"]))


def test_remote_effect_needs_approval_in_the_real_catalog():
    catalog = KitCommandCatalog.load(ROOT)
    source = work_order(["transfer", "push-current"])
    assert any("requires an explicit human approval" in v for v in command_catalog_violations(source, catalog))
    assert command_catalog_violations(source, catalog, allow_remote_effects=True) == []


def test_store_grant_is_task_bound_one_shot_and_expires(tmp_path):
    store = HumanDecisionStore(tmp_path)
    store.record(mission_id="m", task_id="T", decision="APPROVE", question="push?", now=1000.0)
    assert store.remote_effects_allowed("T", now=1001.0)
    assert not store.remote_effects_allowed("other", now=1001.0)
    assert not store.remote_effects_allowed("T", now=1000.0 + GRANT_TTL_SECONDS + 1)
    store.consume("T", "sha")
    # one-shot for the asked action; afterwards only the bounded CI repair budget
    push = ["agentic-kit transfer push-current"]
    assert not store.permits("T", push, ci_gate_active=False, now=1001.0)
    assert store.permits("T", push, ci_gate_active=True, now=1001.0)
    for n in range(REPAIR_BUDGET):
        store.consume("T", f"repair{n}")
    assert not store.remote_effects_allowed("T", now=1001.0)
    with pytest.raises(ValueError):
        store.consume("T", "sha")
    store.record(mission_id="m", task_id="T", decision="REJECT", question="push?")
    assert not store.remote_effects_allowed("T")
    with pytest.raises(ValueError):
        store.record(mission_id="m", task_id="T", decision="MAYBE", question="?")


def test_decision_text_orders_the_approved_action_and_lifts_prepare_only():
    # Live test 4 (1491): the old text appended the prepare-only task
    # "unchanged" and the remote side therefore did not push.
    approved = decision_mission_text(goal_text="prepare only, do not push", decision="APPROVE",
                                     question="Q?", note="ok")
    assert "APPROVED" in approved and "Q?" in approved
    assert "supersedes any \"prepare only\"" in approved
    assert "MUST perform the approved action now" in approved
    assert "allow_network=true" in approved
    # live 1501-1519: the text named primitives and steered away from the orchestrator
    assert "agentic-kit" not in approved
    assert "most comprehensive orchestrator" in approved
    assert "post-merge check" in approved
    assert "Original task (context only; the decision above takes precedence)" in approved
    assert "Original task (unchanged)" not in approved
    assert "Raw git push, git fetch, git pull and gh stay forbidden" in approved
    rejected = decision_mission_text(goal_text="G", decision="REJECT", question="Q?", note="")
    assert "REJECTED" in rejected and "Original task (unchanged)" in rejected


def test_grant_belongs_to_the_continuation_and_expires_unused(tmp_path):
    store = HumanDecisionStore(tmp_path)
    store.record(mission_id="ask", task_id="T", decision="APPROVE", question="push?")
    assert store.grant_for_mission("T", "ask", mission_ended=True) is None   # the asker never uses it
    assert store.remote_effects_allowed("T")
    grant = store.grant_for_mission("T", "cont", mission_ended=False)
    assert grant["question"] == "push?"
    assert store.current()["grant"]["claimed_by"] == "cont"
    assert store.grant_for_mission("T", "cont", mission_ended=True) is None
    assert not store.remote_effects_allowed("T")
    assert "ended without using" in store.current()["grant"]["expired_reason"]

    store.record(mission_id="ask", task_id="T", decision="APPROVE", question="push?")
    store.grant_for_mission("T", "cont", mission_ended=False)
    assert store.grant_for_mission("T", "later", mission_ended=False) is None
    assert not store.remote_effects_allowed("T")


RUNNER = (
    "import sys, json\nfrom pathlib import Path\n"
    "n=int(sys.argv[1]);d=Path(__file__).parent\n"
    "(d/f'{n:03d}_ok_return_bundle.json').write_text(json.dumps({'status':'PASS'}))\n"
)


def _bridge(tmp_path, local_task_contract=None):
    (tmp_path / "Download").mkdir()
    (tmp_path / "Download" / "run_next.py").write_text(RUNNER)
    (tmp_path / "Download" / "1479_previous.py").write_text("# executed\n")
    manifest = tmp_path / "docs/reference/agentic-kit-commands.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"meta": {"manifest_sha": "x"}, "commands": [
        {"qualified_name": "agentic-kit transfer push-current", "path": ["transfer", "push-current"],
         "surface": "primitive", "safety": "BOUNDED", "replaces_raw": ["git push"], "params": []},
        {"qualified_name": "agentic-kit transfer divergence-status", "path": ["transfer", "divergence-status"],
         "surface": "diagnostic", "safety": "READ_ONLY", "replaces_raw": [], "params": []},
    ]}))
    server = BridgeRuntimeServer(tmp_path, port=0, local_task_contract=local_task_contract)
    info = server.start()

    def call(path, payload=None):
        request = Request(f"http://127.0.0.1:{info.port}{path}", method="POST" if payload is not None else "GET",
                          data=None if payload is None else json.dumps(payload).encode(),
                          headers={"X-AGP-Token": info.token, "Content-Type": "application/json"})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())

    try:
        yield tmp_path, server.local_root, call
    finally:
        server.stop()


@pytest.fixture
def bridge(tmp_path):
    yield from _bridge(tmp_path)


@pytest.fixture
def bridge_with_contract(tmp_path):
    yield from _bridge(tmp_path, LocalTaskContract(tmp_path, allow_network=False))


def mission(call, runtime, task_id="T"):
    created = call("/v1/mission", {"title": "Task · t", "mission_text": "m", "execution_mode": "LIVE",
                                    "run_mode": "FULL_AUTO"})["mission"]
    StartRequestStore(runtime).request(created["mission_id"], task_id=task_id)
    return created["mission_id"]


def test_http_push_without_approval_asks_the_human_and_approval_is_consumed(bridge):
    _root, runtime, call = bridge
    first = mission(call, runtime)
    with pytest.raises(HTTPError):   # no decision while the mission is not waiting for one
        call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    # AGP_REMOTE_EFFECT_ASKS_HUMAN_V1: not executed, the mission asks instead of failing
    asked = call("/v1/file-loop/command", {"filename": "1480_push.py",
                                           "content": work_order(["transfer", "push-current"])})
    assert asked["terminal"] is True and asked["state"] == "NEEDS_HUMAN"
    assert "agentic-kit transfer push-current" in asked["human_reason"]
    assert not (_root / "Download" / "1480_push.py").exists()
    assert call("/v1/status")["mission"]["state"] == "NEEDS_HUMAN"
    record = call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE", "note": "ja"})
    assert record["grant"]["remaining"] == 1 and "1480_push.py" in record["question"]

    mission(call, runtime)   # the desktop continues the same task in a new mission
    accepted = call("/v1/file-loop/command", {"filename": "1480_push.py",
                                              "content": work_order(["transfer", "push-current"])})
    assert accepted["replayed"] is False and accepted["terminal"] is not True
    assert HumanDecisionStore(runtime).current()["grant"]["remaining"] == 0

    # after the push only the bounded CI repair budget remains (AGP_CI_GREEN_COMPLETION_V1);
    # once it is used up, the next push asks the human again instead of running
    step = 1481
    for _ in range(REPAIR_BUDGET):
        repaired = call("/v1/file-loop/command", {"filename": f"{step}_push.py",
                                                  "content": work_order(["transfer", "push-current"])
                                                  + f"# repair {step}\n"})
        assert repaired.get("terminal") is not True, repaired
        step += 1
    again = call("/v1/file-loop/command", {"filename": f"{step}_push.py",
                                           "content": work_order(["transfer", "push-current", "--again"])})
    assert again["state"] == "NEEDS_HUMAN" and again["terminal"] is True


def test_invalid_remote_effect_work_order_is_still_rejected(bridge):
    _root, runtime, call = bridge
    mission(call, runtime)
    bad = work_order(["transfer", "push-current"]) + "import os\nos.system('git push')\n"
    with pytest.raises(HTTPError):
        call("/v1/file-loop/command", {"filename": "1480_push.py", "content": bad})


def test_read_only_work_order_needs_no_approval(bridge):
    _root, runtime, call = bridge
    mission(call, runtime)
    read_only = call("/v1/file-loop/command", {"filename": "1480_status.py",
                                               "content": work_order(["transfer", "divergence-status"])})
    assert read_only["replayed"] is False and read_only["terminal"] is not True


def test_http_status_reports_the_approval_and_it_expires_with_the_mission(bridge_with_contract):
    _root, runtime, call = bridge_with_contract
    first = mission(call, runtime)
    assert call("/v1/status")["local_authority"]["allow_network"] is False
    call("/v1/file-loop/terminal", {"filename": "1480_agp_terminal.json",
                                    "content": json.dumps({"state": "NEEDS_HUMAN", "reason": "Push?"})})
    call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    assert "human_approval" not in call("/v1/status")["local_authority"]   # the asker never gets it
    mission(call, runtime)
    authority = call("/v1/status")["local_authority"]
    assert authority["allow_network"] is True
    assert authority["human_approval"]["approved_question"] == "Push?"
    # the continuation ends without using the approval -> it expires
    call("/v1/file-loop/terminal", {"filename": "1481_agp_terminal.json",
                                    "content": json.dumps({"state": "NEEDS_HUMAN", "reason": "anders"})})
    assert HumanDecisionStore(runtime).current()["grant"]["remaining"] == 0
    mission(call, runtime)
    authority = call("/v1/status")["local_authority"]
    assert authority["allow_network"] is False and "human_approval" not in authority
    asked = call("/v1/file-loop/command", {"filename": "1482_push.py",
                                           "content": work_order(["transfer", "push-current"])})
    assert asked["state"] == "NEEDS_HUMAN"
