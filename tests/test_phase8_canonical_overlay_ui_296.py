from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
C=(ROOT/"chrome_extension/content.js").read_text()

def test_phase8_controls_are_absent_from_normal_overlay():
    for x in (
        'btn("Phase 7: One Round", "start", phase7RunOneRound)',
        'btn("Phase 8: Run", "start", phase8RunMultiRound)',
        'btn("Phase 8: Pause", "status", phase8Pause)',
        'btn("Phase 8: Resume", "mission", phase8Resume)',
        'btn("Phase 8: Stop", "stop", phase8Stop)',
    ):
        assert x not in C

def test_fragile_post_render_dom_patch_remains_removed():
    assert "installPhase8OperatorButtons294" not in C
    assert 'data-agp-phase8-operator="run"' not in C
