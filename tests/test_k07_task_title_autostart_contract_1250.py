from pathlib import Path

C=Path('chrome_extension/content.js').read_text()
def test_task_e2e_and_standard_titles_are_task_first_autostart_eligible():
 a=C[C.index('async function maybeAutoStartTaskFirstMission()'):C.index('// AGP_K07_UNIFIED_OPERATOR_CONTROL_1005')]
 assert '/^(Task|E2E|Standard) · /' in a
 assert 'startsWith("Task · ")' not in a
def test_explicit_start_still_requires_identity_and_success_commit():
 p=C[C.index('async function pollExplicitTaskStartRequest()'):C.index('async function refreshStatus()')]
 assert 'status.mission.mission_id !== missionId' in p
 assert 'const started = await maybeAutoStartTaskFirstMission();' in p
 assert p.index('const started = await maybeAutoStartTaskFirstMission();') < p.index('AGP_TASK_FIRST_AUTOSTART_GENERATION = generation;')
