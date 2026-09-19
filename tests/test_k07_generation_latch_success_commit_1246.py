from pathlib import Path

C=Path('chrome_extension/content.js').read_text()
def test_contract():
 a=C[C.index('async function maybeAutoStartTaskFirstMission()'):C.index('// AGP_K07_UNIFIED_OPERATOR_CONTROL_1005')];assert 'await startAuto();\n      return true;' in a;assert 'return false;' in a
 p=C[C.index('async function pollExplicitTaskStartRequest()'):C.index('async function refreshStatus()')];x=p.index('const started = await maybeAutoStartTaskFirstMission();');y=p.index('if (started)',x);z=p.index('AGP_TASK_FIRST_AUTOSTART_GENERATION = generation;',y);assert x<y<z
