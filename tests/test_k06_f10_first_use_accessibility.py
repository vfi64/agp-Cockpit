import inspect
import agp_cockpit.core.task_operator_api as api
from agp_cockpit.ui.task_operator_panel import TaskOperatorPanel
def test_durable_ordinary_repository_path():
 s=inspect.getsource(api); assert "DurableTaskController" in s; assert "repository_root.expanduser().resolve()" in s; assert '".local"/"share"/"agp-cockpit"/"runtime"' in s
def test_required_persistent_controls_visible():
 s=inspect.getsource(TaskOperatorPanel)
 for x in ("Task pausieren","Task fortsetzen","Checkpoint freigeben","Human-Checkpoint","Completion","Repository:"): assert x in s
def test_keyboard_contract():
 s=inspect.getsource(TaskOperatorPanel); assert "takefocus=True" in s; assert '"<Command-r>"' in s; assert '"<Command-p>"' in s; assert "focus_set()" in s
def test_responsive_native_surface():
 s=inspect.getsource(TaskOperatorPanel); assert "ttk.Button" in s and "ttk.Label" in s; assert ".geometry(" not in s; assert ".place(" not in s


def test_main_window_does_not_expose_durable_task_operator():
    import inspect
    from agp_cockpit.ui.main_window import MainWindow
    source = inspect.getsource(MainWindow)
    assert "TaskOperatorPanel(" not in source
    assert "task_operator_panel" not in source
