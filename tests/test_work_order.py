import json
import sys

import pytest

from agp_cockpit.core.terminal_policy import ExecutionPolicy
from agp_cockpit.core.work_order import parse_work_order_json
from agp_cockpit.core.work_order_runner import (
    execute_work_order,
    preview_work_order,
)


def test_parse_structured_work_order(tmp_path):
    raw = json.dumps({
        "label": "test",
        "cwd": str(tmp_path),
        "argv": [sys.executable, "-c", "print('ok')"],
        "timeout_seconds": 5,
    })

    order = parse_work_order_json(raw)

    assert order.label == "test"
    assert order.cwd == tmp_path
    assert order.argv[0] == sys.executable


def test_invalid_shell_string_is_not_accepted_as_argv(tmp_path):
    raw = json.dumps({
        "cwd": str(tmp_path),
        "argv": "echo hello; rm -rf x",
    })

    with pytest.raises(ValueError):
        parse_work_order_json(raw)


def test_preview_then_execute(tmp_path):
    order = parse_work_order_json(json.dumps({
        "label": "test order",
        "cwd": str(tmp_path),
        "argv": [sys.executable, "-c", "print('hello')"],
        "timeout_seconds": 5,
    }))
    policy = ExecutionPolicy(repository_root=tmp_path)

    preview = preview_work_order(order, policy=policy)
    assert "ARGV:" in preview.preview_text

    run = execute_work_order(order, policy=policy)

    assert run.result.returncode == 0
    assert "RC=0" in run.result_block
    assert "hello" in run.result_block
    assert "BEGINN ERGEBNISBLOCK" in run.result_block
    assert "ENDE ERGEBNISBLOCK" in run.result_block


def test_external_cwd_is_blocked(tmp_path):
    repo = tmp_path / "repo"
    outside = tmp_path / "outside"
    repo.mkdir()
    outside.mkdir()

    order = parse_work_order_json(json.dumps({
        "cwd": str(outside),
        "argv": [sys.executable, "-c", "print('x')"],
    }))

    policy = ExecutionPolicy(repository_root=repo)

    with pytest.raises(PermissionError):
        preview_work_order(order, policy=policy)


def test_work_order_uses_injected_terminal_port_without_subprocess(tmp_path):
    order = parse_work_order_json(json.dumps({
        "label": "portable",
        "cwd": str(tmp_path),
        "argv": ["fake-tool", "arg"],
        "timeout_seconds": 5,
    }))
    policy = ExecutionPolicy(repository_root=tmp_path)

    class FakeTerminal:
        def __init__(self):
            self.previewed = []
            self.executed = []

        def preview(self, command):
            self.previewed.append(command)
            return "FAKE PREVIEW"

        def execute(self, command):
            from agp_cockpit.core.terminal_exec import TerminalResult
            self.executed.append(command)
            return TerminalResult(
                argv=command.argv,
                cwd=command.cwd,
                returncode=0,
                stdout="portable-ok\n",
                stderr="",
                timed_out=False,
                duration_seconds=0.0,
            )

    terminal = FakeTerminal()
    preview = preview_work_order(order, policy=policy, terminal=terminal)
    run = execute_work_order(order, policy=policy, terminal=terminal)

    assert preview.preview_text == "FAKE PREVIEW"
    assert len(terminal.previewed) == 1
    assert len(terminal.executed) == 1
    assert run.result.returncode == 0
    assert "portable-ok" in run.result_block
