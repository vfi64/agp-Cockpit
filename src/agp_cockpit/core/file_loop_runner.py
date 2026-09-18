from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import json
import subprocess, sys
@dataclass(frozen=True)
class FileLoopRun:
    step:int
    command_file:Path
    return_bundle:Path
    run_next_output:Path
    runner_returncode:int
    stdout:str
    stderr:str
    artifact_kind:str="return_bundle"
def step_from_command_file(path:Path)->int:
    prefix=path.name.split("_",1)[0]
    if not prefix.isdigit(): raise ValueError("command file must start with numeric step")
    return int(prefix)


def _work_order_output(stdout: str) -> dict | None:
    """Return a valid work-order object from the runner's final output line."""
    for line in reversed(stdout.splitlines()):
        candidate = line.strip()
        if not candidate:
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if (
            isinstance(value, dict)
            and isinstance(value.get("argv"), list)
            and value.get("argv")
            and isinstance(value.get("cwd"), str)
            and value.get("cwd").strip()
        ):
            return value
    return None


def _contains_command_output(stdout: str) -> bool:
    """Distinguish command output from the fixed run_next progress banners."""
    noise = (
        "Repository :",
        "Script     :",
        "SHA-256    :",
        "Python     :",
        "SELF_TEST_PASS",
        "SELF-TEST PASSED - STARTING REAL RUN",
        "RUN_NEXT PASS",
        "$ ",
        "[rc=",
    )
    return any(
        line.strip()
        and not line.lstrip().startswith("=")
        and not line.strip().startswith(noise)
        for line in stdout.splitlines()
    )


def _materialize_work_order_result(
    download: Path,
    step: int,
    command_file: Path,
    completed: subprocess.CompletedProcess[str],
    work_order: dict,
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    result = download / f"{step}_{command_file.stem}_run_{stamp}_return_bundle.json"
    result.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "agp_cockpit_file_loop_return_bundle",
                "step": step,
                "command_file": str(command_file),
                "execution": "work_order_emitted_by_command_file",
                "artifact_kind": "return_bundle",
                "runner_returncode": completed.returncode,
                "run_next_output": str(download / "__run_next_output.txt"),
                "work_order": work_order,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _materialize_command_failure(
    download: Path,
    step: int,
    command_file: Path,
    completed: subprocess.CompletedProcess[str],
    reason: str,
) -> Path:
    """Persist a failed local command as the single return artifact."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    result = download / f"{step}_{command_file.stem}_run_{stamp}_return_bundle.json"
    result.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "agp_cockpit_file_loop_return_bundle",
                "step": step,
                "command_file": str(command_file),
                "execution": "command_file_failed",
                "artifact_kind": "return_bundle",
                "status": "failed",
                "failure_reason": reason,
                "runner_returncode": completed.returncode,
                "run_next_output": str(download / "__run_next_output.txt"),
                "work_order": None,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _materialize_multiple_bundle_diagnostic(
    download: Path,
    step: int,
    command_file: Path,
    completed: subprocess.CompletedProcess[str],
    bundles: list[Path],
) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    result = download / f"{step}_{command_file.stem}_execution_diagnostic_{stamp}.json"
    result.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "agp_cockpit_file_loop_execution_diagnostic",
                "status": "failed",
                "failure_reason": "multiple new return bundles were produced; none was selected",
                "step": step,
                "command_file": str(command_file),
                "candidate_return_bundles": [str(path) for path in bundles],
                "runner_returncode": completed.returncode,
                "run_next_output": str(download / "__run_next_output.txt"),
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def execute_with_run_next(root:Path,command_file:Path,timeout_seconds:int=300)->FileLoopRun:
    download=root/"Download"; runner=download/"run_next.py"; output_log=download/"__run_next_output.txt"
    if command_file.parent.resolve()!=download.resolve(): raise ValueError("command file must be in repository Download directory")
    step=step_from_command_file(command_file)
    output_log.write_text("RUN_NEXT_OUTPUT_PENDING\n", encoding="utf-8")
    before={p.resolve() for p in download.glob(f"{step:03d}_*_return_bundle.json")}
    cp=subprocess.run([sys.executable,str(runner),str(step)],cwd=root,text=True,capture_output=True,timeout=timeout_seconds)
    after={p.resolve() for p in download.glob(f"{step:03d}_*_return_bundle.json")}
    created=sorted(after-before)
    if not created:
        work_order = _work_order_output(cp.stdout)
        if cp.returncode != 0:
            created = [
                _materialize_command_failure(
                    download, step, command_file, cp, "local command returned a non-zero status"
                ).resolve()
            ]
        elif work_order is not None or _contains_command_output(cp.stdout):
            created = [
                _materialize_work_order_result(
                    download, step, command_file, cp, work_order
                ).resolve()
            ]
        else:
            created = [
                _materialize_command_failure(
                    download,
                    step,
                    command_file,
                    cp,
                    "local command produced no return artifact or observable output",
                ).resolve()
            ]
    artifact_kind = "return_bundle"
    if len(created) > 1:
        diagnostic = _materialize_multiple_bundle_diagnostic(
            download, step, command_file, cp, created
        ).resolve()
        created = [diagnostic]
        artifact_kind = "execution_diagnostic"
    if len(created) != 1:
        raise RuntimeError(f"expected exactly one new return bundle for step {step}, got {len(created)}")
    return FileLoopRun(step,command_file,created[0],output_log,cp.returncode,cp.stdout,cp.stderr,artifact_kind)
