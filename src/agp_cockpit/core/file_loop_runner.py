from __future__ import annotations

import ast
import hashlib
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


def command_contract_violations(command_file: Path) -> list[str]:
    """Reject syntactically valid but incomplete remote work-order files."""
    source = command_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(command_file))
    functions = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    strings = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    has_self_test_argument = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and any(isinstance(argument, ast.Constant) and argument.value == "--self-test" for argument in node.args)
        for node in ast.walk(tree)
    )
    has_bundle_writer = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"write_text", "write_bytes"}
        for node in ast.walk(tree)
    ) or any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"dump", "dump_json"}
        for node in ast.walk(tree)
    )
    has_main_guard = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and any(isinstance(value, ast.Constant) and value.value == "__main__" for value in node.test.comparators)
        for node in ast.walk(tree)
    )
    violations: list[str] = []
    if "main" not in functions:
        violations.append("missing main() entry point")
    if not has_main_guard:
        violations.append("missing __main__ execution guard")
    if "--self-test" not in strings or not has_self_test_argument:
        violations.append("missing --self-test contract")
    if "agentic-kit" not in strings:
        violations.append("missing declared agentic-kit command")
    if not any("return_bundle" in value for value in strings) or not has_bundle_writer:
        violations.append("missing return-bundle contract")
    return violations


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


def _execution_identity(root: Path, command_file: Path, step: int, argv: list[str], returncode: int) -> dict:
    content = command_file.read_bytes()
    return {
        "command_file_sha256": hashlib.sha256(content).hexdigest(),
        "command_file_bytes": len(content),
        "command_file_lines": content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0),
        "interpreter": sys.executable,
        "cwd": str(root.resolve()),
        "argv": [str(item) for item in argv],
        "returncode": returncode,
    }


def _attach_execution_identity(path: Path, identity: dict) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return
    if not isinstance(payload, dict):
        return
    payload["execution_identity"] = identity
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


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
    runner_argv = [sys.executable, str(runner), str(step)]
    try:
        violations = command_contract_violations(command_file)
    except (OSError, UnicodeDecodeError, SyntaxError) as exc:
        violations = [f"command contract could not be inspected: {type(exc).__name__}: {exc}"]
    if violations:
        message = "RUN_NEXT_PRECHECK_FAILED\n" + "\n".join(f"- {item}" for item in violations) + "\n"
        output_log.write_text(message, encoding="utf-8")
        cp = subprocess.CompletedProcess(runner_argv, 2, stdout=message, stderr="")
        result = _materialize_command_failure(
            download,
            step,
            command_file,
            cp,
            "command file semantic contract rejected: " + "; ".join(violations),
            output_log,
        ).resolve()
        _attach_execution_identity(result, _execution_identity(root, command_file, step, runner_argv, 2))
        return FileLoopRun(step, command_file, result, output_log, 2, message, "", "execution_diagnostic")
    before={p.resolve() for p in download.glob(f"{step:03d}_*_return_bundle.json")}
    cp=subprocess.run(runner_argv,cwd=root,text=True,capture_output=True,timeout=timeout_seconds,check=False)
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
    _attach_execution_identity(
        candidate,
        _execution_identity(root, command_file, step, runner_argv, cp.returncode),
    )
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
