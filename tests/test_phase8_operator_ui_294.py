from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
C=(ROOT/"chrome_extension/content.js").read_text()
def test_phase8_operator_ui_superseded_by_canonical_binding_296():
 assert "installPhase8OperatorButtons294" not in C
