import json
from pathlib import Path

from agp_cockpit.core import result_projection as rp


def _write(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_previous_results_and_duplicate_raw_output_are_replaced_by_markers():
    big = "x" * 50_000
    data = {
        "status": "PASS",
        "previous_bundle": {"kit": big},
        "kit_execution": {"returncode": 0, "stdout_tail": big, "json": {"result_status": "PASS"}},
    }
    projected = rp.project_value(data)
    assert projected["previous_bundle"]["agp_omitted"].startswith("copy of an earlier result")
    assert projected["previous_bundle"]["chars"] > 50_000
    assert projected["kit_execution"]["stdout_tail"]["agp_omitted"].startswith("raw output")
    assert projected["kit_execution"]["json"] == {"result_status": "PASS"}


def test_success_output_is_short_and_failure_output_keeps_much_more():
    text = "".join(f"line {i}\n" for i in range(5_000))
    ok = rp.project_value({"returncode": 0, "stdout": text})["stdout"]
    failed = rp.project_value({"returncode": 1, "stdout": text})["stdout"]
    stderr = rp.project_value({"returncode": 0, "stderr": text})["stderr"]
    assert len(ok) < rp.SUCCESS_TEXT + 120
    assert rp.SUCCESS_TEXT * 5 < len(failed) < rp.FAILURE_TEXT + 120
    assert len(stderr) > rp.SUCCESS_TEXT * 5            # failure keys keep detail
    assert "chars omitted, sha256" in ok and ok.endswith(text[-200:])   # the tail survives


def test_status_failed_marks_a_failure_context():
    text = "y" * 30_000
    assert len(rp.project_value({"status": "BLOCKED", "detail": text})["detail"]) > rp.DEFAULT_TEXT


def test_execution_diagnostic_carries_its_candidate_bundle_projection(tmp_path):
    candidate = _write(tmp_path / "Download" / "7_x_return_bundle.json",
                       {"status": "BLOCKED", "previous_bundle": {"a": "b" * 9_000}, "pr": 3})
    log = tmp_path / "Download" / "7_run_next_output.txt"
    log.write_text("run log\n" * 3_000, encoding="utf-8")
    diagnostic = _write(tmp_path / "Download" / "7_7_x_execution_diagnostic.json", {
        "kind": "agp_cockpit_file_loop_execution_diagnostic", "status": "failed",
        "candidate_return_bundles": [str(candidate)], "run_next_output": str(log),
        "stdout": log.read_text(encoding="utf-8"),
    })
    projected = rp.project_bundle(diagnostic)
    assert projected["stdout"]["agp_omitted"].startswith("same text as the attached run_next log")
    inner = projected["candidate_return_bundle_projections"]["7_x_return_bundle.json"]
    assert inner["pr"] == 3 and inner["previous_bundle"]["agp_omitted"]
    assert projected["agp_projection"]["source"] == diagnostic.name


def test_delivery_keeps_small_results_and_projects_large_ones_deterministically(tmp_path):
    small = _write(tmp_path / "Download" / "1_a_return_bundle.json", {"status": "PASS"})
    stats = rp.delivery_files(tmp_path, small, None)
    assert stats["result_file"] == str(small) and stats["projected"] == []

    large = _write(tmp_path / "Download" / "2_b_return_bundle.json",
                   {"status": "PASS", "previous_bundle": {"z": "q" * 80_000}})
    before = large.read_bytes()
    log = tmp_path / "Download" / "2_run_next_output.txt"
    log.write_text("".join(f"{i}\n" for i in range(20_000)), encoding="utf-8")
    first = rp.delivery_files(tmp_path, large, log)
    delivered = Path(first["result_file"])
    assert delivered.name == large.name and delivered.parent == tmp_path / ".local/agp-cockpit/delivery"
    assert large.read_bytes() == before                      # the local evidence is untouched
    payload = json.loads(delivered.read_text(encoding="utf-8"))
    assert payload["agp_projection"]["source_sha256"] and payload["agp_projection"]["source_bytes"] == len(before)
    assert Path(first["output_file"]).name == log.name and first["bytes_after"] < first["bytes_before"] / 5
    content = delivered.read_bytes()
    second = rp.delivery_files(tmp_path, large, log)
    assert second == first and delivered.read_bytes() == content     # pure function of the bytes


def test_non_json_results_are_delivered_unchanged(tmp_path):
    broken = tmp_path / "Download" / "3_c_return_bundle.json"
    broken.parent.mkdir(parents=True)
    broken.write_text("not json " * 5_000, encoding="utf-8")
    assert rp.delivery_files(tmp_path, broken, None)["result_file"] == str(broken)


def test_bridge_attaches_the_projection():
    source = (Path(__file__).resolve().parents[1] / "src/agp_cockpit/core/bridge_server.py").read_text()
    assert "result_projection.delivery_files(repo_root, result_path, output_path)" in source
    assert '"result_file": delivery["result_file"]' in source
    assert '"output_file": delivery["output_file"]' in source
