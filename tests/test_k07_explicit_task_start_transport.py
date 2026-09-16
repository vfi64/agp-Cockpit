from pathlib import Path

from agp_cockpit.core.start_request import StartRequestStore


def test_persisted_monotonic(tmp_path):
 s=StartRequestStore(tmp_path); assert s.current()['generation']==0; assert s.request('m')['generation']==1; assert StartRequestStore(tmp_path).request('m')['generation']==2

def test_desktop_emits_after_create():
 p=Path('src/agp_cockpit/ui/simple_task_panel.py').read_text(); assert p.index('create_live_full_auto(') < p.index('request_task_start(')

def test_refresh_observational():
 c=Path('chrome_extension/content.js').read_text(); b=c[c.index('async function refreshStatus()'):c.index('async function submitAssistant(')]; assert 'maybeAutoStartTaskFirstMission' not in b and 'pollExplicitTaskStartRequest' not in b

def test_explicit_generation_contract():
 c=Path('chrome_extension/content.js').read_text(); b=c[c.index('async function pollExplicitTaskStartRequest()'):c.index('async function refreshStatus()')]; assert '/v1/task/start-request' in b and 'generation <= AGP_TASK_FIRST_AUTOSTART_GENERATION' in b and 'mission_id !== missionId' in b


def test_bridge_handler_captures_runtime_root_for_start_request_store():
    source = Path("src/agp_cockpit/core/bridge_server.py").read_text()
    assert "runtime_root = self.runtime_root" in source
    assert 'StartRequestStore(runtime_root)' in source

def test_desktop_uses_live_http_bridge_as_mission_authority():
    panel = Path("src/agp_cockpit/ui/simple_task_panel.py").read_text()
    assert "self.mission_api = OperatorAPI" not in panel
    assert "create_live_full_auto(" in panel
    assert "mission_status()" in panel
    assert 'mission_response["mission"]' in panel

def test_live_mission_create_precedes_start_request():
    panel = Path("src/agp_cockpit/ui/simple_task_panel.py").read_text()
    assert panel.index("create_live_full_auto(") < panel.index("request_task_start(")


def test_explicit_start_generation_clears_legacy_mission_latch() -> None:
    """A fresh explicit request must not be suppressed by the legacy mission latch."""
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "chrome_extension" / "content.js").read_text(
        encoding="utf-8"
    )
    poll_start = source.index("async function pollExplicitTaskStartRequest()")
    poll_end = source.index("async function refreshStatus()", poll_start)
    poll = source[poll_start:poll_end]
    clear_latch = poll.index("AGP_TASK_FIRST_AUTOSTART_MISSION_ID = null;")
    shared_start = poll.index("const started = await maybeAutoStartTaskFirstMission();", clear_latch)
    success_guard = poll.index("if (started) {", shared_start)
    generation = poll.index("AGP_TASK_FIRST_AUTOSTART_GENERATION = generation;", success_guard)
    assert clear_latch < shared_start < success_guard < generation


def test_explicit_start_request_has_independent_liveness_poller() -> None:
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "chrome_extension" / "content.js").read_text(encoding="utf-8")
    assert "let AGP_TASK_FIRST_START_REQUEST_TIMER = null;" in source
    assert "AGP_TASK_FIRST_START_REQUEST_TIMER = setInterval(" in source
    assert "void pollExplicitTaskStartRequest();" in source


def test_extension_reload_baselines_existing_start_request_generation() -> None:
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "chrome_extension" / "content.js").read_text(encoding="utf-8")
    a = source.index("async function pollExplicitTaskStartRequest()")
    b = source.index("async function refreshStatus()", a)
    poll = source[a:b]
    p1 = poll.index("if (!AGP_TASK_FIRST_START_REQUEST_PRIMED)")
    p2 = poll.index("AGP_TASK_FIRST_START_REQUEST_PRIMED = true;", p1)
    p3 = poll.index("generation <= AGP_TASK_FIRST_AUTOSTART_GENERATION", p2)
    p4 = poll.index("AGP_TASK_FIRST_AUTOSTART_MISSION_ID = null;", p3)
    p5 = poll.index("await maybeAutoStartTaskFirstMission();", p4)
    assert p1 < p2 < p3 < p4 < p5
