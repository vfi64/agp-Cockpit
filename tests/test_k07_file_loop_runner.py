from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
import pytest
from agp_cockpit.core.file_loop_runner import step_from_command_file,execute_with_run_next
def test_step():
    assert step_from_command_file(Path("936_probe.py"))==936
    with pytest.raises(ValueError): step_from_command_file(Path("probe.py"))
def make(tmp_path,body):
    dl=tmp_path/"Download"; dl.mkdir(); (dl/"run_next.py").write_text(body); cmd=dl/"001_probe.py"; cmd.write_text("x=1\n"); return cmd
def test_one(tmp_path):
    cmd=make(tmp_path,"import sys\nfrom pathlib import Path\nn=int(sys.argv[1]); d=Path(__file__).parent\n(d/f'{n:03d}_probe_return_bundle.json').write_text('{}')\n")
    r=execute_with_run_next(tmp_path,cmd); assert r.return_bundle.name=="001_probe_return_bundle.json"
def test_zero(tmp_path):
    cmd=make(tmp_path,"import sys\n")
    with pytest.raises(RuntimeError,match="exactly one"): execute_with_run_next(tmp_path,cmd)
def test_two(tmp_path):
    cmd=make(tmp_path,"import sys\nfrom pathlib import Path\nn=int(sys.argv[1]); d=Path(__file__).parent\n(d/f'{n:03d}_a_return_bundle.json').write_text('{}')\n(d/f'{n:03d}_b_return_bundle.json').write_text('{}')\n")
    with pytest.raises(RuntimeError,match="got 2"): execute_with_run_next(tmp_path,cmd)
