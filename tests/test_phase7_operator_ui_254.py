from pathlib import Path
R=Path(__file__).resolve().parents[1]
C=(R/'chrome_extension/content.js').read_text(); P=(R/'chrome_extension/phase7_single_round.js').read_text()
def test_atomic_ui():
 assert C.count('AGP_PHASE7_SINGLE_ROUND_UI_254')==1
 assert C.count('btn(\"Phase 7: One Round\", \"start\", phase7RunOneRound)')==0
 assert 'ctl.runOneRound()' in C
 assert 'get({token:\"\", baseUrl:\"http://127.0.0.1:9876\"})' in P
 assert 'bridgeBaseUrl' not in P and 'bridgeToken' not in P
