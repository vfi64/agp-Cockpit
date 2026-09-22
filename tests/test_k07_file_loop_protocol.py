import sys
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from agp_cockpit.core.file_loop_protocol import (
    RemoteState,
    accept_command_file,
    next_step_number,
    parse_terminal_reply,
)


def test_accepts_real_python_attachment(tmp_path):
    incoming=tmp_path/"incoming.py";incoming.write_text("print('ok')\n");dl=tmp_path/"Download";dl.mkdir()
    p=accept_command_file(incoming,dl,"probe");assert p.name=="001_probe.py";assert p.read_text()=="print('ok')\n"
def test_refuses_non_python_attachment(tmp_path):
    p=tmp_path/"x.txt";p.write_text("x")
    with pytest.raises(ValueError,match=r"\.py"):accept_command_file(p,tmp_path)

def test_next_step_number_respects_persisted_last_step(tmp_path):
    download=tmp_path/"Download";download.mkdir()
    assert next_step_number(download, minimum_step=1438)==1439
    (download/"1442_existing.py").write_text("x\n")
    assert next_step_number(download, minimum_step=1438)==1443

def test_local_name_uses_next_local_step_when_remote_repeats(tmp_path):
    incoming=tmp_path/"1456_chat_switch_standard_task.py";incoming.write_text("print('ok')\n")
    download=tmp_path/"Download";download.mkdir()
    result=accept_command_file(incoming,download,incoming.stem,minimum_step=1442)
    assert result.name=="1443_chat_switch_standard_task.py"


def test_stale_remote_step_is_still_materialized_under_next_local_step(tmp_path):
    incoming=tmp_path/"1456_chat_switch_standard_task.py";incoming.write_text("print('ok')\n")
    download=tmp_path/"Download";download.mkdir()
    result=accept_command_file(incoming, download, incoming.stem, minimum_step=1456)
    assert result.name=="1457_chat_switch_standard_task.py"


def test_stale_embedded_step_is_localized_without_trusting_remote_number(tmp_path):
    incoming=tmp_path/"1456_chat_switch_standard_task.py"
    incoming.write_text('STEP, EFFECT = 1456, "E2"\nprint(STEP)\n')
    download=tmp_path/"Download";download.mkdir()
    result=accept_command_file(incoming, download, incoming.stem, minimum_step=1456)
    assert result.name=="1457_chat_switch_standard_task.py"
    assert 'STEP, EFFECT = 1457, "E2"' in result.read_text()


def test_remote_step_collision_does_not_overwrite_local_history(tmp_path):
    incoming=tmp_path/"1456_chat_switch_standard_task.py";incoming.write_text("print('new')\n")
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
