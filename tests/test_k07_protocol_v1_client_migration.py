from pathlib import Path
R=Path(__file__).resolve().parents[1]
S=(R/'chrome_extension/content.js').read_text()
def test_migration():
 a=S.index('async function submitAssistant');b=S.index('async function processCompletedAssistant',a);q=S[a:b];assert '\"/v1/turn\"' not in q;assert '\"/v1/protocol/execute\"' in q;assert 'AGP_COCKPIT_ACTION_BEGIN' in q;assert 'RESULT_DELIVERED' in q
