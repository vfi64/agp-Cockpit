from pathlib import Path
from types import SimpleNamespace

import agp_cockpit.core.bridge_execution as execution


def test_bridge_execution_reuses_existing_layer(monkeypatch, tmp_path):
    fake_order = SimpleNamespace(
        argv=("/usr/bin/printf", "x"),
        cwd=tmp_path,
        kind="generic",
        label="demo",
    )

    fake_result = SimpleNamespace(
        returncode=0,
        timed_out=False,
        stdout="x",
        stderr="",
        argv=fake_order.argv,
        cwd=tmp_path,
    )
    fake_run = SimpleNamespace(
        result=fake_result,
        result_block="RESULT",
    )
    fake_preview = SimpleNamespace(
        preview_text="PREVIEW"
    )

    monkeypatch.setattr(
        execution,
        "parse_work_order_json",
        lambda text: fake_order,
    )
    monkeypatch.setattr(
        execution,
        "_construct_policy",
        lambda root, **authority: object(),
    )
    monkeypatch.setattr(
        execution,
        "preview_work_order",
        lambda *args, **kwargs: fake_preview,
    )
    monkeypatch.setattr(
        execution,
        "execute_work_order",
        lambda *args, **kwargs: fake_run,
    )

    step = execution.execute_structured_work_order(
        "{}",
        repository_root=tmp_path,
        kit_binary=tmp_path / ".venv/bin/agentic-kit",
    )

    assert step.returncode == 0
    assert step.result_block == "RESULT"
    assert step.stdout == "x"


def test_bridge_rejects_cwd_escape(monkeypatch, tmp_path):
    fake_order = SimpleNamespace(
        argv=("/usr/bin/printf", "x"),
        cwd=Path("/tmp"),
        kind="generic",
        label="escape",
    )

    monkeypatch.setattr(
        execution,
        "parse_work_order_json",
        lambda text: fake_order,
    )

    try:
        execution.execute_structured_work_order(
            "{}",
            repository_root=tmp_path,
            kit_binary=tmp_path / ".venv/bin/agentic-kit",
        )
    except PermissionError:
        pass
    else:
        raise AssertionError("cwd escape was not rejected")
