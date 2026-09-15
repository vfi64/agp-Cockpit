from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIMPLE = (ROOT / "src/agp_cockpit/ui/simple_task_panel.py").read_text()
API = (ROOT / "src/agp_cockpit/core/task_operator_api.py").read_text()
MAIN = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text()


def test_default_surface_is_task_first():
    assert "SimpleTaskPanel(" in MAIN
    assert 'text="Auftrag laden"' in SIMPLE
    assert 'text="Auftrag prüfen"' not in SIMPLE
    assert 'text="Task starten"' in SIMPLE


def test_normal_gui_has_no_expert_notebook_surface():
    assert "ttk.Notebook" not in MAIN
    assert 'Expert · System' not in MAIN
    assert 'Expert · Einzelauftrag' not in MAIN
    assert 'Expert · Task Operator' not in MAIN
    assert "SimpleTaskPanel(" in MAIN

def test_high_level_contract_is_persisted_without_contract_defined_authority_escalation():
    assert "validate_task_contract" in API
    assert "start_task_from_contract" in API
    body = API.split("def start_task_from_contract", 1)[1]
    assert "set_runtime_contract" in body
    assert "load_and_migrate_settings" in body
    assert "allowed_effects=settings.allowed_effects" in body
    assert "allowed_tools=settings.allowed_tools" in body


def test_simple_surface_explains_human_only_interruptions():
    assert "strategischen oder ausdrücklich menschlichen" in SIMPLE
    assert "Nur hier soll der Nutzer wieder gefragt werden" in SIMPLE

def test_plain_text_load_is_immediately_startable_and_validation_is_automatic():
    assert 'self.workflow_phase = "EMPTY"' in SIMPLE
    assert 'self.workflow_phase = "LOADED"' in SIMPLE
    assert 'self.workflow_phase = "STARTED"' in SIMPLE
    assert 'self.start_button.configure(state="normal")' in SIMPLE
    assert "Auftrag geladen ✓ — bereit zum Starten." in SIMPLE
    assert "self.api.prepare_task_contract(self.contract)" in SIMPLE
    assert 'text="Auftrag prüfen"' not in SIMPLE

def test_internal_runtime_states_are_translated_for_normal_user():
    assert "Du musst momentan nichts tun" in SIMPLE
    assert "Auftrag abgeschlossen ✓" in SIMPLE
    assert "Deine Entscheidung ist erforderlich" in SIMPLE
    assert "Arbeitet / wartet auf Automatik — Zustand:" not in SIMPLE


def test_task_loader_prefers_plain_text():
    assert 'title="Auftrag auswählen"' in SIMPLE
    assert '("Textaufträge", "*.txt")' in SIMPLE
    assert '("JSON-Aufträge", "*.json")' in SIMPLE
    assert 'source.suffix.lower() == ".json"' in SIMPLE
    assert '{"goal": raw.strip()}' in SIMPLE
