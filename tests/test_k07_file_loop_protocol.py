from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from agp_cockpit.core.file_loop_protocol import RemoteState,parse_remote_reply,persist_command

def test_command_file_round_trip(tmp_path: Path):
    r=parse_remote_reply("AGP_COMMAND_FILE_BEGIN\nprint('ok')\nAGP_COMMAND_FILE_END")
    assert r.state is RemoteState.COMMAND_FILE
    p=persist_command(r,tmp_path,"probe")
    assert p.name=="001_probe.py"
    assert p.read_text()=="print('ok')\n"

def test_done():
    assert parse_remote_reply("AGP_DONE").state is RemoteState.DONE

def test_needs_human_reason():
    r=parse_remote_reply("AGP_NEEDS_HUMAN\nPlease confirm login.")
    assert r.state is RemoteState.NEEDS_HUMAN
    assert r.human_reason=="Please confirm login."

@pytest.mark.parametrize("bad",[
    "hello",
    "prose\nAGP_COMMAND_FILE_BEGIN\nx=1\nAGP_COMMAND_FILE_END",
    "AGP_COMMAND_FILE_BEGIN\nAGP_COMMAND_FILE_END",
    "AGP_COMMAND_FILE_BEGIN\nx=1\nAGP_COMMAND_FILE_END\ntrailing",
])
def test_fail_loud(bad):
    with pytest.raises(ValueError):
        parse_remote_reply(bad)
