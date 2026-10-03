"""AGP_DESTRUCTIVE_EXECUTE_GATE_V1 (plan P8, owner 2026-10-03): the full
Wiederherstellen uses the Kit's non-lossy ``work rescue`` (KIT-GF-033, fixed in
Kit 1.0.14). Its dry run runs freely; the signed ``--execute`` of ``work rescue``
and ``work discard-changes`` runs only with an open human approval, and that
approval is always consumed (origin never shows the local effect)."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core import ci_gate
from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.human_decision import HumanDecisionStore
from agp_cockpit.core.kit_command_catalog import (
    DESTRUCTIVE_EXECUTE_COMMANDS,
    LOCAL_ORCHESTRATORS,
    KitCommandCatalog,
    approval_required_commands,
    command_catalog_violations,
    destructive_execute_commands,
)
from agp_cockpit.core.start_request import StartRequestStore

COMMANDS = [
    {"qualified_name": "agentic-kit work rescue", "path": ["work", "rescue"], "surface": "orchestrator",
     "safety": "BOUNDED", "replaces_raw": [], "remote_effects": ["none"],
     "params": [{"opts": ["--execute"]}, {"opts": ["--expected-signature"]}, {"opts": ["--json"]}]},
    {"qualified_name": "agentic-kit work discard-changes", "path": ["work", "discard-changes"],
     "surface": "primitive", "safety": "BOUNDED", "replaces_raw": [], "params": []},
    {"qualified_name": "agentic-kit work recover", "path": ["work", "recover"], "surface": "orchestrator",
     "safety": "BOUNDED", "replaces_raw": [], "params": []},
    {"qualified_name": "agentic-kit transfer push-current", "path": ["transfer", "push-current"],
     "surface": "primitive", "safety": "BOUNDED", "replaces_raw": ["git push"], "params": []},
]
CATALOG = KitCommandCatalog.from_data({"meta": {"manifest_sha": "x"}, "commands": COMMANDS}, "test")


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


def test_rescue_is_a_classified_local_orchestrator():
    rescue = CATALOG.command("agentic-kit work rescue")
    assert "work rescue" in LOCAL_ORCHESTRATORS
    assert CATALOG.effect_known(rescue) and not CATALOG.has_remote_effect(rescue)
    assert DESTRUCTIVE_EXECUTE_COMMANDS == {"work rescue", "work discard-changes"}


def test_dry_run_is_free_and_execute_needs_approval():
    dry = work_order(["work", "rescue", "--json"])
    assert approval_required_commands(dry, CATALOG) == []
    assert command_catalog_violations(dry, CATALOG) == []
    execute = work_order(["work", "rescue", "--execute", "--expected-signature", "abc", "--json"])
    assert destructive_execute_commands(execute, CATALOG) == ["agentic-kit work rescue --execute"]
    assert approval_required_commands(execute, CATALOG) == ["agentic-kit work rescue --execute"]
    assert any("changes local history or files" in v for v in command_catalog_violations(execute, CATALOG))
    discard = "subprocess.run(\"agentic-kit work discard-changes --execute --expected-signature s\")\n"
    assert destructive_execute_commands(discard, CATALOG) == ["agentic-kit work discard-changes --execute"]


def test_execute_flag_on_other_commands_is_not_destructive():
    other = work_order(["work", "recover", "--execute"])
    assert destructive_execute_commands(other, CATALOG) == []
    both = work_order(["work", "rescue", "--execute"]) + work_order(["transfer", "push-current"])
    assert approval_required_commands(both, CATALOG) == [
        "agentic-kit transfer push-current", "agentic-kit work rescue --execute"]


RUNNER = (
    "import sys, json\nfrom pathlib import Path\n"
    "n=int(sys.argv[1]);d=Path(__file__).parent\n"
    "(d/f'{n:03d}_ok_return_bundle.json').write_text(json.dumps({'status':'PASS'}))\n"
)


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    # origin never changes for a local rescue: the refund rule must not apply
    monkeypatch.setattr(ci_gate, "remote_refs", lambda *_a, **_k: {"refs/heads/main": "a" * 40})
    (tmp_path / "Download").mkdir()
    (tmp_path / "Download" / "run_next.py").write_text(RUNNER)
    (tmp_path / "Download" / "1479_previous.py").write_text("# executed\n")
    manifest = tmp_path / "docs/reference/agentic-kit-commands.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"meta": {"manifest_sha": "x"}, "commands": COMMANDS}))
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


def mission(call, runtime, task_id="R"):
    created = call("/v1/mission", {"title": "Task · r", "mission_text": "m", "execution_mode": "LIVE",
                                    "run_mode": "FULL_AUTO"})["mission"]
    StartRequestStore(runtime).request(created["mission_id"], task_id=task_id)
    return created["mission_id"]


def test_bridge_runs_the_dry_run_asks_for_the_execute_and_always_consumes(bridge):
    root, runtime, call = bridge
    first = mission(call, runtime)
    dry = call("/v1/file-loop/command", {"filename": "1480_rescue_dry.py",
                                         "content": work_order(["work", "rescue", "--json"])})
    assert dry["replayed"] is False and dry.get("terminal") is not True
    execute = work_order(["work", "rescue", "--execute", "--expected-signature", "abc", "--json"])
    asked = call("/v1/file-loop/command", {"filename": "1481_rescue.py", "content": execute})
    assert asked["state"] == "NEEDS_HUMAN" and asked["terminal"] is True
    assert "agentic-kit work rescue --execute" in asked["human_reason"]
    assert "lokalen Verlauf" in asked["human_reason"] and "nach außen" not in asked["human_reason"]
    assert not (root / "Download" / "1481_rescue.py").exists()

    call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    mission(call, runtime)
    accepted = call("/v1/file-loop/command", {"filename": "1481_rescue.py", "content": execute})
    assert accepted["replayed"] is False and accepted.get("terminal") is not True
    grant = HumanDecisionStore(runtime).current()["grant"]
    assert grant["remaining"] == 0 and grant["approved_commands"] == ["agentic-kit work rescue --execute"]
    # the consumed approval does not cover a second execute
    again = call("/v1/file-loop/command", {"filename": "1482_rescue.py", "content": execute + "# again\n"})
    assert again["state"] == "NEEDS_HUMAN"


def test_recover_prompt_and_tooltip_describe_the_full_route():
    from agp_cockpit.core import repo_state as rs
    from agp_cockpit.core.standard_tasks import BY_KEY
    from agp_cockpit.core.verbs import BY_KEY as VERBS
    prompt = BY_KEY["recover"].prompt(Path("/r"))
    assert "KIT-GF-033" in prompt and "rescue branch" in prompt and "dry-run signature" in prompt
    assert "only after the\nhuman's approval" in prompt and "Never run raw git" in prompt
    assert "work rescue" not in prompt          # goals, not command names (digest decides)
    tooltip = VERBS[rs.WIEDERHERSTELLEN].tooltip()
    assert "Rescue-Branch" in tooltip and "KIT-GF-033" in tooltip
    assert VERBS[rs.WIEDERHERSTELLEN].kit_gate is None
