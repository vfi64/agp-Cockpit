from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_process_timeout_remains_executor_owned():
 t=(ROOT/"src/agp_cockpit/core/protocol_execution_v1.py").read_text()
 e=(ROOT/"src/agp_cockpit/core/terminal_exec.py").read_text()
 assert "execute_structured_work_order" in t and "timeout" in e.lower()
