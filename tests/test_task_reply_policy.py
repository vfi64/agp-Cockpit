"""AGP_TASK_REPLY_POLICY_V1: task definition, reply policy and transport are
separate; a locally verified task is never offered a remote DONE."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agp_cockpit.core.file_loop_orchestrator import consume_command_file
from agp_cockpit.core.standard_tasks import standard_tasks
from agp_cockpit.core.task_reply_policy import (
    GENERIC,
    LOCALLY_VERIFIED,
    policy_for,
    terminal_reply_instruction,
)

ROOT = Path(__file__).resolve().parents[1]
OFFERS_DONE = '"DONE" or'


def valid_command() -> str:
    return (
        "import argparse\nfrom pathlib import Path\n"
        'COMMAND = ["agentic-kit", "x"]\nRETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n    parser = argparse.ArgumentParser()\n"
        '    parser.add_argument("--self-test", action="store_true")\n    parser.parse_args()\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n    main()\n'
    )


def test_policy_follows_completion_contract():
    assert policy_for(True) is LOCALLY_VERIFIED and not LOCALLY_VERIFIED.remote_done_allowed
    assert policy_for(False) is GENERIC and GENERIC.remote_done_allowed


def test_instruction_offers_done_only_to_generic_missions():
    assert OFFERS_DONE in terminal_reply_instruction(1483, GENERIC)
    verified = terminal_reply_instruction(1483, LOCALLY_VERIFIED)
    assert OFFERS_DONE not in verified
    assert "never declare it DONE" in verified
    assert '1483_agp_terminal.json' in verified and '"NEEDS_HUMAN"' in verified


@pytest.mark.parametrize(("policy", "offers_done"), [(GENERIC, True), (LOCALLY_VERIFIED, False)])
def test_orchestrator_continuation_applies_the_policy(tmp_path, policy, offers_done):
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text(
        "import sys\nfrom pathlib import Path\nn=int(sys.argv[1]);d=Path(__file__).parent\n"
        "(d/f'{n:03d}_x_return_bundle.json').write_text('{}')\n"
    )
    incoming = tmp_path / "incoming.py"
    incoming.write_text(valid_command())
    outcome = consume_command_file(incoming, tmp_path, tmp_path / "state.json", reply_policy=policy)
    assert (OFFERS_DONE in outcome.continuation_text) is offers_done
    assert "_agp_terminal.json" in outcome.continuation_text


def test_chat_switch_task_demands_a_fresh_run_on_every_start():
    prompt = standard_tasks()[0].prompt(ROOT)
    assert "Every start of this task requires a fresh local run" in prompt
    assert "an earlier result never completes a new start" in prompt


def test_bootstrap_never_offers_remote_done():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required")
    script = r"""
const fs = require("fs"), vm = require("vm");
const src = fs.readFileSync("chrome_extension/content.js", "utf8");
const start = src.indexOf("  function missionBootstrapPrompt(mission)");
const end = src.indexOf("  async function maybeAutoStartTaskFirstMission()", start);
const ctx = {STATE:{nextLocalStep:1480, mission:{execution_mode:"LIVE"}, localAuthority:{}}, JSON};
vm.createContext(ctx);
vm.runInContext(src.slice(start, end) + "; globalThis.out = missionBootstrapPrompt({mission_text:'X'});", ctx);
process.stdout.write(JSON.stringify(ctx.out));
"""
    result = subprocess.run([node, "-e", script], cwd=ROOT, capture_output=True, text=True, check=True)
    bootstrap = json.loads(result.stdout)
    assert "1480_agp_terminal.json" in bootstrap
    assert OFFERS_DONE not in bootstrap
    assert "earlier results in this conversation do not complete it" in bootstrap
