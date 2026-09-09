from pathlib import Path

DOC=Path("docs/planning/LOCAL_LLM_OBSERVATION_VALUE_GATE.md")
SCOPE=Path("docs/planning/SCOPE_BOUNDARY.md")
MASTER=Path("docs/planning/MASTER_PLAN.md")
PLAN=Path("docs/planning/TEST_PLAN.md")

def text(p): return p.read_text()
def normalized(p): return " ".join(text(p).split())

def test_t28_local_model_is_e0_untrusted_and_has_no_decision_or_effect_authority():
    d=normalized(DOC)
    assert "untrusted E0 evidence" in d
    for forbidden in ("work orders/actions","capability/effect policy","authorize Kit recovery",
                      "approve a human checkpoint","propose or verify completion","mutate repository"):
        assert forbidden in d
    assert "D1 Remote Development LLM authority" in d

def test_value_gate_defaults_to_no_admit_and_requires_reproducible_controlled_comparison():
    d=normalized(DOC)
    assert "`DO_NOT_ADMIT`" in d and "`ADMIT_OBSERVATION_ONLY`" in d
    assert "deterministic baseline only" in d
    assert "at least three repeated trials" in d
    assert "fabricated/unsupported critical facts = 0" in d
    assert "critical-fact recall = 100%" in d

def test_local_model_failure_must_fall_back_without_task_state_change():
    d=normalized(DOC)
    assert "falls back to the deterministic baseline without task-state change" in d
    assert "Raw deterministic evidence remains authoritative and auditable" in d

def test_normative_sources_keep_optional_noncritical_boundary():
    assert "outside the critical correctness path" in normalized(SCOPE)
    assert "controlled comparison shows reproducible benefit" in normalized(MASTER)
    assert "optional local model cannot alter policy/work-order/gate/completion" in normalized(PLAN)
