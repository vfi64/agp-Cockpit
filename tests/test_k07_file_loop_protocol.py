from pathlib import Path
import sys,pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from agp_cockpit.core.file_loop_protocol import RemoteState,parse_terminal_reply,accept_command_file
def test_accepts_real_python_attachment(tmp_path):
    incoming=tmp_path/"incoming.py";incoming.write_text("print('ok')\n");dl=tmp_path/"Download";dl.mkdir()
    p=accept_command_file(incoming,dl,"probe");assert p.name=="001_probe.py";assert p.read_text()=="print('ok')\n"
def test_refuses_non_python_attachment(tmp_path):
    p=tmp_path/"x.txt";p.write_text("x")
    with pytest.raises(ValueError,match=r"\.py"):accept_command_file(p,tmp_path)
def test_done():assert parse_terminal_reply("AGP_DONE").state is RemoteState.DONE
def test_human():
    r=parse_terminal_reply("AGP_NEEDS_HUMAN\nConfirm login.");assert r.state is RemoteState.NEEDS_HUMAN and r.human_reason=="Confirm login."
def test_prose_is_never_executable():
    with pytest.raises(ValueError,match="not executable"):parse_terminal_reply("please run print('x')")
