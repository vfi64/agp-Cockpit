"""AGP_WORK_TASK_NOT_ON_MAIN_V1 (live 2026-10-26, Kit repository steps 91–93): an „Arbeiten“ task
started on main failed its own branch check three times; the start path now refuses main."""
import subprocess
from pathlib import Path

from agp_cockpit.core.work_tab_guard import work_task_block_reason

ROOT = Path(__file__).resolve().parents[1]
PANEL = (ROOT / "src/agp_cockpit/ui/simple_task_panel.py").read_text(encoding="utf-8")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=repo, check=True,
                   capture_output=True)


def test_main_master_and_detached_are_refused_a_work_branch_is_not(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "commit", "-q", "--allow-empty", "-m", "base")
    reason = work_task_block_reason(tmp_path)
    assert reason.startswith("Blockiert — das Repository steht auf main") and "„Arbeit beginnen“" in reason
    git(tmp_path, "branch", "-q", "-m", "main", "master")
    assert "steht auf master" in work_task_block_reason(tmp_path)
    git(tmp_path, "switch", "-q", "--detach")
    assert "detached HEAD" in work_task_block_reason(tmp_path)
    git(tmp_path, "switch", "-q", "-c", "chore/kit-1-1-6")
    assert work_task_block_reason(tmp_path) == ""


def test_a_folder_git_cannot_read_is_no_reason_to_refuse(tmp_path):
    assert work_task_block_reason(tmp_path) == ""


def test_both_start_paths_ask_the_guard():
    start = PANEL[PANEL.index("def start_task("):PANEL.index("def _launch(")]
    launch = PANEL[PANEL.index("def _launch("):PANEL.index("@staticmethod", PANEL.index("def _launch("))]
    assert "work_task_block_reason(self.repository_root)" in start
    assert start.index("work_task_block_reason") < start.index("messagebox.askyesno(")
    assert launch.index("work_task_block_reason(self.repository_root)") < launch.index("start_task_from_contract")
