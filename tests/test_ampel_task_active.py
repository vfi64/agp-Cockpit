"""AGP_AMPEL_TASK_ACTIVE_V1 and AGP_MANUAL_GITHUB_RELEASE_HINT_V1 (live 2026-10-06, release 0.2.1).

Right after „Freigeben“ the bridge still reported the answered mission (NEEDS_HUMAN), so the Lage showed „Grün — bereit für
neue Arbeit“ and recommended „Arbeit beginnen“ while the release ran. After the release the
tag existed but no GitHub entry, and the Cockpit did not say that the owner creates it.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import agp_cockpit.ui.standard_tasks_panel as m
from agp_cockpit.core import release_hygiene as rh
from agp_cockpit.ui.standard_tasks_panel import StandardTasksPanel


def test_the_tracked_task_counts_as_running_while_the_bridge_still_shows_the_old_mission(monkeypatch):
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": {"mission_id": "m", "state": "NEEDS_HUMAN"}})
    assert StandardTasksPanel._task_running(SimpleNamespace(_task_active=True))
    assert not StandardTasksPanel._task_running(SimpleNamespace(_task_active=False))
    monkeypatch.setattr(m, "bridge_status", lambda: {"mission": {"mission_id": "m", "state": "RUNNING"}})
    assert StandardTasksPanel._task_running(SimpleNamespace(_task_active=False))


def test_tracking_marks_the_task_active_and_hides_an_old_command():
    shown: list[str] = []
    panel = SimpleNamespace(_poll_job=None, _task_active=False, after=lambda _ms, _fn: "job",
                            show_followup_command=shown.append, refresh_progress=None)
    StandardTasksPanel._track(panel, "mission-1")
    assert panel._task_active and panel._tracked_mission_id == "mission-1" and shown == [""]


def _workspace(tmp_path: Path, publication: str, template: str | None) -> Path:
    (tmp_path / ".agentic").mkdir(parents=True, exist_ok=True)
    text = f"publication: {publication}\n"
    if template is not None:
        text += f'release:\n  github_release_title_template: "{template}"\n'
    (tmp_path / ".agentic/config.yaml").write_text(text, encoding="utf-8")
    return tmp_path


def test_a_private_release_names_the_owners_github_command(tmp_path):
    root = _workspace(tmp_path, "none", "AGP Cockpit {version} (privat)")
    command = rh.manual_github_release_command(root, "0.2.1")
    assert command.startswith(f"cd {root} && ")
    assert "gh release create v0.2.1 --verify-tag --title 'AGP Cockpit 0.2.1 (privat)'" in command
    assert "awk '/^## v0\\.2\\.1( |$)/{f=1;next} /^## /{f=0} f' CHANGELOG.md" in command
    assert command.endswith("--notes-file .local/agp-cockpit/tmp/notes-0.2.1.md")


def test_no_command_where_the_kit_publishes_or_no_entry_is_wanted(tmp_path):
    assert rh.manual_github_release_command(_workspace(tmp_path / "a", "github", "T {version}"), "1.0") == ""
    assert rh.manual_github_release_command(_workspace(tmp_path / "b", "none", None), "1.0") == ""
    assert rh.manual_github_release_command(_workspace(tmp_path / "c", "none", "T {version}"), "") == ""


def test_the_command_extracts_exactly_the_version_section(tmp_path):
    import subprocess
    root = _workspace(tmp_path, "none", "T {version}")
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## Unreleased\n\n## v0.2.10 - x\n\n- other\n\n## v0.2.1 - 2026-10-06\n\n- a\n- b\n\n"
        "## v0.2.0 - 2026-10-05\n\n- old\n", encoding="utf-8")
    command = rh.manual_github_release_command(root, "0.2.1")
    extract = command.split(" && gh release")[0]
    subprocess.run(["/bin/sh", "-c", extract], check=True)
    assert (root / ".local/agp-cockpit/tmp/notes-0.2.1.md").read_text() == "\n- a\n- b\n\n"
