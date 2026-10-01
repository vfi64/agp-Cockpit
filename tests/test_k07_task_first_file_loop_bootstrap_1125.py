from pathlib import Path

C=(Path(__file__).resolve().parents[1]/"chrome_extension/content.js").read_text()
def test_bootstrap():
 a=C.index("function missionBootstrapPrompt"); b=C.index("async function maybeAutoStartTaskFirstMission",a); x=C[a:b]
 assert "exactly ONE executable Python command file as a .py attachment" in x
 assert "The local bridge is the numbering authority for this run." in x
 assert "The next local work-order number is" in x
 assert "Do not return Protocol-v1 JSON" in x
 assert "Return exactly ONE bounded work order as a single JSON object." not in x
def test_order():
 assert C.index("const k07CommandFiles = assistantPythonAttachmentCandidates();") < C.index("const pureStructured = parsePureJsonObject(completed);")
def test_legacy_retained():
 assert "FORMAT REPAIR ONLY" in C and "/v1/protocol/execute" in C

def test_long_chat_baseline_excludes_all_previous_assistant_messages():
 assert "assistantBaselineMessageIds" in C
 assert "captureAssistantBaseline" in C
 assert "const baselineIds = assistantBaselineIds()" in C
 assert "!baselineIds.has(id)" in C

def test_attachment_name_detection_tolerates_ui_label_suffixes_without_relaxing_type():
 assert r'/\.py(?:$|[?#\s])/i.test(item.name || "")' in C
 assert r'/\.py(?:$|[?#])/i.test(item.href || "")' in C

def test_attachment_number_must_match_local_next_step():
    assert "nextLocalStep: 0" in C
    assert "STATE.nextLocalStep = Number(result.next_local_step || 0);" in C
    assert "const expectedStep = Number(STATE.nextLocalStep || 0);" in C
    assert "Number(match[1]) === expectedStep" in C
    assert "stalePythonAttachment" in C
    assert "Number(match[1]) !== expectedStep" in C
    assert r"label.match(/(?:^|[\s/])(\d+)_" in C
