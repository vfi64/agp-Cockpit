from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BG=(ROOT/"chrome_extension/background.js").read_text()
def test_order():
 fn=BG[BG.index("async function agpSubmitFileLoopContinuation"):]
 assert fn.index("attachResultFiles") < fn.index("chrome.tabs.sendMessage(tabId")
def test_no_json_payload():
 fn=BG[BG.index("async function agpSubmitFileLoopContinuation"):]
 assert "JSON.stringify" not in fn and "Attached is the result file" in fn
def test_fail_loud_confirmation():
 fn=BG[BG.index("async function agpAttachFileLoopResultBundle"):]
 assert 'stage !== "RESULT_FILE_ATTACHED"' in fn
