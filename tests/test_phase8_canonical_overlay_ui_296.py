from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
C=(ROOT/"chrome_extension/content.js").read_text()
def test_phase8_buttons_are_part_of_canonical_render():
 p7=C.index('btn("Phase 7: One Round", "start", phase7RunOneRound)')
 p8=C.index('btn("Phase 8: Run", "start", phase8RunMultiRound)')
 diag=C.index('diagnostics.id = "agp-cockpit-diagnostics"')
 assert diag < p7 < p8
def test_all_phase8_controls_use_canonical_btn_factory():
 for x in ('btn("Phase 8: Run", "start", phase8RunMultiRound)','btn("Phase 8: Pause", "status", phase8Pause)','btn("Phase 8: Resume", "mission", phase8Resume)','btn("Phase 8: Stop", "stop", phase8Stop)'): assert x in C
def test_fragile_post_render_dom_patch_removed():
 assert "installPhase8OperatorButtons294" not in C
 assert 'data-agp-phase8-operator="run"' not in C
