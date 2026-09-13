from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIMPLE = (ROOT / "src/agp_cockpit/ui/simple_task_panel.py").read_text()
API = (ROOT / "src/agp_cockpit/core/task_operator_api.py").read_text()
MAIN = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text()


def test_default_surface_is_task_first():
    assert 'text="Arbeiten"' in MAIN
    assert "SimpleTaskPanel(" in MAIN
    assert 'text="Auftrag laden"' in SIMPLE
    assert 'text="Auftrag prüfen"' in SIMPLE
    assert 'text="Task starten"' in SIMPLE


def test_expert_gui_is_preserved_as_secondary_tabs():
    assert 'text="Expert · System"' in MAIN
    assert 'text="Expert · Einzelauftrag"' in MAIN
    assert 'text="Expert · Task Operator"' in MAIN
    assert "WorkOrderPanel(" in MAIN
    assert "TaskOperatorPanel(" in MAIN


def test_high_level_contract_is_persisted_without_granting_new_authority():
    assert "validate_task_contract" in API
    assert "start_task_from_contract" in API
    body = API.split("def start_task_from_contract", 1)[1]
    assert "set_runtime_contract" in body
    assert "set_task_authority(" not in body


def test_simple_surface_explains_human_only_interruptions():
    assert "strategischen oder ausdrücklich menschlichen" in SIMPLE
    assert "Nur hier soll der Nutzer wieder gefragt werden" in SIMPLE

def test_validation_feedback_survives_pre_start_refresh():
    assert 'self.workflow_phase = "EMPTY"' in SIMPLE
    assert 'self.workflow_phase = "LOADED"' in SIMPLE
    assert 'self.workflow_phase = "VALIDATED"' in SIMPLE
    assert 'self.workflow_phase = "STARTED"' in SIMPLE
    assert "Auftrag geprüft ✓" in SIMPLE
    assert 'if self.workflow_phase != "STARTED"' in SIMPLE

def test_internal_runtime_states_are_translated_for_normal_user():
    assert "Du musst momentan nichts tun" in SIMPLE
    assert "Auftrag abgeschlossen ✓" in SIMPLE
    assert "Deine Entscheidung ist erforderlich" in SIMPLE
    assert "Arbeitet / wartet auf Automatik — Zustand:" not in SIMPLE
