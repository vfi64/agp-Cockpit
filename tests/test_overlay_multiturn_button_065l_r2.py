from pathlib import Path

def test_multiturn_overlay_uses_existing_btn_factory():
    s = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    assert 'btn("LIVE 3-Turn", "liveprobe", newMultiTurnLiveProbeMission)' in s
    assert 'button("③ LIVE 3-Turn", "liveprobe", newMultiTurnLiveProbeMission)' not in s
