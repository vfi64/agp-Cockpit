from pathlib import Path

import json

import agp_cockpit.core.kit_carrier as carrier
from agp_cockpit.core.work_order import LocalWorkOrder


def test_generic_command_is_accepted_without_kit_lookup(tmp_path):
    order = LocalWorkOrder(
        argv=("/usr/bin/printf", "x"),
        cwd=tmp_path,
        kind="generic",
    )

    result = carrier.inspect_kit_authority(
        order,
        kit_binary=Path("/fake/agentic-kit"),
    )

    assert result.accepted is True
    assert result.is_kit_command is False


def test_kit_command_invokes_command_for(monkeypatch, tmp_path):
    calls = []

    class Result:
        returncode = 0
        stdout = json.dumps({"status": "pass"})
        stderr = ""

    monkeypatch.setattr(
        carrier.subprocess,
        "run",
        lambda argv, **kwargs: calls.append(argv) or Result(),
    )

    order = LocalWorkOrder(
        argv=("agentic-kit", "check"),
        cwd=tmp_path,
        kind="kit",
    )

    result = carrier.inspect_kit_authority(
        order,
        kit_binary=Path("/venv/bin/agentic-kit"),
    )

    assert result.accepted is True
    assert result.is_kit_command is True
    assert "command-for" in calls[0]
