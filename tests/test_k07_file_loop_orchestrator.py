from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
import pytest
from agp_cockpit.core.file_loop_protocol import RemoteState
from agp_cockpit.core.file_loop_orchestrator import consume_remote_reply

def fixture_root(tmp_path):
    dl=tmp_path/"Download"; dl.mkdir()
    (dl/"run_next.py").write_text("import sys\nfrom pathlib import Path\nn=int(sys.argv[1]); d=Path(__file__).parent\n(d/f'{n:03d}_x_return_bundle.json').write_text('PASS')\n")
    return tmp_path

def test_command_exactly_once(tmp_path):
    root=fixture_root(tmp_path); state=root/".local/state.json"
    text="AGP_COMMAND_FILE_BEGIN\nprint('x')\nAGP_COMMAND_FILE_END"
    o=consume_remote_reply(text,root,state)
    assert o.state is RemoteState.COMMAND_FILE and o.run.return_bundle.exists()
    with pytest.raises(RuntimeError,match="duplicate"): consume_remote_reply(text,root,state)

def test_done_is_terminal(tmp_path):
    state=tmp_path/"state.json"
    o=consume_remote_reply("AGP_DONE",tmp_path,state)
    assert o.state is RemoteState.DONE

def test_human_is_terminal(tmp_path):
    state=tmp_path/"state.json"
    o=consume_remote_reply("AGP_NEEDS_HUMAN\nConfirm login.",tmp_path,state)
    assert o.state is RemoteState.NEEDS_HUMAN and o.human_reason=="Confirm login."
