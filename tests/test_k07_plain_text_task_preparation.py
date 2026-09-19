from pathlib import Path

from agp_cockpit.core.task_operator_api import TaskOperatorAPI


def test_minimal_plain_text_payload_is_prepared_without_semantic_rewrite(tmp_path: Path):
    api=TaskOperatorAPI(tmp_path)
    try:
        prepared=api.prepare_task_contract({"goal":"Mein unveränderter Auftrag"})
        assert prepared["goal"]=="Mein unveränderter Auftrag"
        assert prepared["task_id"].startswith("cockpit-")
        assert prepared["repository_root"]==str(tmp_path.resolve())
        assert prepared["acceptance_criteria"]==[]
    finally: api.controller.close()
