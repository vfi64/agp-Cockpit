from __future__ import annotations

import json
from pathlib import Path

import pytest

from agp_cockpit import __version__, app
from agp_cockpit.first_run_diagnostics import run_first_run_diagnostics


def test_cli_help_is_non_gui_and_fast(capsys):
    with pytest.raises(SystemExit) as exc:
        app.main(['--help'])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert 'AGP Cockpit' in out
    assert '--diagnose' in out


def test_cli_version_is_non_gui(capsys):
    with pytest.raises(SystemExit) as exc:
        app.main(['--version'])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_module_entrypoint_delegates_to_app_main():
    text = Path('src/agp_cockpit/__main__.py').read_text(encoding='utf-8')
    assert 'from agp_cockpit.app import main' in text
    assert 'app_bootstrap' not in text


def test_first_run_diagnostics_are_structured(tmp_path, monkeypatch):
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    report = run_first_run_diagnostics(tmp_path)
    assert report['schema'] == 'agp-cockpit.first-run-diagnostics.v1'
    assert report['schema_version'] == 1
    assert report['application_version'] == __version__
    assert report['overall'] in {'PASS', 'WARN'}
    ids = {check['id'] for check in report['checks']}
    assert {
        'python-version', 'platform', 'chrome', 'context-root',
        'local-state', 'browser-extension-assets',
    } <= ids


def test_diagnose_cli_outputs_json_without_gui(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr('platform.system', lambda: 'Linux')
    rc = app.main(['--diagnose', '--repository-root', str(tmp_path)])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload['schema'] == 'agp-cockpit.first-run-diagnostics.v1'
    assert payload['application'] == 'agp-cockpit'
