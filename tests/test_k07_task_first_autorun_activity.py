from pathlib import Path
MISSION_CLIENT = Path("src/agp_cockpit/core/mission_http_client.py").read_text()

ROOT=Path(__file__).resolve().parents[1]
PANEL=(ROOT/"src/agp_cockpit/ui/simple_task_panel.py").read_text()
CONTENT=(ROOT/"chrome_extension/content.js").read_text()

def test_task_start_creates_live_full_auto_browser_mission():
    assert "create_live_full_auto" in PANEL
    assert "create_live_full_auto(" in PANEL
    assert '"LIVE"' in MISSION_CLIENT
    assert '"FULL_AUTO"' in MISSION_CLIENT
    assert '"Task · "' in PANEL

def test_task_first_browser_mission_autostarts_without_affecting_generic_expert_missions():
    assert "async function maybeAutoStartTaskFirstMission" in CONTENT
    assert '/^(Task|E2E) · /' in CONTENT
    assert 'mission.execution_mode !== "LIVE"' in CONTENT
    assert 'mission.run_mode !== "FULL_AUTO"' in CONTENT
    assert "AGP_TASK_FIRST_AUTOSTART_MISSION_ID" in CONTENT

def test_normal_surface_reports_only_observed_browser_activity():
    assert "Browser-Mission arbeitet" in PANEL
    assert "wartet auf den ersten Remote-Turn" in PANEL
    assert "turn_count" in PANEL and "step_count" in PANEL


def test_status_refresh_does_not_autostart_persisted_task():
    source = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    refresh = source[source.index("async function refreshStatus()"):source.index("async function submitAssistant(")]
    assert "maybeAutoStartTaskFirstMission()" not in refresh
    assert "status refresh is observational only" in refresh

def test_result_prompt_must_leave_composer_before_next_turn_is_claimed():
    source = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    process = source[source.index("async function processCompletedAssistant("):source.index("async function tick()")]
    assert "await sendPrompt(result.prompt);" in process
    assert "result prompt remained in composer after send acknowledgement" in process
    assert process.index("await sendPrompt(result.prompt);") < process.index("STATE.waitingForAssistant = true;")
