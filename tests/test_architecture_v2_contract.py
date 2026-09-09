from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")

def test_v2_scope_establishes_remote_reasoning_and_deterministic_controller():
    scope = read("docs/planning/SCOPE_BOUNDARY.md")
    assert "Remote Development LLM owns development reasoning" in scope
    assert "Cockpit\nowns deterministic task orchestration" in scope
    assert "Agentic Project Kit owns governed repository" in scope

def test_v2_scope_separates_failure_from_task_termination():
    scope = read("docs/planning/SCOPE_BOUNDARY.md")
    assert "A local execution failure is evidence" in scope
    assert "not by itself a\ntask failure" in scope

def test_v2_contract_contains_authority_effect_and_unknown_outcome_rules():
    scope = read("docs/planning/SCOPE_BOUNDARY.md")
    architecture = read("docs/planning/ARCHITECTURE.md")
    assert all(x in scope for x in ("D0", "D1", "D2", "E0", "E4"))
    assert "OUTCOME_UNKNOWN" in architecture
    assert "blind replay" in scope.lower()

def test_protocol_v1_is_not_silently_redefined():
    protocol = read("docs/planning/PROTOCOL.md")
    assert "V1 remains frozen for legacy sessions" in protocol
    assert "protocol version 2" in protocol
    assert "must not be silently injected into V1 frames" in protocol

def test_completion_requires_verification_not_remote_claim():
    scope = read("docs/planning/SCOPE_BOUNDARY.md")
    architecture = read("docs/planning/ARCHITECTURE.md")
    assert "COMPLETE_PROPOSAL" in scope
    assert "VERIFIED_COMPLETE" in scope
    assert "COMPLETE_REJECTED" in architecture

def test_kit_governance_remains_authoritative():
    scope = read("docs/planning/SCOPE_BOUNDARY.md")
    assert "Kit remains authoritative" in scope
    assert "unauthorized bypass" in scope

def test_local_llm_is_not_in_critical_path():
    scope = read("docs/planning/SCOPE_BOUNDARY.md")
    assert "outside the critical correctness path" in scope
    assert "may not alter policy" in scope

def test_master_plan_orders_architecture_gate_before_s2_runtime():
    plan = read("docs/planning/MASTER_PLAN.md")
    assert "Phase 12 / S1" in plan
    assert "No S2 runtime\nbehavior before this gate" in plan
    assert "Phase 13 / S2" in plan

def test_status_no_longer_claims_phase6_active():
    status = read(".agentic/state/status.md")
    assert "Phase 12 / S1" in status
    assert "Current continuation — Phase 6" not in status

def test_adr_0003_is_accepted():
    adr = read("docs/architecture/ADR-0003-persistent-remote-llm-task-runtime.md")
    assert "Status: Accepted" in adr
    assert "Local execution failure is evidence" in adr
