from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
C=(ROOT/"chrome_extension/content.js").read_text()
def test_phase8_buttons_are_part_of_canonical_render():
 assert "AGP_PHASE8_CANONICAL_OVERLAY_UI_296" in C
 p7=C.index('btn("P7 One Round", "start", phase7RunOneRound)')
 p8=C.index('btn("P8 Run", "start", phase8RunMultiRound)')
 root=C.index("root.appendChild(actions)",p7)
 assert p7 < p8 < root
def test_all_phase8_controls_use_canonical_btn_factory():
 for x in ('btn("P8 Run", "start", phase8RunMultiRound)','btn("P8 Pause", "status", phase8Pause)','btn("P8 Resume", "mission", phase8Resume)','btn("P8 Stop", "stop", phase8Stop)'): assert x in C
def test_fragile_post_render_dom_patch_removed():
 assert "installPhase8OperatorButtons294" not in C
 assert 'data-agp-phase8-operator="run"' not in C
