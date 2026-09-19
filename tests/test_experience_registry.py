import json
from pathlib import Path

R=Path(__file__).resolve().parents[1]; B=R/'docs/experience'
def j(p): return json.loads(p.read_text())
def test_registry():
 g=j(B/'registry.json'); assert g['authority']=='ADVISORY_ONLY'
 for x in g['records']:
  q=j(R/x['path']); assert q['experience_id']==x['experience_id']; assert q['evidence']; assert q['verification']['required_checks']
def test_k07_start_invariants():
 q=j(B/'records/EXP-browser-explicit-start-001.json'); c=set(q['verification']['required_checks']); assert 'reconnect_without_explicit_task_start_does_not_start' in c; assert 'explicit_desktop_task_start_starts_exactly_once' in c; assert 'passive_reconnect_autostart' in q['lesson']['forbidden_regressions']
