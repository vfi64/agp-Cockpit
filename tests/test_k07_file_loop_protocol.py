import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from agp_cockpit.core.file_loop_protocol import (
    RemoteState,
    accept_command_file,
    next_step_number,
    parse_terminal_reply,
    reserve_remote_issued_steps,
)


def valid_command(step: int | None = None) -> str:
    step_line = f'STEP, EFFECT = {step}, "E2"\n' if step is not None else ""
    return (
        "import argparse\nfrom pathlib import Path\n"
        f"{step_line}"
        'COMMAND = ["agentic-kit", "check"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n"
        "    parser = argparse.ArgumentParser()\n"
        '    parser.add_argument("--self-test", action="store_true")\n'
        "    parser.parse_args()\n"
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


def test_accepts_real_python_attachment(tmp_path):
    incoming=tmp_path/"incoming.py";incoming.write_text(valid_command());dl=tmp_path/"Download";dl.mkdir()
    p=accept_command_file(incoming,dl,"probe");assert p.name=="001_probe.py";assert p.read_text()==valid_command()
def test_refuses_non_python_attachment(tmp_path):
    p=tmp_path/"x.txt";p.write_text("x")
    with pytest.raises(ValueError,match=r"\.py"):accept_command_file(p,tmp_path)

def test_next_step_number_respects_persisted_last_step(tmp_path):
    download=tmp_path/"Download";download.mkdir()
    assert next_step_number(download, minimum_step=1438)==1439
    (download/"1442_existing.py").write_text("x\n")
    assert next_step_number(download, minimum_step=1438)==1443


def test_next_step_number_respects_reserved_remote_issued_step(tmp_path):
    download=tmp_path/"Download";download.mkdir()
    reserve_remote_issued_steps(download, [1472])
    assert next_step_number(download, minimum_step=1471)==1473
    incoming = tmp_path/"1472_chat_switch_standard_task.py"
    incoming.write_text(valid_command())
    result=accept_command_file(
        incoming,
        download,
        "1472_chat_switch_standard_task",
        minimum_step=1471,
    )
    assert result.name == "1473_chat_switch_standard_task.py"

def test_local_name_uses_next_local_step_when_remote_repeats(tmp_path):
    incoming=tmp_path/"1456_chat_switch_standard_task.py";incoming.write_text(valid_command())
    download=tmp_path/"Download";download.mkdir()
    result=accept_command_file(incoming,download,incoming.stem,minimum_step=1442)
    assert result.name=="1443_chat_switch_standard_task.py"


def test_stale_remote_step_is_still_materialized_under_next_local_step(tmp_path):
    incoming=tmp_path/"1456_chat_switch_standard_task.py";incoming.write_text(valid_command())
    download=tmp_path/"Download";download.mkdir()
    result=accept_command_file(incoming, download, incoming.stem, minimum_step=1456)
    assert result.name=="1457_chat_switch_standard_task.py"


def test_stale_embedded_step_is_localized_without_trusting_remote_number(tmp_path):
    incoming=tmp_path/"1456_chat_switch_standard_task.py"
    incoming.write_text(valid_command(1456))
    download=tmp_path/"Download";download.mkdir()
    result=accept_command_file(incoming, download, incoming.stem, minimum_step=1456)
    assert result.name=="1457_chat_switch_standard_task.py"
    assert 'STEP, EFFECT = 1457, "E2"' in result.read_text()


def test_remote_step_collision_does_not_overwrite_local_history(tmp_path):
    incoming=tmp_path/"1456_chat_switch_standard_task.py";incoming.write_text(valid_command())
    download=tmp_path/"Download";download.mkdir()
    (download/"1456_chat_switch_standard_task.py").write_text("print('old')\n")
    result=accept_command_file(incoming, download, incoming.stem, minimum_step=1442)
    assert result.name=="1457_chat_switch_standard_task.py"
    assert (download/"1456_chat_switch_standard_task.py").read_text()=="print('old')\n"
def test_done():assert parse_terminal_reply("AGP_DONE").state is RemoteState.DONE
def test_human():
    r=parse_terminal_reply("AGP_NEEDS_HUMAN\nConfirm login.");assert r.state is RemoteState.NEEDS_HUMAN and r.human_reason=="Confirm login."
def test_prose_is_never_executable():
    with pytest.raises(ValueError,match="not executable"):parse_terminal_reply("please run print('x')")
