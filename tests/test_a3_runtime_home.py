"""Slice A3 (AGP_RUNTIME_HOME_V1): the Cockpit's runtime of a steered repository lives in the
Cockpit's own checkout (live 2026-10-06: the Kit repository received bridge log, missions,
digest, delivery copies and work-order temp files, which its audits scanned — KIT-GF-054)."""
from pathlib import Path

import pytest

from agp_cockpit.core import runtime_paths as rp

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def home(tmp_path, monkeypatch):
    home = tmp_path / "cockpit"
    home.mkdir()
    monkeypatch.setenv(rp.HOME_ENV, str(home))
    return home


def test_without_a_home_the_repository_keeps_its_own_folder(tmp_path, monkeypatch):
    monkeypatch.delenv(rp.HOME_ENV, raising=False)
    assert rp.runtime_dir(tmp_path, "logs") == tmp_path.resolve() / ".local/agp-cockpit/logs"


def test_the_cockpits_own_repository_keeps_its_folder(home):
    assert rp.runtime_base(home) == home.resolve() / ".local/agp-cockpit"


def test_a_steered_repository_gets_its_own_folder_in_the_home(home, tmp_path):
    kit = tmp_path / "agentic-project-kit"
    kit.mkdir()
    base = rp.runtime_base(kit)
    assert base.parent == home.resolve() / ".local/agp-cockpit/repos"
    assert base.name.startswith("agentic-project-kit-") and len(base.name) == len("agentic-project-kit-") + 8
    other = tmp_path / "x" / "agentic-project-kit"
    other.mkdir(parents=True)
    assert rp.runtime_base(other) != base             # same name, different repository


def test_bridge_log_missions_refresh_delivery_and_tmp_follow_the_home(home, tmp_path):
    from agp_cockpit.core.browser_refresh import (
        refresh_request_path,
        request_browser_refresh,
    )
    from agp_cockpit.core.diagnostic_log import DiagnosticLogger
    from agp_cockpit.core.mission_state import MissionStore
    from agp_cockpit.core.result_projection import delivery_files
    kit = tmp_path / "kit"
    (kit / "Download").mkdir(parents=True)
    base = rp.runtime_base(kit)
    DiagnosticLogger(kit).event("TEST", component="test")
    assert (base / "logs/bridge.log").is_file()
    assert MissionStore(kit).root == base / "missions"
    request_browser_refresh(kit, reason="test")
    assert refresh_request_path(kit) == base / "browser/refresh_request.json" and refresh_request_path(kit).is_file()
    result = kit / "Download" / "1_x_return_bundle.json"
    result.write_text('{"status": "PASS"}', encoding="utf-8")
    log = kit / "Download" / "1_run_next_output.txt"
    log.write_text("log\n", encoding="utf-8")
    assert Path(delivery_files(kit, result, log)["result_file"]).parent == base / "delivery"
    assert not (kit / ".local").exists()                 # nothing of the Cockpit in the steered repository
    runner = (ROOT / "src/agp_cockpit/core/file_loop_runner.py").read_text(encoding="utf-8")
    assert 'runtime_dir(root.resolve(), "tmp", str(step))' in runner


def test_the_app_announces_its_home_before_the_first_log_line():
    app = (ROOT / "src/agp_cockpit/app.py").read_text(encoding="utf-8")
    assert app.index("announce_home(root)") < app.index("log = DiagnosticLogger(root)")


def test_cleanup_offers_the_runtime_left_in_a_steered_repository(home, tmp_path):
    from agp_cockpit.core import maintenance
    kit = tmp_path / "kit"
    legacy = kit / ".local" / "agp-cockpit" / "logs"
    legacy.mkdir(parents=True)
    (legacy / "bridge.log").write_text("x" * 100, encoding="utf-8")
    planned = maintenance.plan(kit)
    old = [c for c in planned.candidates if c.area == "Alte Cockpit-Laufzeit im Repository"]
    assert [c.path for c in old] == [kit.resolve() / ".local/agp-cockpit"] and old[0].bytes == 100
    result = maintenance.execute(kit, planned)
    assert result["deleted"] == 1 and not (kit / ".local/agp-cockpit").exists()
