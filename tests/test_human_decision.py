"""AGP_HUMAN_DECISION_V1 + AGP_REMOTE_EFFECT_GATE_V1: a remote-effect Kit
command runs only after an explicit, one-shot human approval of that task."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
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
    assert not store.remote_effects_allowed("T", now=1001.0)
    with pytest.raises(ValueError):
        store.consume("T", "sha")
    store.record(mission_id="m", task_id="T", decision="REJECT", question="push?")
    assert not store.remote_effects_allowed("T")
    with pytest.raises(ValueError):
        store.record(mission_id="m", task_id="T", decision="MAYBE", question="?")


def test_decision_text_states_the_scope_of_the_approval():
    approved = decision_mission_text(goal_text="G", decision="APPROVE", question="Q?", note="ok")
    assert "APPROVED" in approved and "exactly the next work order" in approved and "Q?" in approved
    assert "Raw git push, git fetch and git pull stay forbidden" in approved
    assert "REJECTED" in decision_mission_text(goal_text="G", decision="REJECT", question="Q?", note="")


RUNNER = (
    "import sys, json\nfrom pathlib import Path\n"
    "n=int(sys.argv[1]);d=Path(__file__).parent\n"
    "(d/f'{n:03d}_ok_return_bundle.json').write_text(json.dumps({'status':'PASS'}))\n"
)


@pytest.fixture
def bridge(tmp_path):
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
    server = BridgeRuntimeServer(tmp_path, port=0)
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


def mission(call, runtime, task_id="T"):
    created = call("/v1/mission", {"title": "Task · t", "mission_text": "m", "execution_mode": "LIVE",
                                    "run_mode": "FULL_AUTO"})["mission"]
    StartRequestStore(runtime).request(created["mission_id"], task_id=task_id)
    return created["mission_id"]


def test_http_push_is_rejected_until_approved_and_approval_is_consumed(bridge):
    _root, runtime, call = bridge
    first = mission(call, runtime)
    push = {"filename": "1480_push.py", "content": work_order(["transfer", "push-current"])}
    with pytest.raises(HTTPError) as rejected:
        call("/v1/file-loop/command", push)
    assert "requires an explicit human approval" in rejected.value.read().decode()

    with pytest.raises(HTTPError):   # no decision while the mission is not waiting for one
        call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    call("/v1/file-loop/terminal", {"filename": "1480_agp_terminal.json",
                                    "content": json.dumps({"state": "NEEDS_HUMAN", "reason": "Push?"})})
    record = call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE", "note": "ja"})
    assert record["grant"]["remaining"] == 1 and record["question"] == "Push?"

    mission(call, runtime)   # the desktop continues the same task in a new mission
    accepted = call("/v1/file-loop/command", {"filename": "1481_push.py",
                                              "content": work_order(["transfer", "push-current"])})
    assert accepted["replayed"] is False
    assert HumanDecisionStore(runtime).current()["grant"]["remaining"] == 0

    with pytest.raises(HTTPError):   # one-shot: the next push needs a new approval
        call("/v1/file-loop/command", {"filename": "1482_push.py",
                                       "content": work_order(["transfer", "push-current", "--again"])})
    read_only = call("/v1/file-loop/command", {"filename": "1482_status.py",
                                               "content": work_order(["transfer", "divergence-status"])})
    assert read_only["replayed"] is False
