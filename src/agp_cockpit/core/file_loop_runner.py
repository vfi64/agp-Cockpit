from __future__ import annotations

import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agp_cockpit.core.command_file_contract import command_contract_violations

MAX_CAPTURE_BYTES = 256 * 1024
MAX_RUNNER_LOG_BYTES = 256 * 1024
MAX_RETURN_BUNDLE_BYTES = 2_000_000


def _bounded_text(value: str | None, limit: int = MAX_CAPTURE_BYTES) -> str:
    """Keep diagnostic text bounded while retaining both beginning and end."""
    text = str(value or "")
    encoded = text.encode("utf-8", errors="replace")
    if len(encoded) <= limit:
        return text
    marker = (
        f"\n...[AGP OUTPUT TRUNCATED; original_bytes={len(encoded)}; "
        f"limit_bytes={limit}]...\n"
    ).encode()
    if len(marker) >= limit:
        return marker[:limit].decode("utf-8", errors="ignore")
    keep = (limit - len(marker)) // 2
    return (
        encoded[:keep].decode("utf-8", errors="replace")
        + marker.decode("utf-8")
        + encoded[-keep:].decode("utf-8", errors="replace")
    )


def _bound_file(path: Path, limit: int = MAX_RUNNER_LOG_BYTES) -> bool:
    """Bound an already-written runner log without deleting its evidence."""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if len(data) <= limit:
        return False
    marker = (
        f"\n...[AGP FILE TRUNCATED; original_bytes={len(data)}; "
        f"limit_bytes={limit}]...\n"
    ).encode()
    keep = max(0, (limit - len(marker)) // 2)
    bounded = data[:keep] + marker + data[-keep:]
    path.write_bytes(bounded[:limit])
    return True


@dataclass(frozen=True)
class FileLoopRun:
    step:int
    command_file:Path
    return_bundle:Path
    run_next_output:Path
    runner_returncode:int | None
    stdout:str
    stderr:str
    artifact_kind:str="return_bundle"


@dataclass(frozen=True)
class RunnerExecution:
    completed: subprocess.CompletedProcess[str]
    outcome: str


class RunNextProcessController:
    """Own the one live run_next process and its complete process group."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._process: subprocess.Popen[str] | None = None
        self._stop_requested = False

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            process = self._process
            return {
                "active": process is not None and process.poll() is None,
                "pid": None if process is None else process.pid,
                "stop_requested": self._stop_requested,
            }

    @staticmethod
    def _signal_group(process: subprocess.Popen[str], signum: int) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(process.pid, signum)
            else:
                process.send_signal(signum)
        except ProcessLookupError:
            return

    @classmethod
    def _terminate_group(cls, process: subprocess.Popen[str]) -> None:
        cls._signal_group(process, signal.SIGTERM)
        deadline = time.monotonic() + 2.0
        while process.poll() is None and time.monotonic() < deadline:
            time.sleep(0.02)
        if process.poll() is None:
            cls._signal_group(process, signal.SIGKILL)

    def run(
        self,
        argv: list[str],
        *,
        cwd: Path,
        timeout_seconds: int,
        env: dict[str, str] | None = None,
    ) -> RunnerExecution:
        process = subprocess.Popen(
            argv,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            start_new_session=True,
        )
        with self._lock:
            self._process = process
            self._stop_requested = False
        try:
            try:
                stdout, stderr = process.communicate(timeout=timeout_seconds)
                with self._lock:
                    outcome = "STOPPED" if self._stop_requested else "COMPLETE"
                return RunnerExecution(
                    subprocess.CompletedProcess(
                        argv,
                        process.returncode,
                        _bounded_text(stdout),
                        _bounded_text(stderr),
                    ),
                    outcome,
                )
            except subprocess.TimeoutExpired as exc:
                self._terminate_group(process)
                stdout, stderr = process.communicate()
                if not stdout:
                    stdout = exc.stdout or ""
                if not stderr:
                    stderr = exc.stderr or ""
                return RunnerExecution(
                    subprocess.CompletedProcess(
                        argv,
                        process.returncode,
                        _bounded_text(stdout),
                        _bounded_text(stderr),
                    ),
                    "TIMEOUT",
                )
        finally:
            with self._lock:
                if self._process is process:
                    self._process = None

    def stop(self) -> dict[str, object]:
        with self._lock:
            process = self._process
            if process is None or process.poll() is not None:
                return {"requested": False, "active": False, "pid": None}
            self._stop_requested = True
            pid = process.pid
        self._terminate_group(process)
        return {"requested": True, "active": False, "pid": pid}
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


def _run_next_interpreter(root: Path) -> str:
    """Choose a real Python interpreter, not the packaged desktop executable."""
    project_python = root / ".venv" / "bin" / "python"
    if project_python.is_file() and os.access(project_python, os.X_OK):
        return str(project_python)
    return sys.executable


def _execution_identity(root: Path, command_file: Path, step: int, argv: list[str], returncode: int) -> dict:
    content = command_file.read_bytes()
    return {
        "command_file_sha256": hashlib.sha256(content).hexdigest(),
        "command_file_bytes": len(content),
        "command_file_lines": content.count(b"\n") + (1 if content and not content.endswith(b"\n") else 0),
        "interpreter": str(argv[0]),
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
                "stdout": _bounded_text(completed.stdout),
                "stderr": _bounded_text(completed.stderr),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _materialize_unknown_diagnostic(
    download: Path,
    step: int,
    command_file: Path,
    completed: subprocess.CompletedProcess[str],
    reason: str,
    outcome: str,
    output_path: Path,
    candidate_bundles: list[Path],
) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    result = download / f"{step}_{command_file.stem}_execution_diagnostic_{stamp}.json"
    result.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "agp_cockpit_file_loop_execution_diagnostic",
                "status": "unknown",
                "outcome": "OUTCOME_UNKNOWN",
                "failure_reason": reason,
                "termination": outcome,
                "step": step,
                "command_file": str(command_file),
                "candidate_return_bundles": [str(path) for path in candidate_bundles],
                "runner_returncode": completed.returncode,
                "run_next_output": str(output_path),
                "stdout": _bounded_text(completed.stdout),
                "stderr": _bounded_text(completed.stderr),
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
                "stdout": _bounded_text(completed.stdout),
                "stderr": _bounded_text(completed.stderr),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _materialize_nonzero_bundle_diagnostic(
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
                "failure_reason": (
                    "authorized run_next returned a non-zero status; "
                    "candidate return bundle(s) are evidence only"
                ),
                "step": step,
                "command_file": str(command_file),
                "candidate_return_bundles": [str(path) for path in bundles],
                "runner_returncode": completed.returncode,
                "run_next_output": str(output_path),
                "stdout": _bounded_text(completed.stdout),
                "stderr": _bounded_text(completed.stderr),
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
                "stdout": _bounded_text(completed.stdout),
                "stderr": _bounded_text(completed.stderr),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def _materialize_oversized_bundle_diagnostic(
    download: Path,
    step: int,
    command_file: Path,
    completed: subprocess.CompletedProcess[str],
    candidate: Path,
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
                "failure_reason": (
                    "return bundle exceeds the bounded evidence limit; "
                    "inspect the producer and use a summary or artifact path instead"
                ),
                "step": step,
                "command_file": str(command_file),
                "candidate_return_bundle": str(candidate),
                "candidate_return_bundle_bytes": candidate.stat().st_size,
                "max_return_bundle_bytes": MAX_RETURN_BUNDLE_BYTES,
                "runner_returncode": completed.returncode,
                "run_next_output": str(output_path),
                "stdout": _bounded_text(completed.stdout),
                "stderr": _bounded_text(completed.stderr),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return result


def kit_guard_dir(root: Path, step: int) -> Path:
    from agp_cockpit.core.runtime_paths import runtime_dir
    return runtime_dir(root.resolve(), "kit-guard", str(step))


def install_kit_guard(root: Path, step: int, kit_approvals=None) -> Path:
    """AGP_KIT_INVOCATION_GUARD_V1: the guard directory for this step, first on PATH."""
    from agp_cockpit.core.kit_command_catalog import KitCommandCatalog
    from agp_cockpit.core.kit_installation import find_kit_binary
    from agp_cockpit.core.kit_invocation_guard import (
        LOG_NAME,
        KitApprovals,
        build_policy,
        guard_interpreter,
        install,
    )

    real_kit = find_kit_binary(root)
    if real_kit is not None and not real_kit.is_file():
        real_kit = None
    directory = kit_guard_dir(root, step)
    policy = build_policy(
        KitCommandCatalog.load(root),
        kit_approvals if kit_approvals is not None else KitApprovals(),
        real_kit=None if real_kit is None else real_kit.resolve() if real_kit.is_absolute() else (root / real_kit).resolve(),
        log_path=directory / LOG_NAME,
    )
    return install(directory, policy, interpreter=guard_interpreter(real_kit, _run_next_interpreter(root)))


def execute_with_run_next(
    root: Path,
    command_file: Path,
    # A Kit orchestrator that publishes, waits for CI, merges and closes out
    # (two CI waits of up to 300 s each plus merges) exceeds 11 minutes.
    timeout_seconds: int = 1800,
    process_controller: RunNextProcessController | None = None,
    kit_approvals=None,
) -> FileLoopRun:
    download=root/"Download"; runner=download/"run_next.py"; output_log=download/"__run_next_output.txt"
    if command_file.parent.resolve()!=download.resolve(): raise ValueError("command file must be in repository Download directory")
    step=step_from_command_file(command_file)
    output_log.write_text("RUN_NEXT_OUTPUT_PENDING\n", encoding="utf-8")
    runner_argv = [_run_next_interpreter(root), str(runner), str(step)]
    try:
        violations = command_contract_violations(command_file, expected_step=step)
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
    if not runner.is_file():
        message = f"RUN_NEXT_UNAVAILABLE\nrunner not found: {runner}\n"
        output_log.write_text(message, encoding="utf-8")
        cp = subprocess.CompletedProcess(runner_argv, 127, message, "")
        result = _materialize_command_failure(
            download,
            step,
            command_file,
            cp,
            "authorized Download/run_next.py is missing",
            output_log,
        ).resolve()
        _attach_execution_identity(result, _execution_identity(root, command_file, step, runner_argv, 127))
        return FileLoopRun(step, command_file, result, output_log, 127, message, "", "execution_diagnostic")
    before={p.resolve() for p in download.glob(f"{step:03d}_*_return_bundle.json")}
    controller = process_controller or RunNextProcessController()
    try:
        # AGP_CI_GREEN_COMPLETION_V1: the project venv plus Homebrew, so Kit
        # commands that query GitHub find `gh` in an app started via `open`.
        from agp_cockpit.core.ci_gate import tool_env
        runner_env = tool_env(root)
        runner_env["AGP_COCKPIT_REPOSITORY_ROOT"] = str(root.resolve())
        # AGP_MAINTENANCE_CLEANUP_V1: temporary files of a work order stay in
        # the repository (cleaned by maintenance), not scattered over /tmp.
        from agp_cockpit.core.runtime_paths import runtime_dir  # AGP_RUNTIME_HOME_V1
        work_tmp = runtime_dir(root.resolve(), "tmp", str(step))
        work_tmp.mkdir(parents=True, exist_ok=True)
        for name in ("TMPDIR", "TEMP", "TMP"):
            runner_env[name] = str(work_tmp)
        # AGP_PYTEST_SHARED_TEMPROOT_V1 (2026-10-29, Kit repository): each work order had its own
        # TMPDIR, so pytest's retention (the newest three runs per temp root) never applied and every
        # test run left a full pytest-of-<user> tree (~38,000 files, ~1,600 symlinks) per step. One
        # temp root per repository lets pytest prune its own old runs.
        pytest_root = runtime_dir(root.resolve(), "tmp", "pytest")
        pytest_root.mkdir(parents=True, exist_ok=True)
        runner_env["PYTEST_DEBUG_TEMPROOT"] = str(pytest_root)
        # AGP_KIT_INVOCATION_GUARD_V1: every real agentic-kit call of the work order meets the
        # guard first; without approvals (None) it refuses every approval-required call.
        runner_env["PATH"] = os.pathsep.join(
            [str(install_kit_guard(root, step, kit_approvals)), runner_env.get("PATH", "")]
        )
        execution = controller.run(
            runner_argv,
            cwd=root,
            timeout_seconds=timeout_seconds,
            env=runner_env,
        )
    except OSError as exc:
        message = f"RUN_NEXT_EXECUTION_FAILED\n{type(exc).__name__}: {exc}\n"
        output_log.write_text(message, encoding="utf-8")
        cp = subprocess.CompletedProcess(runner_argv, 127, message, "")
        result = _materialize_command_failure(
            download,
            step,
            command_file,
            cp,
            f"authorized run_next execution failed: {type(exc).__name__}: {exc}",
            output_log,
        ).resolve()
        _attach_execution_identity(result, _execution_identity(root, command_file, step, runner_argv, 127))
        return FileLoopRun(step, command_file, result, output_log, 127, message, "", "execution_diagnostic")
    cp = execution.completed
    snapshots=sorted(download.glob(f"{step}_run_next_output*.txt"), key=lambda p: p.stat().st_mtime_ns)
    for snapshot in snapshots:
        _bound_file(snapshot)
    _bound_file(output_log)
    if snapshots:
        output_log=snapshots[-1].resolve()
    after={p.resolve() for p in download.glob(f"{step:03d}_*_return_bundle.json")}
    created=sorted(after-before)
    if execution.outcome != "COMPLETE":
        reason = (
            f"local run_next exceeded timeout of {timeout_seconds} seconds; execution outcome is unknown"
            if execution.outcome == "TIMEOUT"
            else "local run_next was terminated by operator stop; execution outcome is unknown"
        )
        diagnostic = _materialize_unknown_diagnostic(
            download,
            step,
            command_file,
            cp,
            reason,
            execution.outcome,
            output_log,
            created,
        ).resolve()
        _attach_execution_identity(
            diagnostic,
            _execution_identity(root, command_file, step, runner_argv, cp.returncode),
        )
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
    if not created:
        if cp.returncode != 0:
            reason = "local command returned a non-zero status"
        elif _contains_command_output(cp.stdout):
            reason = "local command did not create a return bundle; stdout is diagnostic only"
        else:
            reason = "local command produced no return artifact or observable output"
        created = [_materialize_command_failure(download, step, command_file, cp, reason, output_log).resolve()]
    elif cp.returncode != 0:
        diagnostic = _materialize_nonzero_bundle_diagnostic(
            download,
            step,
            command_file,
            cp,
            created,
            output_log,
        ).resolve()
        _attach_execution_identity(
            diagnostic,
            _execution_identity(root, command_file, step, runner_argv, cp.returncode),
        )
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
    if candidate.stat().st_size > MAX_RETURN_BUNDLE_BYTES:
        diagnostic = _materialize_oversized_bundle_diagnostic(
            download,
            step,
            command_file,
            cp,
            candidate,
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
    _attach_execution_identity(
        candidate,
        _execution_identity(root, command_file, step, runner_argv, cp.returncode),
    )
    if candidate.stat().st_size > MAX_RETURN_BUNDLE_BYTES:
        diagnostic = _materialize_oversized_bundle_diagnostic(
            download,
            step,
            command_file,
            cp,
            candidate,
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
