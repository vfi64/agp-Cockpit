from pathlib import Path


def test_simple_surface_exposes_contextual_human_release():
    s=Path("src/agp_cockpit/ui/simple_task_panel.py").read_text()
    assert 'text="Entscheidung freigeben"' in s
    assert 'status.get("suspension_reason") == "WAITING_FOR_HUMAN"' in s
    assert "self.api.approve_checkpoint()" in s
    assert 'state="normal" if waiting_for_human else "disabled"' in s

def test_file_loop_ingress_honors_durable_human_wait():
    s=Path("src/agp_cockpit/core/bridge_server.py").read_text()
    start=s.index('if path == "/v1/file-loop/command":')
    end=s.index('if path == "/v1/protocol/action":',start)
    block=s[start:end]
    assert 'current_task_id = str(current_start.get("task_id") or "").strip()' in block
    assert 'durable.snapshot.get("suspension_reason") == "WAITING_FOR_HUMAN"' in block
    assert 'raise RuntimeError("WAITING_FOR_HUMAN")' in block
    assert block.index("WAITING_FOR_HUMAN") < block.index("consume_command_file(")
