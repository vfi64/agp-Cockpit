"""AGP_HANDOFF_PROJECTION_V2_CONSUMER_V1 (KIT-GF-094, Kit main 334ac052): „Chat wechseln“ accepts the external
handoff projection v2. Its package files stay byte-identical across regenerations; a new run_id in the ignored
runtime identity, the exact HEAD and the validator PASS of that same run prove the regeneration. v1 keeps its
old evidence; any other projection contract is BLOCKED."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from agp_cockpit.core import handoff_completion as hc
from agp_cockpit.core.task_controller import DurableTaskController

HEAD = "a" * 40
V2_REPORT = {"kind": "successor_handoff_validation_report", "schema_version": 1, "status": "PASS",
             "projection_contract_version": 2, "generator_version": 2, "input_digest": "b" * 64, "findings": []}


def identity(run_id: str, **overrides) -> dict:
    data = {"schema_version": 1, "projection_contract_version": 2, "head": HEAD, "generated_head": HEAD,
            "origin_main": HEAD, "branch": "main", "worktree_clean": True,
            "generated_at_utc": "2026-11-01T00:00:00+00:00", "run_id": run_id, "input_digest": "b" * 64,
            "freshness": "PASS", "integrity": "PASS", "validator_status": "PASS"}
    data.update(overrides)
    return data


def write_identity(root, data) -> None:
    path = root / hc.RUNTIME_IDENTITY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


@pytest.fixture
def v2(tmp_path, monkeypatch):
    root = tmp_path
    (root / hc.PACKAGE).mkdir(parents=True)
    (root / "Download").mkdir()
    runtime = root / "runtime"
    runtime.mkdir()
    for name in hc.FILES:
        (root / hc.PACKAGE / name).write_text("durable\n")
    (root / hc.PACKAGE / "validation_report.json").write_text(json.dumps(V2_REPORT))
    write_identity(root, identity("run-before"))
    before = hc.package_snapshot(root)
    prompt = root / "Download/2301_START_NEW_CHAT_DETAILED_PROMPT.md"
    prompt.write_text("Read-only intake")
    bundle = root / "Download/2301_return_bundle.json"
    bundle.write_text(json.dumps({"status": "PASS", "package_path": str(root / hc.PACKAGE),
                                  "detailed_start_prompt_path": str(prompt)}))
    run = SimpleNamespace(return_bundle=bundle, runner_returncode=0, artifact_kind="return_bundle", step=2301)
    calls = []

    def kit_v2(_root, head):
        calls.append(head)
        return {"contract": 2, "identity": json.loads((root / hc.RUNTIME_IDENTITY).read_text()),
                "projection": {"status": "PASS"}, "identity_status": "PASS"}
    monkeypatch.setattr(hc, "validate_v2_with_kit", kit_v2)
    monkeypatch.setattr(hc, "validate_with_kit", lambda _root: pytest.fail("v1 validator used for a v2 package"))
    monkeypatch.setattr(hc.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=HEAD + "\n"))
    controller = DurableTaskController("task", runtime / "tasks.sqlite3")
    controller.store.set_runtime_contract("task", scope={"completion_contract": {"kind": hc.CONTRACT_KIND}})
    yield root, runtime, before, run, controller, calls
    controller.close()


def prepare(v2):
    root, runtime, before, run, _controller, _calls = v2
    return hc.prepare_receipt(root, runtime, mission_id="mission", task_id="task", cycle_id="cycle",
                              run=run, before=before)


def test_byte_identical_v2_package_with_a_new_run_completes(v2):
    root, runtime, _before, _run, controller, calls = v2
    write_identity(root, identity("run-after"))           # the package files are untouched
    receipt = prepare(v2)
    assert receipt["projection_contract"] == 2 and receipt["run_id"] == "run-after" and calls == [HEAD]
    assert str(root / hc.RUNTIME_IDENTITY) in receipt["hashes"]
    result = hc.acknowledge_delivery(root, runtime, controller, mission_id="mission", cycle_id="cycle",
                                     result_sha256=receipt["result_sha256"])
    assert result["state"] == "DONE"


def test_v2_without_a_new_run_is_not_a_completion(v2):
    root, *_ = v2
    for name in hc.FILES:                                  # touched files are no evidence under v2
        (root / hc.PACKAGE / name).touch()
    (root / hc.PACKAGE / "validation_report.json").write_text(json.dumps(V2_REPORT))
    assert prepare(v2) is None


def test_a_later_run_before_the_acknowledgement_is_rejected(v2):
    root, runtime, _before, _run, controller, _calls = v2
    write_identity(root, identity("run-after"))
    receipt = prepare(v2)
    write_identity(root, identity("run-third"))
    with pytest.raises(ValueError):
        hc.acknowledge_delivery(root, runtime, controller, mission_id="mission", cycle_id="cycle",
                                result_sha256=receipt["result_sha256"])


@pytest.mark.parametrize("report", [
    {"status": "PASS", "projection_contract_version": 3},
    {"status": "PASS", "projection_contract_version": True},
    {"status": "PASS"},
])
def test_an_unknown_projection_contract_is_blocked(v2, report):
    root, *_ = v2
    (root / hc.PACKAGE / "validation_report.json").write_text(json.dumps(report))
    write_identity(root, identity("run-after"))
    with pytest.raises(ValueError, match="BLOCKED"):
        prepare(v2)


def test_v1_package_is_still_recognised(tmp_path):
    (tmp_path / hc.PACKAGE).mkdir(parents=True)
    (tmp_path / hc.PACKAGE / "validation_report.json").write_text(json.dumps({"status": "PASS", "generated_head": HEAD}))
    assert hc.projection_contract(tmp_path) == 1
    (tmp_path / hc.PACKAGE / "validation_report.json").write_text("[]")
    with pytest.raises(ValueError, match="BLOCKED"):
        hc.projection_contract(tmp_path)


def _kit_answer(monkeypatch, **report):
    answer = {"contract": 2, "runtime_path": str(hc.RUNTIME_IDENTITY), "projection": {"status": "PASS"},
              "identity": identity("run-after"), "identity_status": "PASS"}
    answer.update(report)
    monkeypatch.setattr(hc.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=json.dumps(answer)))


def test_the_cockpit_reads_the_runtime_identity_itself(monkeypatch, tmp_path):
    _kit_answer(monkeypatch)
    assert hc.validate_v2_with_kit(tmp_path, HEAD)["identity"]["run_id"] == "run-after"
    for bad in ({"identity": identity("r", head="c" * 40)}, {"identity": identity("r", generated_head="c" * 40)},
                {"identity": identity("r", integrity="FAIL")}, {"identity": identity("r", schema_version=2)},
                {"identity_status": "FAIL"}, {"projection": {"status": "FAIL", "code": "projection_integrity_mismatch"}}):
        _kit_answer(monkeypatch, **bad)
        with pytest.raises(ValueError):
            hc.validate_v2_with_kit(tmp_path, HEAD)
    for blocked in ({"contract": 3}, {"identity": identity("r", projection_contract_version=3)},
                    {"runtime_path": ".agentic/tmp/elsewhere.json"}):
        _kit_answer(monkeypatch, **blocked)
        with pytest.raises(ValueError, match="BLOCKED"):
            hc.validate_v2_with_kit(tmp_path, HEAD)
