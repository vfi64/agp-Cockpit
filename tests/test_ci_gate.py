"""AGP_CI_GREEN_COMPLETION_V1: a task that pushed is complete only when the
CI of its pull request is green for the local HEAD (checked with the Kit)."""
from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core import ci_gate
from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.human_decision import HumanDecisionStore
from agp_cockpit.core.start_request import StartRequestStore
from agp_cockpit.core.terminal_reply import parse_terminal_reply

HEAD = "a" * 40


def red(head=HEAD):
    return {"decision": "red", "head_ref_oid": head, "failed_checks": ["agentic-gate"],
            "failed_run_diagnostics": [{"check_name": "agentic-gate", "conclusion": "FAILURE",
                                        "details_url": "https://x/actions/runs/1",
                                        "log_excerpt": "Error: Unexpected return from a matcher function."}]}


def test_evaluate_requires_green_for_exactly_the_local_head():
    assert ci_gate.evaluate({"decision": "green", "head_ref_oid": HEAD}, head=HEAD).kind == "green"
    assert ci_gate.evaluate({"decision": "green", "head_ref_oid": "b" * 40}, head=HEAD).kind == "behind"
    assert ci_gate.evaluate({"decision": "pending", "head_ref_oid": HEAD}, head=HEAD).kind == "pending"
    assert ci_gate.evaluate({"decision": "no-checks", "head_ref_oid": HEAD}, head=HEAD).kind == "pending"
    assert ci_gate.evaluate({"decision": "not-open", "state": "MERGED"}, head=HEAD).kind == "blocked"
    assert ci_gate.evaluate({"decision": "error", "error": "gh missing"}, head=HEAD).kind == "blocked"
    verdict = ci_gate.evaluate(red(), head=HEAD)
    assert verdict.kind == "red" and "Unexpected return" in verdict.log_excerpt
    assert verdict.failed_checks == ("agentic-gate",)


def test_run_pr_status_calls_the_kit_and_tolerates_trailing_lines(tmp_path):
    seen = {}

    def runner(argv, **kwargs):
        seen["argv"], seen["env"] = argv, kwargs["env"]
        return SimpleNamespace(returncode=0, stdout=json.dumps(red()) + "\nFINAL_SIGNAL=x\n", stderr="")

    data = ci_gate.run_pr_status(tmp_path, tmp_path / ".venv/bin/agentic-kit", 7, runner=runner)
    assert data["decision"] == "red"
    assert seen["argv"][1:5] == ["pr", "status", "7", "--json"]
    assert seen["env"]["PATH"].split(os.pathsep)[0] == str(tmp_path / ".venv" / "bin")
    failing = ci_gate.run_pr_status(tmp_path, tmp_path / "kit", 7, runner=lambda *a, **k: SimpleNamespace(
        returncode=1, stdout="", stderr="gh: not logged in"))
    assert failing["decision"] == "error" and "not logged in" in failing["error"]




def test_terminal_reply_carries_an_optional_pull_request_number():
    ok = parse_terminal_reply("12_agp_terminal.json", json.dumps({"state": "DONE", "reason": "r", "pr": 5}))
    assert ok.pr == 5
    assert parse_terminal_reply("12_agp_terminal.json", json.dumps({"state": "DONE", "reason": "r"})).pr is None
    for bad in (0, -1, "5", True):
        with pytest.raises(ValueError):
            parse_terminal_reply("12_agp_terminal.json", json.dumps({"state": "DONE", "reason": "r", "pr": bad}))


def test_approval_covers_repair_pushes_only_while_the_ci_gate_is_active(tmp_path):
    store = HumanDecisionStore(tmp_path)
    store.record(mission_id="ask", task_id="T", decision="APPROVE", question="push?")
    push = ["agentic-kit transfer push-current"]
    assert store.permits("T", ["agentic-kit release-publish"], ci_gate_active=False)   # the asked action
    store.consume("T", "first")
    assert not store.permits("T", push, ci_gate_active=False)
    assert store.permits("T", push, ci_gate_active=True)
    assert store.permits("T", ["agentic-kit transfer pr-create"], ci_gate_active=True)
    assert not store.permits("T", ["agentic-kit release-publish"], ci_gate_active=True)
    for n in range(ci_gate.REPAIR_BUDGET):
        store.consume("T", f"repair{n}")
    assert not store.permits("T", push, ci_gate_active=True)


# --- HTTP: approve -> push -> DONE rejected until the Kit reports green ------

RUNNER = (
    "import sys, json, subprocess\nfrom pathlib import Path\n"
    "n=int(sys.argv[1]);d=Path(__file__).parent\n"
    "(d/f'{n:03d}_ok_return_bundle.json').write_text(json.dumps({'status':'PASS'}))\n"
    # every run publishes a ref, unless the test simulates a run the Kit blocked
    "if not (d.parent/'no-remote-effect').exists():\n"
    "    subprocess.run(['git','push','-q','origin',f'HEAD:refs/heads/run-{n}'],cwd=d.parent,check=True)\n"
)
FAKE_KIT = (
    "#!/usr/bin/env python3\nimport os, sys\n"
    "if sys.argv[1:3] == ['transfer', 'post-merge-check']:\n"
    "    print(os.environ.get('AGP_TEST_PMC', '{\"result_status\": \"PASS\"}')); sys.exit(0)\n"
    "assert sys.argv[1:3] == ['pr', 'status'], sys.argv\n"
    "print(open(os.environ['AGP_TEST_PR_STATUS']).read())\n"
    "print('FINAL_SIGNAL=d')\n"
)
FAKE_GH = (
    "#!/usr/bin/env python3\nimport os, sys\n"
    "if sys.argv[1:3] == ['run', 'list']:\n"
    "    print(open(os.environ['AGP_TEST_RUNS']).read()); sys.exit(0)\n"
    "if sys.argv[1:3] == ['run', 'view']:\n"
    "    print('Error: main broke'); sys.exit(0)\n"
    "sys.exit(2)\n"
)


def work_order(kit_args):
    return (
        "import argparse, subprocess\nfrom pathlib import Path\n"
        f"KIT = {json.dumps(['agentic-kit', *kit_args])}\n"
        'RETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n    p = argparse.ArgumentParser()\n"
        '    p.add_argument("--self-test", action="store_true")\n    p.parse_args()\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n    main()\n'
    )


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", "-b", "fix/x", str(tmp_path)], check=True)
    (tmp_path / "README").write_text("x")
    subprocess.run([*git, "-C", str(tmp_path), "add", "README"], check=True)
    subprocess.run([*git, "-C", str(tmp_path), "commit", "-qm", "c"], check=True)
    head = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], text=True,
                          capture_output=True, check=True).stdout.strip()
    (tmp_path / "Download").mkdir()
    (tmp_path / "Download" / "run_next.py").write_text(RUNNER)
    (tmp_path / "Download" / "1479_previous.py").write_text("# executed\n")
    kit = tmp_path / ".venv" / "bin" / "agentic-kit"
    kit.parent.mkdir(parents=True)
    kit.write_text(FAKE_KIT)
    kit.chmod(kit.stat().st_mode | stat.S_IEXEC)
    gh = tmp_path / ".venv" / "bin" / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
    runs_file = tmp_path / "runs.json"
    monkeypatch.setenv("AGP_TEST_RUNS", str(runs_file))
    origin = tmp_path.parent / (tmp_path.name + "-origin.git")
    subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin", str(origin)], check=True)
    status_file = tmp_path / "pr-status.json"
    monkeypatch.setenv("AGP_TEST_PR_STATUS", str(status_file))
    manifest = tmp_path / "docs/reference/agentic-kit-commands.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"meta": {"manifest_sha": "x"}, "commands": [
        {"qualified_name": f"agentic-kit {' '.join(path)}", "path": path, "surface": "primitive",
         "safety": "BOUNDED", "replaces_raw": [], "params": []}
        for path in (["transfer", "push-current"], ["transfer", "pr-create"], ["pr", "wait-ci"],
                     ["transfer", "divergence-status"], ["release-publish"], ["work", "finish"],
                     ["transfer", "post-merge-complete"])
    ]}))
    server = BridgeRuntimeServer(tmp_path, port=0)
    info = server.start()

    def call(path, payload=None):
        request = Request(f"http://127.0.0.1:{info.port}{path}", method="POST" if payload is not None else "GET",
                          data=None if payload is None else json.dumps(payload).encode(),
                          headers={"X-AGP-Token": info.token, "Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())

    try:
        yield SimpleNamespace(root=tmp_path, runtime=server.local_root, call=call, head=head,
                              status=status_file, runs=runs_file, origin=origin)
    finally:
        server.stop()


def start(b):
    created = b.call("/v1/mission", {"title": "Task · t", "mission_text": "m", "execution_mode": "LIVE",
                                      "run_mode": "FULL_AUTO"})["mission"]
    StartRequestStore(b.runtime).request(created["mission_id"], task_id="T")
    return created["mission_id"]


def step(b):
    return b.call("/v1/status")["next_local_step"]


def command(b, name, kit_args):
    n = step(b)
    return b.call("/v1/file-loop/command", {"filename": f"{n}_{name}.py", "content": work_order(kit_args)})


def done(b, **extra):
    n = step(b)
    return b.call("/v1/file-loop/terminal", {"filename": f"{n}_agp_terminal.json",
                                             "content": json.dumps({"state": "DONE", "reason": "pushed", **extra})})


def test_http_done_is_accepted_only_with_green_ci_for_the_local_head(bridge):
    b = bridge
    first = start(b)
    asked = command(b, "push", ["transfer", "push-current"])
    assert asked["state"] == "NEEDS_HUMAN"
    b.call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    start(b)
    assert command(b, "push", ["transfer", "push-current"]).get("terminal") is not True
    assert ci_gate.CiGateStore(b.runtime).required("T")

    no_pr = done(b)
    assert no_pr["state"] == "CONTINUE" and no_pr["terminal"] is False
    assert "pull request against main" in no_pr["prompt"]
    assert "agentic-kit transfer" not in no_pr["prompt"]          # goals, not commands
    assert "most comprehensive orchestrator" in no_pr["prompt"]
    assert f"{no_pr['next_step']}_" in no_pr["prompt"]
    assert b.call("/v1/status")["mission"]["state"] not in {"DONE", "NEEDS_HUMAN"}

    # PR creation and a repair push are covered by the approval's repair budget
    assert command(b, "pr", ["transfer", "pr-create"]).get("terminal") is not True
    b.status.write_text(json.dumps(red(b.head)))
    rejected = done(b, pr=7)
    assert rejected["state"] == "CONTINUE"
    assert "Unexpected return from a matcher function" in rejected["prompt"]
    assert (b.root / ".local/agp-cockpit/ci" / f"{b.head}.json").is_file()
    assert command(b, "repair_push", ["transfer", "push-current"]).get("terminal") is not True
    # a remote effect outside the repair budget still asks the human
    assert command(b, "publish", ["release-publish"])["state"] == "NEEDS_HUMAN"


def test_http_green_ci_completes_and_pending_waits(bridge):
    b = bridge
    first = start(b)
    command(b, "push", ["transfer", "push-current"])
    b.call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    start(b)
    command(b, "push", ["transfer", "push-current"])
    b.status.write_text(json.dumps({"decision": "pending", "head_ref_oid": b.head}))
    waiting = done(b, pr=7)
    assert waiting["state"] == "CONTINUE" and "Wait for the CI" in waiting["prompt"]
    b.status.write_text(json.dumps({"decision": "green", "head_ref_oid": b.head}))
    finished = done(b)          # the PR number is remembered
    assert finished["state"] == "DONE" and finished["authority"] == "ci-verified"
    assert b.call("/v1/status")["mission"]["state"] == "DONE"


def test_http_without_a_push_done_is_not_gated(bridge):
    b = bridge
    start(b)
    command(b, "status", ["transfer", "divergence-status"])
    assert done(b)["state"] == "DONE"


def test_http_exhausted_repairs_end_with_needs_human(bridge):
    b = bridge
    first = start(b)
    command(b, "push", ["transfer", "push-current"])
    b.call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    start(b)
    command(b, "push", ["transfer", "push-current"])
    gate = ci_gate.CiGateStore(b.runtime)
    gate._update("T", red_heads=["1" * 40, "2" * 40, "3" * 40])   # three red repairs already
    b.status.write_text(json.dumps(red(b.head)))
    final = done(b, pr=7)
    assert final["state"] == "NEEDS_HUMAN" and final["authority"] == "ci-gate-exhausted"


# --- AGP_CI_LIFECYCLE_COMPLETION_V2: a merging orchestrator needs the merged lifecycle ---

def test_merge_expected_follows_the_commands_that_ran():
    assert ci_gate.merge_expected(["agentic-kit work finish"], "KIT=['agentic-kit','work','finish']")
    assert not ci_gate.merge_expected(["agentic-kit work finish"], "... '--no-merge' ...")
    assert not ci_gate.merge_expected(["agentic-kit transfer push-current"], "")
    assert ci_gate.merge_expected(["agentic-kit transfer pr-create-complete"], "--no-merge")


def approve_and_run_orchestrator(b):
    first = start(b)
    assert command(b, "finish", ["work", "finish"])["state"] == "NEEDS_HUMAN"
    b.call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    start(b)
    assert command(b, "finish", ["work", "finish"]).get("terminal") is not True
    entry = ci_gate.CiGateStore(b.runtime).get("T")
    assert entry["required"] and entry["merge_expected"]


def merged_main(b):
    git = ["git", "-C", str(b.root)]
    subprocess.run([*git, "branch", "-m", "main"], check=True)


def test_http_open_green_pr_is_not_enough_after_a_merging_orchestrator(bridge):
    b = bridge
    approve_and_run_orchestrator(b)
    b.status.write_text(json.dumps({"decision": "green", "state": "OPEN", "head_ref_oid": b.head}))
    rejected = done(b, pr=7)
    assert rejected["state"] == "CONTINUE" and "merge the pull request" in rejected["prompt"]
    # re-running the approved orchestrator is covered by the repair budget
    assert command(b, "finish_again", ["work", "finish"]).get("terminal") is not True
    assert command(b, "closeout", ["transfer", "post-merge-complete"]).get("terminal") is not True
    assert command(b, "publish", ["release-publish"])["state"] == "NEEDS_HUMAN"


def test_http_merged_lifecycle_needs_sync_closeout_and_green_main(bridge, monkeypatch):
    b = bridge
    approve_and_run_orchestrator(b)
    b.status.write_text(json.dumps({"decision": "not-open", "state": "MERGED", "head_ref_oid": b.head}))
    subprocess.run(["git", "-C", str(b.root), "push", "-q", "origin", "HEAD:refs/heads/main"], check=True)
    behind = done(b, pr=7)                       # merged, but still on the feature branch
    assert behind["state"] == "CONTINUE" and "synchronized with origin/main" in behind["prompt"]
    merged_main(b)
    monkeypatch.setenv("AGP_TEST_PMC", '{"result_status": "BLOCKED", "state": "NEEDS_SUCCESSOR_PACKAGE_REFRESH"}')
    closeout = done(b)
    assert closeout["state"] == "CONTINUE" and "post-merge closeout" in closeout["prompt"]
    monkeypatch.setenv("AGP_TEST_PMC", '{"result_status": "PASS"}')
    b.runs.write_text(json.dumps([{"databaseId": 9, "status": "completed", "conclusion": "failure",
                                   "workflowName": "Agentic Gate"}]))
    red = done(b)
    assert red["state"] == "CONTINUE" and "Error: main broke" in red["prompt"], red
    b.runs.write_text(json.dumps([{"databaseId": 10, "status": "in_progress", "conclusion": "",
                                   "workflowName": "Agentic Gate"}]))
    assert done(b)["state"] == "CONTINUE"
    b.runs.write_text(json.dumps([{"databaseId": 11, "status": "completed", "conclusion": "success",
                                   "workflowName": "Agentic Gate"}]))
    finished = done(b)
    assert finished["state"] == "DONE" and finished["authority"] == "ci-verified"
    assert "gemergt" in finished["human_reason"]
    evidence = json.loads((b.root / ".local/agp-cockpit/ci" / f"{b.head}.json").read_text())
    assert evidence["lifecycle"]["origin_main"] == b.head


def test_http_merged_pr_without_the_local_work_is_not_done(bridge):
    b = bridge
    git = ["git", "-C", str(b.root), "-c", "user.name=t", "-c", "user.email=t@t"]
    (b.root / "fix.txt").write_text("local fix")
    subprocess.run([*git, "add", "fix.txt"], check=True)
    subprocess.run([*git, "commit", "-qm", "local fix not yet in the PR"], check=True)
    approve_and_run_orchestrator(b)
    # the PR was merged at the older head; the new local commit never reached it
    b.status.write_text(json.dumps({"decision": "not-open", "state": "MERGED", "head_ref_oid": b.head}))
    rejected = done(b, pr=7)
    assert rejected["state"] == "CONTINUE"
    assert "not part of the merged pull request" in rejected["prompt"]


def test_content_script_defines_sleep():
    source = (Path(__file__).resolve().parents[1] / "chrome_extension/content.js").read_text()
    assert "function sleep(" in source and "await sleep(" in source


# --- AGP_EFFECT_REFUND_V1 ---------------------------------------------------

def test_http_a_run_without_any_change_on_origin_keeps_the_approval(bridge):
    b = bridge
    first = start(b)
    command(b, "push", ["transfer", "push-current"])
    b.call("/v1/task/decision", {"mission_id": first, "decision": "APPROVE"})
    start(b)
    (b.root / "no-remote-effect").write_text("the Kit blocked before any mutation")
    assert command(b, "push", ["transfer", "push-current"]).get("terminal") is not True
    grant = HumanDecisionStore(b.runtime).current()["grant"]
    assert grant["remaining"] == 1 and not grant.get("consumed")
    assert not ci_gate.CiGateStore(b.runtime).required("T")
    (b.root / "no-remote-effect").unlink()
    assert command(b, "push_again", ["transfer", "push-current", "--json"]).get("terminal") is not True
    assert HumanDecisionStore(b.runtime).current()["grant"]["remaining"] == 0
    assert ci_gate.CiGateStore(b.runtime).required("T")
