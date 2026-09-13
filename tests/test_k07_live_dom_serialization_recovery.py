from pathlib import Path
C=Path('chrome_extension/content.js').read_text(encoding='utf-8')

def test_wired():
    assert 'AGP_K07_LIVE_DOM_SERIALIZATION_RECOVERY_758' in C
    assert 'repairRenderedJsonStringEscapes(raw)' in C
    assert 'parsePureJsonObject(repairedText)' in C
    assert 'rendered-json-escape-repair' in C
