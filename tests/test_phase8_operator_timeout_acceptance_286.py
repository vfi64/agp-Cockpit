from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_operator_controls_are_explicit():
 t=(ROOT/"chrome_extension/content.js").read_text()
 for x in ("phase8RunMultiRound","phase8Pause","phase8Resume","phase8Stop","maximale Rundenzahl"): assert x in t
def test_browser_timeout_is_bounded_in_reused_contract():
 t=(ROOT/"chrome_extension/conversation_contract.js").read_text()
 assert "timeoutMs = 30000" in t and "PHASE5_COMPLETED_ASSISTANT_TIMEOUT" in t
def test_process_timeout_remains_executor_owned():
 t=(ROOT/"src/agp_cockpit/core/protocol_execution_v1.py").read_text()
 e=(ROOT/"src/agp_cockpit/core/terminal_exec.py").read_text()
 assert "execute_structured_work_order" in t and "timeout" in e.lower()
def test_phase8_does_not_duplicate_transport_or_executor():
 t=(ROOT/"chrome_extension/phase8_multi_round.js").read_text()
 assert "fetch(" not in t and "/v1/protocol/execute" not in t and "AGPCockpitPhase7SingleRound" in t
