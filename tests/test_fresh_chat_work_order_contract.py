"""Regression for live step 1568 (2026-10-02): a fresh ChatGPT chat sent a
work order without ``--self-test``; download ingress rejected it fail-fast and
the mission stopped. Now ingress checks only safety, /command corrects, and
every prompt states the structural contract."""

from pathlib import Path
from types import SimpleNamespace

from agp_cockpit.core import bridge_server
from agp_cockpit.core.command_file_contract import (
    WORK_ORDER_KIT_RULE,
    command_content_contract_violations,
)
from agp_cockpit.core.download_ingress import read_downloaded_command

ROOT = Path(__file__).resolve().parents[1]

LIVE_1568 = '''#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

STEP = 1568
ROOT = Path(".")
OUT = ROOT / "Download" / f"{STEP}_{STEP}_agp_branch_closeout_probe_return_bundle.json"

def main():
    p = subprocess.run(["agentic-kit", "work", "recover", "--json"], text=True, capture_output=True)
    OUT.write_text(json.dumps({"rc": p.returncode}) + "\\n")

if __name__ == "__main__":
    main()
'''


def test_the_live_1568_work_order_is_fetched_and_its_violation_is_correctable(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    path = download / "1568_agp_branch_closeout_probe.py"
    path.write_text(LIVE_1568, encoding="utf-8")
    assert read_downloaded_command(path, path.name, tmp_path)[1] == LIVE_1568
    violations = command_content_contract_violations(LIVE_1568)
    assert violations == ["missing --self-test contract"]
    message = "command file semantic contract rejected: " + "; ".join(violations)
    assert bridge_server._correctable(ValueError(message))


def test_the_correction_prompt_restates_the_work_order_contract(tmp_path):
    events = []
    mission = SimpleNamespace(mission_id="m-1568", state="RUNNING")
    engine = SimpleNamespace(runtime=SimpleNamespace(state=mission, final=lambda *a: None))
    diag = SimpleNamespace(event=lambda name, **kw: events.append(name))
    (tmp_path / "Download").mkdir()
    (tmp_path / "rt").mkdir()
    response = bridge_server._policy_rejection_response(
        tmp_path / "rt", tmp_path, engine, diag, filename="1568_x.py",
        reason="command file semantic contract rejected: missing --self-test contract",
        cycle_id="c1",
    )
    assert response["state"] == "CONTINUE" and response["terminal"] is False
    assert WORK_ORDER_KIT_RULE in response["prompt"]
    assert events == ["K07_WORK_ORDER_REJECTED"]


def test_the_rule_names_every_structural_check():
    for part in ("main()", "__main__", "STEP", "--self-test", "exits 0",
                 "Download/<STEP>_<topic>_return_bundle.json"):
        assert part in WORK_ORDER_KIT_RULE
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    assert WORK_ORDER_KIT_RULE in content
    ingress = (ROOT / "src/agp_cockpit/core/download_ingress.py").read_text(encoding="utf-8")
    assert "validate_command_content" not in ingress
