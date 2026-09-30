"""AGP_K07_DELIVERY_STATE_V1 / AGP_K07_INFLIGHT_RECORD_V1 behavioral proofs."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from agp_cockpit.core.file_loop_orchestrator import (
    UNKNOWN_OUTCOME_NOTICE,
    _continuation_for_run,
    consume_command_file,
    mark_result_delivered,
)
from agp_cockpit.core.file_loop_protocol import RemoteState
from agp_cockpit.core.file_loop_runner import FileLoopRun, RunnerExecution


def valid_command(text: str = "check") -> str:
    return (
        "import argparse\nfrom pathlib import Path\n"
        f'COMMAND = ["agentic-kit", "{text}"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n"
        "    parser = argparse.ArgumentParser()\n"
        '    parser.add_argument("--self-test", action="store_true")\n'
        "    parser.parse_args()\n"
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


class RecordingController:
    """Stands in for the run_next process; observes durable state at start."""

    def __init__(self, state_file: Path, fail: BaseException | None = None) -> None:
        self.state_file = state_file
        self.fail = fail
        self.observed_states: list[list[str]] = []
        self.calls = 0

    def run(self, argv, *, cwd, timeout_seconds, env=None):
        self.calls += 1
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.observed_states.append([entry.get("state") for entry in state["command_history"]])
        if self.fail is not None:
            raise self.fail
        step = int(argv[-1])
        (Path(cwd) / "Download" / f"{step:03d}_x_return_bundle.json").write_text("{}")
        return RunnerExecution(subprocess.CompletedProcess(argv, 0, "", ""), "COMPLETE")


def make_root(tmp_path: Path) -> Path:
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text("raise SystemExit('controller stub replaces runner')\n")
    return tmp_path


def write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def test_step_is_persisted_as_running_before_runner_starts(tmp_path):
    root = make_root(tmp_path)
    state = root / "state.json"
    controller = RecordingController(state)
    outcome = consume_command_file(write(tmp_path, "a.py", valid_command()), root, state,
                                   process_controller=controller)
    assert controller.observed_states == [["RUNNING"]]
    history = json.loads(state.read_text())["command_history"]
    assert [entry["state"] for entry in history] == ["COMMAND_FILE"]
    assert history[0]["delivery"] == "PENDING"
    assert outcome.delivery_pending is True


def test_lost_outcome_blocks_every_later_command_without_running_it(tmp_path):
    root = make_root(tmp_path)
    state = root / "state.json"
    crashing = RecordingController(state, fail=KeyboardInterrupt())
    with pytest.raises(KeyboardInterrupt):
        consume_command_file(write(tmp_path, "a.py", valid_command("a")), root, state,
                             process_controller=crashing)
    history = json.loads(state.read_text())["command_history"]
    assert history[-1]["state"] == "OUTCOME_UNKNOWN"

    later = RecordingController(state)
    for name, text in (("a.py", valid_command("a")), ("b.py", valid_command("b"))):
        outcome = consume_command_file(write(tmp_path, name, text), root, state,
                                       process_controller=later)
        assert outcome.state is RemoteState.BLOCKED
        assert "unresolved execution outcome" in (outcome.human_reason or "")
    assert later.calls == 0


def test_bridge_restart_with_running_record_is_not_blindly_replayed(tmp_path):
    root = make_root(tmp_path)
    state = root / "state.json"
    state.write_text(json.dumps({
        "mission_id": None,
        "command_history": [{"sha256": "x", "step": 7, "state": "RUNNING"}],
    }))
    controller = RecordingController(state)
    outcome = consume_command_file(write(tmp_path, "a.py", valid_command()), root, state,
                                   process_controller=controller)
    assert outcome.state is RemoteState.BLOCKED
    assert controller.calls == 0


def test_new_remote_command_implies_delivery_of_previous_result(tmp_path):
    root = make_root(tmp_path)
    state = root / "state.json"
    controller = RecordingController(state)
    consume_command_file(write(tmp_path, "a.py", valid_command("a")), root, state,
                         process_controller=controller)
    consume_command_file(write(tmp_path, "b.py", valid_command("b")), root, state,
                         process_controller=controller)
    history = json.loads(state.read_text())["command_history"]
    assert [entry["delivery"] for entry in history] == ["DELIVERED_IMPLIED", "PENDING"]


def test_delivery_acknowledgement_is_bound_to_result_hash_and_idempotent(tmp_path):
    root = make_root(tmp_path)
    state = root / "state.json"
    outcome = consume_command_file(write(tmp_path, "a.py", valid_command()), root, state,
                                   process_controller=RecordingController(state))
    digest = hashlib.sha256(outcome.run.return_bundle.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="unknown result"):
        mark_result_delivered(state, "0" * 64)
    assert mark_result_delivered(state, digest)["idempotent"] is False
    assert mark_result_delivered(state, digest)["idempotent"] is True


def test_unknown_outcome_recovery_prompt_forbids_assuming_no_effect(tmp_path):
    bundle = tmp_path / "diag.json"
    bundle.write_text(json.dumps({"status": "unknown", "outcome": "OUTCOME_UNKNOWN",
                                  "failure_reason": "timeout"}))
    run = FileLoopRun(5, tmp_path / "005_x.py", bundle, tmp_path / "log.txt", None, "", "",
                      "execution_diagnostic")
    assert UNKNOWN_OUTCOME_NOTICE in _continuation_for_run(run)
