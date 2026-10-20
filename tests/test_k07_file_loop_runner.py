import shutil
import sys
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
import pytest

from agp_cockpit.core.file_loop_runner import (
    MAX_CAPTURE_BYTES,
    MAX_RETURN_BUNDLE_BYTES,
    MAX_RUNNER_LOG_BYTES,
    RunNextProcessController,
    _run_next_interpreter,
    command_contract_violations,
    execute_with_run_next,
    step_from_command_file,
)


def test_self_test_argv_guard_is_a_valid_contract(tmp_path):
    command = tmp_path / "001_probe.py"
    command.write_text(
        'import sys\nfrom pathlib import Path\n'
        'COMMAND = ["agentic-kit", "check"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        'def main():\n'
        '    if "--self-test" in sys.argv: return 0\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )
    assert "missing --self-test contract" not in command_contract_violations(command)


def test_embedded_step_must_match_local_step(tmp_path):
    command = tmp_path / "1461_probe.py"
    command.write_text(
        'import sys\nfrom pathlib import Path\n'
        'STEP = 1460\n'
        'COMMAND = ["agentic-kit", "check"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        'def main():\n'
        '    if "--self-test" in sys.argv: return 0\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )
    violations = command_contract_violations(command, expected_step=1461)
    assert "embedded STEP 1460 does not match local step 1461" in violations


def test_tuple_embedded_step_must_match_local_step(tmp_path):
    command = tmp_path / "1461_probe.py"
    command.write_text(
        'import sys\nfrom pathlib import Path\n'
        'STEP, EFFECT = 1460, "E2"\n'
        'COMMAND = ["agentic-kit", "check"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        'def main():\n'
        '    if "--self-test" in sys.argv: return 0\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )
    violations = command_contract_violations(command, expected_step=1461)
    assert "embedded STEP 1460 does not match local step 1461" in violations


def test_matching_embedded_step_is_accepted(tmp_path):
    command = tmp_path / "1461_probe.py"
    command.write_text(
        'import sys\nfrom pathlib import Path\n'
        'STEP = 1461\n'
        'COMMAND = ["agentic-kit", "check"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        'def main():\n'
        '    if "--self-test" in sys.argv: return 0\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )
    assert "embedded STEP" not in " ".join(command_contract_violations(command, expected_step=1461))


def test_step():
    assert step_from_command_file(Path("936_probe.py"))==936
    with pytest.raises(ValueError): step_from_command_file(Path("probe.py"))


def test_truncated_python_is_rejected_before_run_next(tmp_path):
    cmd = make(tmp_path, "raise SystemExit('runner must not start')\n")
    cmd.write_text("def find_package():\n    if True:\n")

    result = execute_with_run_next(tmp_path, cmd)
    data = __import__("json").loads(result.return_bundle.read_text())

    assert result.artifact_kind == "execution_diagnostic"
    assert result.runner_returncode == 2
    assert data["execution"] == "command_file_failed"
    assert "IndentationError" in data["failure_reason"]
    assert "semantic contract rejected" in data["failure_reason"]
    assert "runner must not start" not in result.stdout
def make(tmp_path,body):
    dl=tmp_path/"Download"; dl.mkdir(); (dl/"run_next.py").write_text(body)
    cmd=dl/"001_probe.py"; cmd.write_text(
        'import argparse\nfrom pathlib import Path\n'
        'COMMAND = ["agentic-kit", "check"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        'def main():\n'
        '    parser = argparse.ArgumentParser()\n'
        '    parser.add_argument("--self-test", action="store_true")\n'
        '    parser.parse_args()\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    ); return cmd
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


def test_nonzero_runner_with_candidate_bundle_is_diagnostic(tmp_path):
    cmd=make(tmp_path,"import sys\nfrom pathlib import Path\nn=int(sys.argv[1]); d=Path(__file__).parent\n(d/f'{n:03d}_probe_return_bundle.json').write_text('{\"status\":\"ok\"}')\nsys.exit(1)\n")
    result=execute_with_run_next(tmp_path,cmd)
    data=__import__("json").loads(result.return_bundle.read_text())
    assert result.artifact_kind=="execution_diagnostic"
    assert result.runner_returncode==1
    assert data["status"]=="failed"
    assert "non-zero status" in data["failure_reason"]
    assert data["candidate_return_bundles"][0].endswith("001_probe_return_bundle.json")


def test_canonical_runner_self_test_bundle_is_not_success(tmp_path):
    download=tmp_path/"Download"; download.mkdir()
    shutil.copy2(ROOT/"Download/run_next.py", download/"run_next.py")
    command=download/"001_probe.py"
    command.write_text(
        'import argparse\nfrom pathlib import Path\n'
        'COMMAND = ["agentic-kit", "check"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        'def main():\n'
        '    parser = argparse.ArgumentParser()\n'
        '    parser.add_argument("--self-test", action="store_true")\n'
        '    parser.parse_args()\n'
        '    Path(__file__).with_name("001_probe_return_bundle.json").write_text("{\\"status\\":\\"ok\\"}")\n'
        'if __name__ == "__main__":\n'
        '    main()\n'
    )
    result=execute_with_run_next(tmp_path,command)
    data=__import__("json").loads(result.return_bundle.read_text())
    assert result.artifact_kind=="execution_diagnostic"
    assert result.runner_returncode==1
    assert "non-zero status" in data["failure_reason"]
    assert "Self-test produced canonical response artifact" in (
        result.stdout + result.stderr + result.run_next_output.read_text(encoding="utf-8")
    )


def test_runner_puts_project_venv_first_on_child_path(tmp_path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    cmd = make(
        tmp_path,
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "n=int(sys.argv[1]); d=Path(__file__).parent\n"
        "(d/f'{n:03d}_path_return_bundle.json').write_text(json.dumps({'path': os.environ['PATH'].split(os.pathsep)[:2]}))\n",
    )
    result = execute_with_run_next(tmp_path, cmd)
    # AGP_KIT_INVOCATION_GUARD_V1: the step's Kit guard comes first, then the project venv.
    guard, venv = __import__("json").loads(result.return_bundle.read_text())["path"]
    assert Path(guard).name == "1" and Path(guard).parent.name == "kit-guard"
    assert venv == str(tmp_path / ".venv" / "bin")


def test_runner_prefers_project_python_over_desktop_bundle(tmp_path):
    python_path = tmp_path / ".venv" / "bin" / "python"
    python_path.parent.mkdir(parents=True)
    python_path.symlink_to(sys.executable)

    assert _run_next_interpreter(tmp_path) == str(python_path)

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


def test_oversized_bundle_and_runner_output_are_bounded_and_rejected(tmp_path):
    cmd = make(
        tmp_path,
        "import sys\n"
        "from pathlib import Path\n"
        "n=int(sys.argv[1]); d=Path(__file__).parent\n"
        "(d/f'{n:03d}_probe_return_bundle.json').write_text('x' * 2100000)\n"
        "(d/f'{n}_run_next_output.txt').write_text('y' * 300000)\n"
        "print('z' * 600000)\n",
    )

    result = execute_with_run_next(tmp_path, cmd)
    data = __import__("json").loads(result.return_bundle.read_text())

    assert result.artifact_kind == "execution_diagnostic"
    assert data["status"] == "failed"
    assert "exceeds the bounded evidence limit" in data["failure_reason"]
    assert data["candidate_return_bundle_bytes"] > MAX_RETURN_BUNDLE_BYTES
    assert len(result.stdout.encode("utf-8")) <= MAX_CAPTURE_BYTES
    assert result.run_next_output.stat().st_size <= MAX_RUNNER_LOG_BYTES


def test_missing_authorized_runner_becomes_diagnostic_bundle(tmp_path):
    cmd = make(tmp_path, "import sys\n")
    (tmp_path / "Download" / "run_next.py").unlink()

    result = execute_with_run_next(tmp_path, cmd)
    data = __import__("json").loads(result.return_bundle.read_text())

    assert result.artifact_kind == "execution_diagnostic"
    assert data["status"] == "failed"
    assert "run_next.py is missing" in data["failure_reason"]


def test_timeout_is_materialized_as_outcome_unknown_and_process_group_stops(tmp_path):
    cmd = make(
        tmp_path,
        "import sys, time\n"
        "from pathlib import Path\n"
        "n=int(sys.argv[1]); d=Path(__file__).parent\n"
        "time.sleep(5)\n"
        "(d/f'{n:03d}_probe_return_bundle.json').write_text('{}')\n",
    )

    result = execute_with_run_next(tmp_path, cmd, timeout_seconds=0.1)
    data = __import__("json").loads(result.return_bundle.read_text())

    assert result.artifact_kind == "execution_diagnostic"
    assert data["status"] == "unknown"
    assert data["outcome"] == "OUTCOME_UNKNOWN"
    assert data["termination"] == "TIMEOUT"
    assert result.run_next_output.exists()
    time.sleep(0.2)
    assert not (tmp_path / "Download" / "001_probe_return_bundle.json").exists()


def test_operator_stop_terminates_active_runner_and_materializes_unknown_result(tmp_path):
    cmd = make(
        tmp_path,
        "import sys, time\n"
        "from pathlib import Path\n"
        "n=int(sys.argv[1]); d=Path(__file__).parent\n"
        "time.sleep(5)\n"
        "(d/f'{n:03d}_probe_return_bundle.json').write_text('{}')\n",
    )
    controller = RunNextProcessController()
    holder = {}

    def run():
        holder["result"] = execute_with_run_next(
            tmp_path,
            cmd,
            timeout_seconds=10,
            process_controller=controller,
        )

    thread = threading.Thread(target=run)
    thread.start()
    deadline = time.monotonic() + 3
    while not controller.snapshot()["active"] and time.monotonic() < deadline:
        time.sleep(0.01)
    assert controller.snapshot()["active"] is True

    stop = controller.stop()
    thread.join(timeout=3)
    result = holder["result"]
    data = __import__("json").loads(result.return_bundle.read_text())

    assert stop["requested"] is True
    assert result.artifact_kind == "execution_diagnostic"
    assert data["status"] == "unknown"
    assert data["outcome"] == "OUTCOME_UNKNOWN"
    assert data["termination"] == "STOPPED"
    assert thread.is_alive() is False
