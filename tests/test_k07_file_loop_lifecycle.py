from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from agp_cockpit.core.file_loop_lifecycle import FileLoopLifecycle
def test_pause_resume():
    x=FileLoopLifecycle(); g=x.start()["generation"]; assert x.pause()["state"]=="PAUSED"; assert not x.may_start_next_turn(g); assert x.resume()["state"]=="RUNNING"; assert x.may_start_next_turn(g)
def test_stop_fence():
    x=FileLoopLifecycle(); g=x.start()["generation"]; s=x.stop(); assert s["generation"]==g+1 and s["state"]=="STOPPED"; assert not x.may_start_next_turn(g)
def test_reset_fence():
    x=FileLoopLifecycle(); g=x.start()["generation"]; s=x.reset(); assert s["generation"]==g+1 and s["state"]=="IDLE"; assert not x.may_start_next_turn(g)
