import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from agp_cockpit.core.automation_guard import AutomationGuard, AutomationLimits
from agp_cockpit.core.file_loop_orchestrator import (
    CONTINUATION_TEXT,
    RECOVERY_CONTINUATION_PREFIX,
    REPLAY_CONTINUATION_TEXT,
    consume_command_file,
    consume_terminal_reply,
)
from agp_cockpit.core.file_loop_protocol import RemoteState


def fixture_root(tmp_path):
    dl=tmp_path/"Download";dl.mkdir();(dl/"run_next.py").write_text("import sys\nfrom pathlib import Path\nn=int(sys.argv[1]);d=Path(__file__).parent\n(d/f'{n:03d}_x_return_bundle.json').write_text('{}')\n");return tmp_path
def test_attachment_exactly_once(tmp_path):
    root=fixture_root(tmp_path);state=root/".local/state.json";incoming=tmp_path/"incoming.py";incoming.write_text(valid_command())
    o=consume_command_file(incoming,root,state);assert o.state is RemoteState.COMMAND_FILE and o.run.return_bundle.exists() and o.continuation_text.startswith(CONTINUATION_TEXT) and o.replayed is False
    replay=consume_command_file(incoming,root,state)
    assert replay.run.return_bundle.exists() and replay.continuation_text==REPLAY_CONTINUATION_TEXT and replay.replayed is True


def test_identical_preflight_failure_replays_even_under_new_remote_name(tmp_path):
    root = tmp_path
    download = root / "Download"
    download.mkdir()
    (download / "run_next.py").write_text("raise SystemExit('runner must not start')\n")
    broken = "def find_package():\n    return None\n"
    first = tmp_path / "1444_chat_switch_standard_task.py"
    second = tmp_path / "1457_chat_switch_standard_task.py"
    first.write_text(broken)
    second.write_text(broken)
    state = root / "state.json"

    first_outcome = consume_command_file(first, root, state)
    second_outcome = consume_command_file(second, root, state)

    assert first_outcome.replayed is False
    assert second_outcome.replayed is True
    assert second_outcome.run is not None
    assert second_outcome.run.step == 1
    assert second_outcome.state is RemoteState.COMMAND_FILE


def test_same_preflight_file_is_replayed_instead_of_reexecuted(tmp_path):
    root = tmp_path
    download = root / "Download"
    download.mkdir()
    (download / "run_next.py").write_text("raise SystemExit('runner must not start')\n")
    source = tmp_path / "1457_chat_switch_standard_task.py"
    source.write_text("def find_package():\n    return None\n")
    state = root / "state.json"

    first = consume_command_file(source, root, state)
    replay = consume_command_file(source, root, state)

    assert first.replayed is False
    assert replay.replayed is True
    assert replay.run is not None
    assert replay.run.step == 1
    assert replay.continuation_text == REPLAY_CONTINUATION_TEXT


def test_new_mission_discards_persisted_preflight_failures(tmp_path):
    root = tmp_path
    download = root / "Download"
    download.mkdir()
    (download / "run_next.py").write_text("raise SystemExit('runner must not start')\n")
    state = root / "state.json"

    old = tmp_path / "1444_chat_switch_standard_task.py"
    old.write_text("def find_package():\n    return None\n")
    old_outcome = consume_command_file(old, root, state, mission_id="old-mission")
    assert old_outcome.state is RemoteState.COMMAND_FILE

    current = tmp_path / "1457_chat_switch_standard_task.py"
    current.write_text("def find_package():\n    return None\n")
    current_outcome = consume_command_file(
        current, root, state, mission_id="new-mission"
    )

    assert current_outcome.state is RemoteState.COMMAND_FILE
    assert current_outcome.continuation_text.startswith(RECOVERY_CONTINUATION_PREFIX)
    persisted = __import__("json").loads(state.read_text())
    assert persisted["mission_id"] == "new-mission"
    assert persisted["preflight_failures"] == 1
    assert len(persisted["command_history"]) == 1
def test_done_and_human(tmp_path):
    state=tmp_path/"state.json";assert consume_terminal_reply("AGP_DONE",state).state is RemoteState.DONE
    state.unlink();o=consume_terminal_reply("AGP_NEEDS_HUMAN\nConfirm login.",state);assert o.state is RemoteState.NEEDS_HUMAN and o.human_reason=="Confirm login."

def test_consume_uses_persisted_step_when_download_inventory_is_missing(tmp_path):
    root=tmp_path;dl=root/"Download";dl.mkdir()
    (dl/"run_next.py").write_text("import sys\nfrom pathlib import Path\nn=int(sys.argv[1]);d=Path(__file__).parent\n(d/f'{n:03d}_x_return_bundle.json').write_text('{}')\n")
    incoming=tmp_path/"incoming.py";incoming.write_text(valid_command("persisted-step"))
    state=root/"state.json";state.write_text('{"step": 1438}')
    outcome=consume_command_file(incoming,root,state)
    assert outcome.run is not None and outcome.run.step==1439
    assert outcome.run.command_file.name.startswith("1439_")


def test_consume_assigns_next_local_step_and_preserves_remote_filename_hint(tmp_path):
    root = fixture_root(tmp_path)
    incoming = tmp_path / "1456_chat_switch_standard_task.py"
    incoming.write_text(valid_command("remote-step"))
    (root / "Download" / "1442_previous.py").write_text("print('old')\n")
    state = root / "state.json"

    outcome = consume_command_file(incoming, root, state)

    assert outcome.run is not None
    assert outcome.run.step == 1443
    assert outcome.run.command_file.name == "1443_chat_switch_standard_task.py"
    assert "1443" in outcome.run.return_bundle.name
    persisted = json.loads(state.read_text())
    assert persisted["remote_filename"] == "1456_chat_switch_standard_task"
    assert "expected local step: 1444" in (outcome.continuation_text or "")
    assert "internal STEP constant" in (outcome.continuation_text or "")

def test_failed_local_step_produces_recovery_prompt(tmp_path):
    root=tmp_path; dl=root/"Download"; dl.mkdir()
    (dl/"run_next.py").write_text(
        "import sys\nfrom pathlib import Path\nPath(__file__).with_name('__run_next_output.txt').write_text('IndentationError: line 78')\nsys.exit(1)\n"
    )
    incoming=tmp_path/"incoming.py"; incoming.write_text("broken\n")
    outcome=consume_command_file(incoming,root,root/"state.json")
    assert outcome.run is not None
    assert outcome.continuation_text.startswith(RECOVERY_CONTINUATION_PREFIX)
    assert "FAILED command-file step" in outcome.continuation_text
    assert "real run was never reached" in outcome.continuation_text
    assert "<= 80 source lines and <= 16 KiB" in outcome.continuation_text

def valid_command(text="check"):
    return (
        'import argparse\nfrom pathlib import Path\n'
        f'COMMAND = ["agentic-kit", "{text}"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        'def main():\n'
        '    parser = argparse.ArgumentParser()\n'
        '    parser.add_argument("--self-test", action="store_true")\n'
        '    parser.parse_args()\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )

def test_three_identical_failures_block_without_fourth_turn(tmp_path):
    root=tmp_path; dl=root/"Download"; dl.mkdir()
    (dl/"run_next.py").write_text(
        'import json,sys\nfrom pathlib import Path\n'
        'n=int(sys.argv[1]); d=Path(__file__).parent\n'
        '(d/f"{n:03d}_x_return_bundle.json").write_text(json.dumps({"status":"failed","failure_reason":"same failure"}))\n'
    )
    state=root/"state.json"
    outcomes=[]
    for index in range(3):
        incoming=tmp_path/f"incoming-{index}.py"
        incoming.write_text(valid_command(f"check-{index}"))
        outcomes.append(consume_command_file(incoming,root,state))
    assert outcomes[-1].state.value == "BLOCKED"
    assert outcomes[-1].continuation_text is None
    replay=consume_command_file(tmp_path/"incoming-2.py",root,state)
    assert replay.state.value == "BLOCKED"
    assert replay.continuation_text is None

def test_semantically_incomplete_command_is_rejected_before_runner(tmp_path):
    root=tmp_path; dl=root/"Download"; dl.mkdir()
    (dl/"run_next.py").write_text("raise SystemExit('runner should not start')\n")
    incoming=tmp_path/"incoming.py"; incoming.write_text("def find_package():\n    return None\n")
    outcome=consume_command_file(incoming,root,root/"state.json")
    assert outcome.run is not None
    assert outcome.run.artifact_kind == "execution_diagnostic"
    assert "semantic contract rejected" in outcome.run.return_bundle.read_text()


def test_two_preflight_failures_block_without_a_third_remote_turn(tmp_path):
    root = tmp_path
    download = root / "Download"
    download.mkdir()
    (download / "run_next.py").write_text("raise SystemExit('runner must not start')\n")
    state = root / "state.json"

    first = tmp_path / "1439_chat_switch_standard_task.py"
    second = tmp_path / "1440_chat_switch_standard_task.py"
    first.write_text("def find_package():\n    return None\n")
    second.write_text("def find_package():\n    return None\n# second truncated candidate\n")

    first_outcome = consume_command_file(first, root, state)
    assert first_outcome.state is RemoteState.COMMAND_FILE
    assert first_outcome.continuation_text.startswith(RECOVERY_CONTINUATION_PREFIX)

    second_outcome = consume_command_file(second, root, state)
    assert second_outcome.state is RemoteState.BLOCKED
    assert second_outcome.continuation_text is None
    assert "preflight failures" in (second_outcome.human_reason or "")
    persisted = __import__("json").loads(state.read_text())
    assert persisted["state"] == "BLOCKED"
    assert persisted["preflight_failures"] == 2


def test_file_loop_uses_shared_guard_turn_budget(tmp_path):
    root = fixture_root(tmp_path)
    state = root / "state.json"
    guard = AutomationGuard(AutomationLimits(max_turns=1))
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"
    first.write_text(valid_command("first"))
    second.write_text(valid_command("second"))

    assert consume_command_file(first, root, state, guard=guard).state is RemoteState.COMMAND_FILE
    blocked = consume_command_file(second, root, state, guard=guard)
    assert blocked.state is RemoteState.BLOCKED
    assert "turn budget exceeded" in (blocked.human_reason or "")


def test_file_loop_deduplicates_replays_without_consuming_repeat_budget(tmp_path):
    root = fixture_root(tmp_path)
    state = root / "state.json"
    guard = AutomationGuard(AutomationLimits(max_identical_assistant_messages=1))
    outcomes = []
    for index in range(3):
        source = tmp_path / f"same-{index}.py"
        source.write_text(valid_command("same"))
        outcomes.append(consume_command_file(source, root, state, guard=guard))

    assert outcomes[0].state is RemoteState.COMMAND_FILE
    assert outcomes[1].replayed is True
    assert outcomes[2].state is RemoteState.COMMAND_FILE
    assert outcomes[2].replayed is True
