from pathlib import Path
C=(Path(__file__).resolve().parents[1]/"chrome_extension/content.js").read_text()
def test_bootstrap():
 a=C.index("function missionBootstrapPrompt"); b=C.index("async function maybeAutoStartTaskFirstMission",a); x=C[a:b]
 assert "exactly ONE executable Python command file as a .py attachment" in x
 assert "Do not return Protocol-v1 JSON" in x
 assert "Return exactly ONE bounded work order as a single JSON object." not in x
def test_order():
 assert C.index("const k07CommandFiles = assistantPythonAttachmentCandidates();") < C.index("const pureStructured = parsePureJsonObject(completed);")
def test_legacy_retained():
 assert "FORMAT REPAIR ONLY" in C and "/v1/protocol/execute" in C
