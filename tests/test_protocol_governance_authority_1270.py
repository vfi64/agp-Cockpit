from pathlib import Path
def T(p):return Path(p).read_text()
def test_agent_protocol_first():assert "AGP_PROTOCOL_FIRST_RULE_V1" in T("AGENTS.md")
def test_authority():assert "canonical communication authority" in T("docs/planning/COMMUNICATION_PROTOCOL.md")
def test_current_divergence():assert "ACTION_NOT_AUTHORIZED_BY_LOCAL_TASK_CONTRACT" in T("docs/planning/COMMUNICATION_PROTOCOL.md")
def test_meta_lenses():
 s=T("docs/engineering/FAILURE_META_ANALYSIS.md").lower()
 for x in ["architecture","temporal","identity","authorization","idempotency","observability","regression"]:assert x in s
def test_history():assert "Generation 52" in T("docs/engineering/PROTOCOL_CHANGE_AND_FAILURE_LOG.md")
def test_existing_authorities_link():
 for f in ["docs/planning/DOCUMENT_AUTHORITY.md","docs/planning/ARCHITECTURE.md","docs/planning/MASTER_PLAN.md","docs/planning/SCOPE_BOUNDARY.md","docs/planning/PROTOCOL.md"]:assert "docs/planning/COMMUNICATION_PROTOCOL.md" in T(f)
