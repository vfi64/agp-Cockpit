from pathlib import Path


def test_multiturn_probe_is_not_exposed_as_normal_overlay_button():
    s = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    assert 'btn("LIVE 3-Turn", "liveprobe", newMultiTurnLiveProbeMission)' not in s
    assert "newMultiTurnLiveProbeMission" in s
