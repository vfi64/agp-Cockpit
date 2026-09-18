import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
import pytest

from agp_cockpit.core.file_loop_runner import (
    execute_with_run_next,
    step_from_command_file,
)


def test_step():
    assert step_from_command_file(Path("936_probe.py"))==936
    with pytest.raises(ValueError): step_from_command_file(Path("probe.py"))
def make(tmp_path,body):
    dl=tmp_path/"Download"; dl.mkdir(); (dl/"run_next.py").write_text(body); cmd=dl/"001_probe.py"; cmd.write_text("x=1\n"); return cmd
def test_one(tmp_path):
    cmd=make(tmp_path,"import sys\nfrom pathlib import Path\nn=int(sys.argv[1]); d=Path(__file__).parent\n(d/f'{n:03d}_probe_return_bundle.json').write_text('{}')\n")
    r=execute_with_run_next(tmp_path,cmd); assert r.return_bundle.name=="001_probe_return_bundle.json"
    assert r.run_next_output == tmp_path / "Download" / "__run_next_output.txt"
def test_zero(tmp_path):
    cmd=make(tmp_path,"import sys\n")
    r=execute_with_run_next(tmp_path,cmd)
    data=__import__('json').loads(r.return_bundle.read_text())
    assert data["status"]=="failed"
    assert "no return artifact" in data["failure_reason"]

def test_work_order_output_is_not_treated_as_execution(tmp_path):
    cmd=make(tmp_path,"import json\nprint(json.dumps({'kind':'generic','cwd':str(__file__),'argv':['git','status'],'timeout_seconds':30,'label':'status'}))\n")
    r=execute_with_run_next(tmp_path,cmd)
    data=__import__('json').loads(r.return_bundle.read_text())
    assert data["kind"]=="agp_cockpit_file_loop_return_bundle"
    assert data["status"]=="failed"
    assert "did not create a return bundle" in data["failure_reason"]

def test_successful_command_output_gets_materialized_as_return_bundle(tmp_path):
    cmd=make(tmp_path,"import subprocess\nprint(subprocess.run(['printf','status-ok'],capture_output=True,text=True).stdout)\n")
    r=execute_with_run_next(tmp_path,cmd)
    data=__import__('json').loads(r.return_bundle.read_text())
    assert data["kind"]=="agp_cockpit_file_loop_return_bundle"
    assert "status-ok" in data["stdout"]
def test_two(tmp_path):
    cmd=make(tmp_path,"import sys\nfrom pathlib import Path\nn=int(sys.argv[1]); d=Path(__file__).parent\n(d/f'{n:03d}_a_return_bundle.json').write_text('{}')\n(d/f'{n:03d}_b_return_bundle.json').write_text('{}')\n")
    r=execute_with_run_next(tmp_path,cmd)
    data=__import__('json').loads(r.return_bundle.read_text())
    assert r.artifact_kind=="execution_diagnostic"
    assert data["kind"]=="agp_cockpit_file_loop_execution_diagnostic"
    assert len(data["candidate_return_bundles"])==2

def test_failed_command_gets_json_return_bundle(tmp_path):
    cmd=make(tmp_path,"import sys\nprint('compile failed: invalid syntax')\nraise SystemExit(1)\n")
    r=execute_with_run_next(tmp_path,cmd)
    data=__import__('json').loads(r.return_bundle.read_text())
    assert r.runner_returncode==1
    assert data["status"]=="failed"
    assert data["execution"]=="command_file_failed"
    assert data["runner_returncode"]==1
    assert data["work_order"] is None
    assert "compile failed" in data["stdout"]

def test_runner_uses_step_scoped_log_when_available(tmp_path):
    cmd=make(tmp_path,"import sys\nfrom pathlib import Path\nn=int(sys.argv[1]); d=Path(__file__).parent\n(d/f'{n}_run_next_output.txt').write_text('immutable-log')\n(d/f'{n:03d}_probe_return_bundle.json').write_text('{}')\n")
    r=execute_with_run_next(tmp_path,cmd)
    assert r.run_next_output == tmp_path / "Download" / "1_run_next_output.txt"

def test_invalid_return_bundle_becomes_failed_diagnostic(tmp_path):
    cmd=make(tmp_path,"import sys\nfrom pathlib import Path\nn=int(sys.argv[1]); d=Path(__file__).parent\n(d/f'{n:03d}_probe_return_bundle.json').write_text('not-json')\n")
    r=execute_with_run_next(tmp_path,cmd)
    data=__import__('json').loads(r.return_bundle.read_text())
    assert r.artifact_kind=="execution_diagnostic"
    assert data["kind"]=="agp_cockpit_file_loop_execution_diagnostic"
    assert data["status"]=="failed"
    assert data["candidate_return_bundle"].endswith("001_probe_return_bundle.json")
    assert "JSONDecodeError" in data["candidate_return_bundle_error"]
    assert Path(data["candidate_return_bundle"]).exists()
