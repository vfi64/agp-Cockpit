from pathlib import Path


def test_task_operator_api_imports_and_initializes(tmp_path: Path) -> None:
    from agp_cockpit.core.task_operator_api import TaskOperatorAPI

    api = TaskOperatorAPI(tmp_path)
    try:
        status = api.status()
    finally:
        api.controller.close()

    assert status["repository_root"] == str(tmp_path.resolve())
