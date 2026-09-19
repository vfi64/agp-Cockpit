from pathlib import Path
import sys,pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from agp_cockpit.core.file_loop_protocol import RemoteState
from agp_cockpit.core.file_loop_orchestrator import consume_command_file,consume_terminal_reply,CONTINUATION_TEXT,REPLAY_CONTINUATION_TEXT,RECOVERY_CONTINUATION_PREFIX
def fixture_root(tmp_path):
    dl=tmp_path/"Download";dl.mkdir();(dl/"run_next.py").write_text("import sys\nfrom pathlib import Path\nn=int(sys.argv[1]);d=Path(__file__).parent\n(d/f'{n:03d}_x_return_bundle.json').write_text('{}')\n");return tmp_path
def test_attachment_exactly_once(tmp_path):
    root=fixture_root(tmp_path);state=root/".local/state.json";incoming=tmp_path/"incoming.py";incoming.write_text(valid_command())
    o=consume_command_file(incoming,root,state);assert o.state is RemoteState.COMMAND_FILE and o.run.return_bundle.exists() and o.continuation_text==CONTINUATION_TEXT and o.replayed is False
    replay=consume_command_file(incoming,root,state)
    assert replay.run.return_bundle.exists() and replay.continuation_text==REPLAY_CONTINUATION_TEXT and replay.replayed is True
def test_done_and_human(tmp_path):
    state=tmp_path/"state.json";assert consume_terminal_reply("AGP_DONE",state).state is RemoteState.DONE
    state.unlink();o=consume_terminal_reply("AGP_NEEDS_HUMAN\nConfirm login.",state);assert o.state is RemoteState.NEEDS_HUMAN and o.human_reason=="Confirm login."

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
