"""Release slice 2026-10-05: AGP_PR_RELEASE_CATEGORY_V1, AGP_RELEASE_CHANGELOG_GATE_V1,
AGP_KIT_GITHUB_RELEASE_V1 (P11c) and AGP_RELEASE_PHASE2_APPROVAL_V1."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agp_cockpit.core import build_freshness as bf
from agp_cockpit.core import release_hygiene as rh
from agp_cockpit.core import standard_verifier as sv
from agp_cockpit.core.command_file_contract import validate_command_content
from agp_cockpit.core.standard_tasks import BY_KEY

ROOT = Path(__file__).resolve().parents[1]


def order(body: str) -> str:
    return f"STEP = 1\nimport subprocess\n{body}\n"


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=repo, text=True, capture_output=True, check=True)
    return done.stdout.strip()


def workspace(tmp_path: Path, publication: str = "github") -> Path:
    (tmp_path / ".agentic").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agentic/config.yaml").write_text(f"publication: {publication}\n", encoding="utf-8")
    return tmp_path


PR = 'subprocess.run(["agentic-kit", "transfer", "pr-create-complete", "--title", "T"{body}])'


# --- AGP_PR_RELEASE_CATEGORY_V1 -----------------------------------------------------

def test_a_pull_request_without_a_category_is_rejected_where_the_kit_publishes_to_github(tmp_path):
    root = workspace(tmp_path)
    assert "release-note category" in rh.category_violations(order(PR.format(body="")), root)[0]
    without_line = PR.format(body=', "--body", "Some text"')
    assert rh.category_violations(order(without_line), root)
    good = PR.format(body=', "--body", "Summary\\n\\nrelease-note-category: Fixed\\n"')
    assert rh.category_violations(order(good), root) == []
    via_variable = 'BODY = "release-note-category: Tests / Gates"\n' + PR.format(body=', "--body", BODY')
    assert rh.category_violations(order(via_variable), root) == []
    wrong = PR.format(body=', "--body", "release-note-category: Feature"')
    assert "not a category: feature" in rh.category_violations(order(wrong), root)[0]


def test_work_finish_execute_cannot_carry_a_category(tmp_path):
    root = workspace(tmp_path)
    execute = 'subprocess.run(["agentic-kit", "work", "finish", "--branch", "b", "--title", "T", "--execute"])'
    assert "KIT-GF-048" in rh.category_violations(order(execute), root)[0]
    dry = 'subprocess.run(["agentic-kit", "work", "finish", "--branch", "b", "--title", "T"])'
    assert rh.category_violations(order(dry), root) == []


def test_private_tag_repositories_are_not_affected(tmp_path):
    assert rh.category_violations(order(PR.format(body="")), workspace(tmp_path, "none")) == []


def test_the_cockpit_lists_exactly_the_kits_categories():
    release_notes = pytest.importorskip("agentic_project_kit.release_notes")
    for category in rh.RELEASE_NOTE_CATEGORIES:
        assert release_notes._normalize_category(category), category
    for rejected in ("feature", "chore", "unclassified"):
        assert release_notes._normalize_category(rejected) is None
        assert rejected not in rh.RELEASE_NOTE_CATEGORIES


def test_the_rejection_is_correctable_through_the_work_order_contract(tmp_path):
    root = workspace(tmp_path)
    source = ("STEP = 1\nimport subprocess\nimport sys\n"
              "def main():\n"
              "    if '--self-test' in sys.argv:\n        return 0\n"
              "    subprocess.run(['agentic-kit', 'transfer', 'pr-create-complete', '--title', 'T'])\n"
              "    Path('Download/1_x_return_bundle.json').write_text('{}')\n"
              "if __name__ == '__main__':\n    main()\n")
    with pytest.raises(ValueError, match="AGP_PR_RELEASE_CATEGORY_V1"):
        validate_command_content(source, repository_root=root)


# --- AGP_RELEASE_CHANGELOG_GATE_V1 --------------------------------------------------

CHANGELOG = """# Changelog

## Unreleased

{unreleased}
## v0.3.0 - 2026-10-06

- Generated line

## v0.2.0 - 2026-10-05

- Old
"""


@pytest.fixture
def release_repo(tmp_path):
    root = workspace(tmp_path)
    git(root, "init", "-q", "-b", "main")
    (root / "CHANGELOG.md").write_text(CHANGELOG.format(unreleased="- Detailed entry\n"), encoding="utf-8")
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "base")
    git(root, "switch", "-q", "-c", "release/0.3.0")
    return root


def test_the_release_pull_request_needs_an_empty_unreleased_section(release_repo):
    pr = order(PR.format(body=', "--body", "release-note-category: Release"'))
    found = rh.changelog_violations(pr, release_repo)
    assert len(found) == 1 and "move every entry of the Unreleased section into '## v0.3.0'" in found[0]
    (release_repo / "CHANGELOG.md").write_text(CHANGELOG.format(unreleased=""), encoding="utf-8")
    assert rh.changelog_violations(pr, release_repo) == []
    assert rh.changelog_violations(order('subprocess.run(["agentic-kit", "release", "prepare"])'),
                                   release_repo) == []        # only the pull-request step is gated


def test_the_release_pull_request_needs_the_version_section(release_repo):
    (release_repo / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n## v0.2.0\n", encoding="utf-8")
    pr = order(PR.format(body=', "--body", "release-note-category: Release"'))
    assert "no section '## v0.3.0'" in rh.changelog_violations(pr, release_repo)[0]


def test_work_branches_are_not_gated(release_repo):
    git(release_repo, "switch", "-q", "-c", "feat/x")
    pr = order(PR.format(body=', "--body", "release-note-category: Fixed"'))
    assert rh.changelog_violations(pr, release_repo) == []


def test_unreleased_entries_reads_only_its_section():
    assert rh.unreleased_entries(CHANGELOG.format(unreleased="- a\n- b\n")) == ["- a", "- b"]
    assert rh.unreleased_entries(CHANGELOG.format(unreleased="")) == []
    assert rh.unreleased_entries("# Changelog\n") == []


def test_the_real_changelog_has_an_unreleased_section_and_the_corrected_020_entry():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    section = text.split("## v0.2.0 - 2026-10-05", 1)[1].split("## v0.1.1", 1)[0]
    assert "corrected entry" in section and "AGP_K07_REMOTE_FILE_REGENERATE_V1" in section
    assert "- Fix remote file regeneration" not in section          # the pull-request titles are gone


# --- AGP_KIT_GITHUB_RELEASE_V1 (P11c) -------------------------------------------------

def test_the_workspace_declares_the_owners_title_and_waits_for_kit_gf_049():
    import yaml
    config = yaml.safe_load((ROOT / ".agentic/config.yaml").read_text(encoding="utf-8"))
    assert config["publication"] == "none"           # switch to github after KIT-GF-049
    assert config["release"]["github_release_title_template"] == "AGP Cockpit {version} (privat)"
    assert rh.github_releases_declared(ROOT)        # categories are collected already


def test_a_title_template_alone_activates_the_category_rule(tmp_path):
    root = workspace(tmp_path, "none")
    assert rh.category_violations(order(PR.format(body="")), root) == []
    (root / ".agentic/config.yaml").write_text(
        'publication: none\nrelease:\n  github_release_title_template: "X {version}"\n', encoding="utf-8")
    assert rh.category_violations(order(PR.format(body="")), root)


def test_release_prompt_and_contract_name_the_github_entry(tmp_path):
    task = BY_KEY["release"]
    github = task.prompt(workspace(tmp_path / "g"), {"version": "0.3.0"})
    assert "GitHub Release entry" in github and "release-note-category" in github
    assert "AGP_RELEASE_CHANGELOG_GATE_V1" in github
    contract = task.contract(workspace(tmp_path / "g"), {"version": "0.3.0"})
    assert "GitHub Release entry v0.3.0 exists and is not a draft." in contract["acceptance_criteria"]
    private = task.prompt(workspace(tmp_path / "n", "none"), {"version": "0.3.0"})
    assert "only the annotated tag" in private and "release-note-category" not in private


class _Runner:
    """git through the real binary, gh answered from a fixture."""

    def __init__(self, gh_payload, gh_rc=0):
        self.gh_payload, self.gh_rc, self.gh_calls = gh_payload, gh_rc, []

    def __call__(self, argv, **kw):
        if Path(str(argv[0])).name == "gh":
            self.gh_calls.append(argv)
            return subprocess.CompletedProcess(argv, self.gh_rc, json.dumps(self.gh_payload), "")
        return subprocess.run(argv, **{k: v for k, v in kw.items() if k != "env"})


@pytest.fixture
def released(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    root = workspace(tmp_path / "repo")
    git(root, "init", "-q", "-b", "main")
    (root / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0.3.0"\n')
    git(root, "add", ".")
    git(root, "commit", "-q", "-m", "release")
    git(root, "remote", "add", "origin", str(origin))
    git(root, "push", "-q", "-u", "origin", "main")
    git(root, "tag", "-a", "v0.3.0", "-m", "Release 0.3.0")
    git(root, "push", "-q", "origin", "v0.3.0")
    return root


def test_the_verifier_also_needs_the_github_entry(released, monkeypatch):
    monkeypatch.setenv("AGP_COCKPIT_GH_BINARY", "gh")
    ok, finding = sv.verify_released(released, version="0.3.0", runner=_Runner(
        {"tagName": "v0.3.0", "isDraft": False, "name": "AGP Cockpit 0.3.0 (privat)"}))
    assert ok and "GitHub Release entry AGP Cockpit 0.3.0 (privat)" in finding
    assert not sv.verify_released(released, version="0.3.0", runner=_Runner({}, gh_rc=1))[0]
    draft = _Runner({"tagName": "v0.3.0", "isDraft": True})
    assert "draft" in sv.verify_released(released, version="0.3.0", runner=draft)[1]
    monkeypatch.setenv("AGP_COCKPIT_GH_BINARY", "none")
    assert "gh is not available" in sv.verify_released(released, version="0.3.0", runner=draft)[1]
    (released / ".agentic/config.yaml").write_text("publication: none\n")
    git(released, "commit", "-qam", "private")
    git(released, "push", "-q", "origin", "main")
    assert sv.verify_released(released, version="0.3.0")[0]           # private tag: no gh needed


# --- AGP_RELEASE_PHASE2_APPROVAL_V1 -----------------------------------------------------

def test_the_releases_own_build_id_does_not_block_its_phase2_approval(tmp_path, monkeypatch):
    stale = bf.BuildFreshness("release-0.1.1-r9", "", "release-0.2.0", True, "Quellstand neuer")
    monkeypatch.setattr(bf, "check", lambda _root: stale)
    monkeypatch.setattr(bf, "kit_block_reason", lambda _root: "")
    assert bf.start_block_reason(tmp_path).startswith("Blockiert")
    assert bf.start_block_reason(tmp_path, release_version="0.2.0") == ""
    assert bf.start_block_reason(tmp_path, release_version="0.3.0").startswith("Blockiert")
    rebuilt = bf.BuildFreshness("release-0.1.1-r9", "release-0.2.0", "release-0.2.0", True, "Neuer Build")
    monkeypatch.setattr(bf, "check", lambda _root: rebuilt)
    assert bf.start_block_reason(tmp_path, release_version="0.2.0").startswith("Blockiert")


def test_only_the_release_decision_passes_its_version():
    source = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
    block = source[source.index("def decide(self, decision: str) -> bool:"):]
    block = block[:block.index("note = self.decision_note")]
    assert 'if task.key == "release":' in block and "release_resume_version" in block
    assert "start_block_reason(self.repository_root, release_version=release_version)" in block
