import sys

import pytest

from agp_cockpit.core.terminal_exec import (
    TerminalCommand,
    preview_command,
    run_command,
)
from agp_cockpit.core.terminal_policy import ExecutionPolicy


def test_runs_argument_vector_without_shell(tmp_path):
    command = TerminalCommand(
        argv=(sys.executable, "-c", "print('hello')"),
        cwd=tmp_path,
        timeout_seconds=5,
    )
    result = run_command(command)
    assert result.returncode == 0
    assert result.stdout.strip() == "hello"
    assert result.stderr == ""
    assert result.timed_out is False


def test_shell_metacharacters_are_plain_arguments(tmp_path):
    command = TerminalCommand(
        argv=(
            sys.executable,
            "-c",
            "import sys; print(sys.argv[1])",
            "hello; touch SHOULD_NOT_EXIST",
        ),
        cwd=tmp_path,
    )
    result = run_command(command)
    assert result.returncode == 0
    assert result.stdout.strip() == "hello; touch SHOULD_NOT_EXIST"
    assert not (tmp_path / "SHOULD_NOT_EXIST").exists()


def test_timeout_is_bounded(tmp_path):
    command = TerminalCommand(
        argv=(
            sys.executable,
            "-c",
            "import time; time.sleep(5)",
        ),
        cwd=tmp_path,
        timeout_seconds=0.1,
    )
    result = run_command(command)
    assert result.timed_out is True


def test_preview_contains_cwd_and_argv(tmp_path):
    command = TerminalCommand(
        argv=("python3", "-V"),
        cwd=tmp_path,
    )
    preview = preview_command(command)
    assert f"CWD: {tmp_path}" in preview
    assert "[0] python3" in preview
    assert "[1] -V" in preview


def test_policy_rejects_external_cwd(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    policy = ExecutionPolicy(repository_root=repo)
    command = TerminalCommand(argv=("echo", "x"), cwd=outside)

    with pytest.raises(PermissionError):
        policy.validate(command)


def test_policy_accepts_repo_subdir(tmp_path):
    repo = tmp_path / "repo"
    child = repo / "sub"
    child.mkdir(parents=True)

    policy = ExecutionPolicy(repository_root=repo)
    command = TerminalCommand(argv=("echo", "x"), cwd=child)

    policy.validate(command)


def test_policy_rejects_sudo(tmp_path):
    policy = ExecutionPolicy(repository_root=tmp_path)
    command = TerminalCommand(argv=("sudo", "echo", "x"), cwd=tmp_path)

    with pytest.raises(PermissionError):
        policy.validate(command)
