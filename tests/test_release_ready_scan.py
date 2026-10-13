"""KIT-GF-068 (2026-10-13): the Kit's ./ns legacy-reference audit runs inside `release ready` (step A2 of
the release run) and blocked release 0.2.5 on one line of the Cockpit's own findings ledger. The ledger
quotes Kit findings; every such quote must classify as historical/evidence for the Kit's audit."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_the_findings_ledger_passes_the_kits_legacy_reference_audit():
    audit = pytest.importorskip("agentic_project_kit.ns_legacy_reference_audit")
    rel = "docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json"
    lines = (ROOT / rel).read_text(encoding="utf-8").splitlines()
    blocking = [(number, line.strip()[:120]) for number, line in enumerate(lines, 1)
                if audit._has_legacy_reference(line)
                and audit.classify_legacy_reference(rel, line)[0] in {"needs_review", "current_instruction_blocker"}]
    assert blocking == [], blocking


def test_the_whole_repository_passes_the_kits_legacy_reference_audit():
    """The same audit over every tracked file, as `release ready` runs it."""
    audit = pytest.importorskip("agentic_project_kit.ns_legacy_reference_audit")
    result = audit.audit_ns_legacy_references(ROOT)
    assert result.ok, audit.render_ns_legacy_reference_audit(result)[-1500:]
