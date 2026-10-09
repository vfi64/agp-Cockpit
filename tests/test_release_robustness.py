"""Release 0.2.2 (2026-10-07): three failed steps blocked phase 1 and a red stale-app warning
locked the tasks in the middle of the release. AGP_RELEASE_IN_PROGRESS_V1,
AGP_RELEASE_BUILD_ID_GATE_V1, AGP_RELEASE_SUMMARY_JSON_V1, AGP_LOOP_BUTTON_STATES_V1."""
from __future__ import annotations

from pathlib import Path

from agp_cockpit.core import build_freshness as bf
from agp_cockpit.core import release_hygiene as rh
from agp_cockpit.core.standard_tasks import BY_KEY
from agp_cockpit.ui.simple_task_panel import loop_button_states

ROOT = Path(__file__).resolve().parents[1]
PR = ('STEP = 1\nimport subprocess\nsubprocess.run(["agentic-kit", "transfer", "pr-create-complete", '
      '"--title", "Release 0.2.2", "--body", "release-note-category: Release"])\n')
CHANGELOG = "# Changelog\n\n## Unreleased\n\n## v0.2.2 - 2026-10-07\n\n- Entry\n"


def checkout(tmp_path: Path, branch: str, build_id: str, js_id: str | None = None) -> Path:
    (tmp_path / ".git").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".git/HEAD").write_text(f"ref: refs/heads/{branch}\n", encoding="utf-8")
    (tmp_path / "src/agp_cockpit").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src/agp_cockpit/version.py").write_text(f'BRIDGE_BUILD_ID = "{build_id}"\n', encoding="utf-8")
    (tmp_path / "chrome_extension").mkdir(exist_ok=True)
    (tmp_path / "chrome_extension/build_identity.js").write_text(
        f'globalThis.AGP_EXTENSION_BUILD_ID = "{js_id or build_id}";\n', encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    return tmp_path


# --- AGP_RELEASE_IN_PROGRESS_V1 -----------------------------------------------------------

def test_the_live_case_on_the_release_branch_is_a_yellow_note_not_a_lock(tmp_path):
    root = checkout(tmp_path, "release/0.2.2", "release-0.2.2-r12")
    fresh = bf.check(root, "release-0.2.1-r12", frozen=False)
    assert not fresh.stale and fresh.message == ""
    assert fresh.note.startswith("Release 0.2.2 läuft") and "neu bauen" in fresh.note
    assert bf.stale_block_reason.__name__      # the panels ask stale_block_reason, which follows stale
    root = checkout(tmp_path, "release/0.2.2", "release-0.2.2")
    assert bf.check(root, "release-0.2.1-r12", frozen=False).note.startswith("Release 0.2.2 läuft")


def test_a_release_branch_does_not_hide_a_foreign_or_older_build(tmp_path):
    root = checkout(tmp_path, "release/0.2.2", "release-0.3.0")          # another version
    assert bf.check(root, "release-0.2.1-r12", frozen=False).stale
    root = checkout(tmp_path, "feat/x", "release-0.2.2")                 # not a release branch
    assert bf.check(root, "release-0.2.1-r12", frozen=False).stale
    root = checkout(tmp_path, "release/0.2.2", "release-0.2.2")
    assert not bf.check(root, "release-0.2.2", frozen=False).stale       # rebuilt already
    assert bf.check(root, "release-0.2.2", frozen=False).note == ""


def test_after_the_merge_main_asks_for_the_rebuild_by_name(tmp_path):
    root = checkout(tmp_path, "main", "release-0.2.2")
    fresh = bf.check(root, "release-0.2.1-r12", frozen=False)
    assert fresh.stale and fresh.message.startswith("Release 0.2.2 ist im Quellstand")
    assert "neu bauen" in fresh.message
    root = checkout(tmp_path, "main", "release-0.2.2-r1")                # an ordinary rebuild
    assert "ist neuer als die laufende App" in bf.check(root, "release-0.2.2", frozen=False).message


def test_current_branch_reads_head_and_worktrees(tmp_path):
    assert bf.current_branch(checkout(tmp_path / "a", "release/1.2.3", "x")) == "release/1.2.3"
    (tmp_path / "a/.git/HEAD").write_text("0123abcd\n", encoding="utf-8")
    assert bf.current_branch(tmp_path / "a") == ""                       # detached
    gitdir = tmp_path / "gd"
    gitdir.mkdir()
    (gitdir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (tmp_path / "w").mkdir()
    (tmp_path / "w/.git").write_text(f"gitdir: {gitdir}\n", encoding="utf-8")
    assert bf.current_branch(tmp_path / "w") == "main"
    assert bf.current_branch(tmp_path / "none") == ""


def test_the_header_shows_the_note_without_rebuild_button():
    source = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    block = source[source.index("elif freshness is not None and freshness.note:"):]
    block = block[:block.index("else:")]
    assert "_rebuild_button.grid_remove()" in block and "freshness.note" in block
    assert "#d03030" not in block


# --- AGP_RELEASE_BUILD_ID_GATE_V1 ---------------------------------------------------------

def test_the_release_pull_request_needs_the_exact_release_build_id(tmp_path, monkeypatch):
    root = checkout(tmp_path, "release/0.2.2", "release-0.2.2-r12")
    monkeypatch.setattr(rh, "_branch", lambda _root, runner=None: "release/0.2.2")
    found = rh.changelog_violations(PR, root)
    assert len(found) == 2 and all("AGP_RELEASE_BUILD_ID_GATE_V1" in item for item in found)
    assert "'release-0.2.2-r12'" in found[0] and "expected 'release-0.2.2'" in found[0]
    root = checkout(tmp_path, "release/0.2.2", "release-0.2.2", js_id="release-0.2.1-r12")
    assert ["chrome_extension/build_identity.js" in item for item in rh.changelog_violations(PR, root)] == [True]
    root = checkout(tmp_path, "release/0.2.2", "release-0.2.2")
    assert rh.changelog_violations(PR, root) == []


def test_the_build_id_gate_reaches_the_work_order_contract():
    assert "build_id_violations(repository_root, version)" in (
        ROOT / "src/agp_cockpit/core/release_hygiene.py").read_text(encoding="utf-8")


# --- AGP_RELEASE_SUMMARY_JSON_V1 ----------------------------------------------------------

def test_a_text_summary_file_is_rejected_before_it_runs():
    step_1851 = ('STEP = 1851\nimport subprocess\nfrom pathlib import Path\n'
                 'summary = Path(".local/agp-cockpit/tmp/1851") / "release-summary.txt"\n'
                 'subprocess.run(["agentic-kit", "release-prep", "--version", "0.2.2", '
                 '"--summary-lines-from", str(summary), "--json"])\n')
    found = rh.summary_violations(step_1851)
    assert len(found) == 1 and "AGP_RELEASE_SUMMARY_JSON_V1" in found[0] and "release-summary.txt" in found[0]
    literal = ('import subprocess\nsubprocess.run(["agentic-kit", "release-prep", '
               '"--summary-lines-from", "notes.md"])\n')
    assert rh.summary_violations(literal)
    step_1852 = step_1851.replace("release-summary.txt", "release-summary.json")
    assert rh.summary_violations(step_1852) == []
    assert rh.summary_violations('import subprocess\nsubprocess.run(["agentic-kit", "check"])\n') == []


def test_the_release_prompt_names_json_and_the_exact_build_id(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.2.1"\n', encoding="utf-8")
    prompt = BY_KEY["release"].prompt(tmp_path, {"version": "0.2.2"})
    assert "--summary-lines-from <file>.json" in prompt and "AGP_RELEASE_SUMMARY_JSON_V1" in prompt
    assert "exactly release-0.2.2" in prompt and "AGP_RELEASE_BUILD_ID_GATE_V1" in prompt


# --- AGP_LOOP_BUTTON_STATES_V1 ------------------------------------------------------------

def test_loop_buttons_follow_the_task():
    at_rest = loop_button_states("LOADED", "IDLE")
    assert at_rest == {"pause_button": "disabled", "resume_button": "disabled",
                       "stop_button": "disabled", "reset_button": "normal"}
    running = loop_button_states("STARTED", "RUNNING")
    assert running["pause_button"] == running["stop_button"] == "normal"
    assert running["resume_button"] == running["reset_button"] == "disabled"
    paused = loop_button_states("STARTED", "PAUSED")
    assert paused["resume_button"] == paused["stop_button"] == "normal" and paused["pause_button"] == "disabled"
    stopped = loop_button_states("STARTED", "STOPPED")
    assert set(stopped.values()) == {"disabled"}
    assert loop_button_states("STARTED", "IDLE")["pause_button"] == "normal"   # started, no loop event yet


def test_the_panel_applies_the_loop_states_wherever_the_task_changes():
    source = (ROOT / "src/agp_cockpit/ui/simple_task_panel.py").read_text(encoding="utf-8")
    for anchor in ("    def refresh_status(self) -> None:", "    def _show_file_loop_state(",
                   "    def _update_start_button(self) -> None:"):
        block = source[source.index(anchor):]
        end = block.find("\n    def ", 1)
        block = block if end < 0 else block[:end]
        assert "self._update_loop_buttons()" in block, anchor
    init = source[source.index("    def __init__("):source.index("    def _follow_viewport(")]
    assert "self._update_loop_buttons()" in init
