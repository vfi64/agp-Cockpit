from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


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


def _materialize_command_failure(
    download: Path,
    step: int,
    command_file: Path,
    completed: subprocess.CompletedProcess[str],
    reason: str,
    output_path: Path,
) -> Path:
    """Persist a failed local command as the single return artifact."""
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
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
                "run_next_output": str(output_path),
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
    output_path: Path,
) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
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
                "run_next_output": str(output_path),
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


def _materialize_invalid_bundle_diagnostic(
    download: Path,
    step: int,
    command_file: Path,
    completed: subprocess.CompletedProcess[str],
    candidate: Path,
    error: str,
    output_path: Path,
) -> Path:
    """Keep an invalid producer artifact as evidence, but never accept it."""
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    result = download / f"{step}_{command_file.stem}_execution_diagnostic_{stamp}.json"
    result.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "agp_cockpit_file_loop_execution_diagnostic",
                "status": "failed",
                "failure_reason": "the command produced an invalid JSON return bundle",
                "step": step,
                "command_file": str(command_file),
                "candidate_return_bundle": str(candidate),
                "candidate_return_bundle_error": error,
                "runner_returncode": completed.returncode,
                "run_next_output": str(output_path),
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
    cp=subprocess.run([sys.executable,str(runner),str(step)],cwd=root,text=True,capture_output=True,timeout=timeout_seconds,check=False)
    snapshots=sorted(download.glob(f"{step}_run_next_output*.txt"), key=lambda p: p.stat().st_mtime_ns)
    if snapshots:
        output_log=snapshots[-1].resolve()
    after={p.resolve() for p in download.glob(f"{step:03d}_*_return_bundle.json")}
    created=sorted(after-before)
    if not created:
        if cp.returncode != 0:
            reason = "local command returned a non-zero status"
        elif _contains_command_output(cp.stdout):
            reason = "local command did not create a return bundle; stdout is diagnostic only"
        else:
            reason = "local command produced no return artifact or observable output"
        created = [_materialize_command_failure(download, step, command_file, cp, reason, output_log).resolve()]
    artifact_kind = "return_bundle"
    if len(created) > 1:
        diagnostic = _materialize_multiple_bundle_diagnostic(
            download, step, command_file, cp, created, output_log
        ).resolve()
        created = [diagnostic]
        artifact_kind = "execution_diagnostic"
    if len(created) != 1:
        raise RuntimeError(f"expected exactly one new return bundle for step {step}, got {len(created)}")
    candidate = created[0]
    try:
        parsed = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        diagnostic = _materialize_invalid_bundle_diagnostic(
            download,
            step,
            command_file,
            cp,
            candidate,
            f"{type(exc).__name__}: {exc}",
            output_log,
        ).resolve()
        return FileLoopRun(
            step,
            command_file,
            diagnostic,
            output_log,
            cp.returncode,
            cp.stdout,
            cp.stderr,
            "execution_diagnostic",
        )
    if not isinstance(parsed, dict):
        diagnostic = _materialize_invalid_bundle_diagnostic(
            download,
            step,
            command_file,
            cp,
            candidate,
            "JSON return bundle must contain one object",
            output_log,
        ).resolve()
        return FileLoopRun(
            step,
            command_file,
            diagnostic,
            output_log,
            cp.returncode,
            cp.stdout,
            cp.stderr,
            "execution_diagnostic",
        )
    return FileLoopRun(step,command_file,candidate,output_log,cp.returncode,cp.stdout,cp.stderr,artifact_kind)
