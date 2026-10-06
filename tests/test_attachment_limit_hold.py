"""AGP_ATTACHMENT_LIMIT_HOLD_V1 (live 2026-10-06, Kit slice GF-050 B, step 63).

ChatGPT refused the result upload ("Du hast das Limit für Dateianhänge erreicht ·
Erneut versuchen 6. Okt., 19:49"); three immediate retries ended the task STOPPED.
Now the loop holds until the named time and re-delivers the kept result.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agp_cockpit.core.standard_task_progress import describe_standard_task_progress

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
LIVE_ERROR = (
    'Error: ChatGPT composer did not show the selected result evidence files: '
    '{"expected":["063_gf050b_origin_diff_scope_return_bundle.json","63_run_next_output.txt"],'
    '"before":{"composer_found":true,"composer_sample":["Du hast das Limit für Dateianhänge erreicht",'
    '"Erneut versuchen 6. Okt., 19:49","063_gf'
)


def _retry_at(message: str, now: list[int]) -> int:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    start = CONTENT.index("  const ATTACHMENT_LIMIT_PATTERN")
    end = CONTENT.index("  async function holdForAttachmentLimit")
    script = (
        "process.env.TZ='Europe/Berlin';"
        f"const f=new Function({json.dumps(CONTENT[start:end] + '; return attachmentLimitRetryAt;')})();"
        f"const n=new Date({now[0]},{now[1]},{now[2]},{now[3]},{now[4]}).getTime();"
        f"const at=f({json.dumps(message)},n);"
        "console.log(at===0?0:Math.round((at-n)/60000));"
    )
    done = subprocess.run([node, "-e", script], capture_output=True, text=True, check=True)
    return int(done.stdout.strip())


def test_the_live_limit_message_holds_until_one_minute_after_the_named_time():
    assert _retry_at(LIVE_ERROR, [2026, 9, 6, 18, 2]) == 108          # 18:02 -> 19:50
    assert _retry_at(LIVE_ERROR, [2026, 9, 6, 19, 55]) == 1           # just passed: retry soon
    assert _retry_at(LIVE_ERROR.replace("19:49", "00:30"), [2026, 9, 6, 23, 50]) == 41   # after midnight


def test_other_errors_do_not_hold_and_an_unnamed_time_waits_fifteen_minutes():
    assert _retry_at("ChatGPT composer not clean", [2026, 9, 6, 18, 0]) == 0
    assert _retry_at("You have reached the file upload limit.", [2026, 9, 6, 18, 0]) == 15
    assert _retry_at("upload limit. Try again at 7:49 PM", [2026, 9, 6, 18, 0]) == 110


def test_the_tick_holds_instead_of_counting_an_error_and_retries_afterwards():
    catch = CONTENT.index("if (await holdForAttachmentLimit(err, runGeneration)) return;")
    assert catch < CONTENT.index("STATE.errors += 1;", catch)
    gate = CONTENT.index("if (STATE.running && STATE.transportHoldUntil) {")
    assert CONTENT.index("if (STATE.paused) return;") < gate < CONTENT.index("await pollExplicitTaskStartRequest();", gate)
    assert 'clientEvent("K07_ATTACHMENT_LIMIT_RETRY"' in CONTENT
    stop = CONTENT[CONTENT.index("async function stop("):]
    assert stop.index("STATE.transportHoldUntil = 0;") < stop.index("STATE.timer = null;")
    hold = CONTENT[CONTENT.index("async function holdForAttachmentLimit"):]
    assert "STATE.assistantWaitStartedAt = 0;" in hold[:1200]      # no answer timeout while holding


def test_the_bridge_records_the_hold_without_blocking_and_the_lage_says_wartet(tmp_path):
    from agp_cockpit.core.bridge_runtime import BridgeRuntime
    runtime = BridgeRuntime(tmp_path)
    mission = runtime.create_mission(title="x", mission_text="y", execution_mode="LIVE", run_mode="FULL_AUTO")
    note = "ChatGPT-Anhangslimit erreicht — das Ergebnis bleibt lokal gespeichert; erneuter Versand automatisch um 19:50."
    assert runtime.record_browser_transport("K07_ATTACHMENT_LIMIT_HOLD",
                                            {"mission_id": mission.mission_id, "reason": note})
    assert runtime.state.browser_transport_blocked is False
    payload = {"mission": {"mission_id": "m", "state": "RUNNING", "turn_count": 13, "step_count": 13,
                           "browser_transport_event": "K07_ATTACHMENT_LIMIT_HOLD",
                           "browser_transport_note": note}}
    progress = describe_standard_task_progress(mission_id="m", task_status={"state": "RUNNING"},
                                               bridge_status=payload)
    assert progress.text.startswith("Wartet — ChatGPT-Anhangslimit") and not progress.terminal
    assert "19:50" in progress.text


def test_the_mission_start_asks_for_few_combined_work_orders():
    assert "Every turn costs one file upload and ChatGPT limits uploads" in CONTENT


def test_the_actual_tick_holds_and_redelivers_the_same_command_file():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node required for actual content-script behavior test")
    done = subprocess.run([node, str(ROOT / "tests/attachment_limit_hold.cjs")], cwd=ROOT,
                          capture_output=True, text=True, timeout=20, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
