from __future__ import annotations

import json
from pathlib import Path
from typing import ClassVar

from agp_cockpit import app
from agp_cockpit.settings import AppSettings


class _FakeLogger:
    events: ClassVar[list[tuple[str, str, dict]]] = []

    def __init__(self, root: Path):
        self.root = root

    def event(self, name, *, component="bridge", details=None, **kwargs):
        self.events.append((name, component, details or {}))


def test_desktop_start_loads_settings_and_emits_structured_event(tmp_path, monkeypatch):
    _FakeLogger.events.clear()
    monkeypatch.setattr(
        "agp_cockpit.settings.load_and_migrate_settings",
        lambda path: (AppSettings(bridge_port=9876), True),
    )
    monkeypatch.setattr(
        "agp_cockpit.core.diagnostic_log.DiagnosticLogger",
        _FakeLogger,
    )
    monkeypatch.setattr(
        "agp_cockpit.app_bootstrap.run",
        lambda root, **kwargs: 0,
    )

    (tmp_path / "chrome_extension").mkdir()
    (tmp_path / ".agentic").mkdir()
    (tmp_path / ".git").mkdir()
    rc = app.main(["--repository-root", str(tmp_path)])

    assert rc == 0
    assert _FakeLogger.events == [
        (
            "DESKTOP_START",
            "desktop",
            {
                "settings_schema_version": 2,
                "settings_migrated": True,
                "repository_root_source": "explicit",
                "bridge_host": "127.0.0.1",
                "bridge_port": 9876,
            },
        )
    ]


def test_diagnose_includes_settings_check(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("platform.system", lambda: "Linux")
    rc = app.main(["--diagnose", "--repository-root", str(tmp_path)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    ids = {item["id"] for item in payload["checks"]}
    assert "settings" in ids
