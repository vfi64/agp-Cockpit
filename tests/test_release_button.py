"""P11 Release button (AGP_RELEASE_VERIFIER_V1, AGP_RELEASE_DRY_RUN_FREE_V1,
AGP_RELEASE_APPROVAL_SCOPE_V1; owner 2026-10-04)."""

import subprocess
from pathlib import Path

import pytest

from agp_cockpit.core import standard_verifier as sv
from agp_cockpit.core.kit_command_catalog import (
    KitCommandCatalog,
    approval_required_commands,
)
from agp_cockpit.core.standard_tasks import BY_KEY

TASK = BY_KEY["release"]


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=repo, text=True, capture_output=True, check=True)
    return done.stdout.strip()


def commit(repo: Path, name: str, text: str, message: str) -> None:
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path):
    """A private workspace on main at 0.1.0 with a bare origin."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / ".agentic").mkdir()
    (root / ".agentic/config.yaml").write_text("publication: none\n")
    git(root, "add", ".agentic/config.yaml")
    commit(root, "pyproject.toml", '[project]\nname = "x"\nversion = "0.1.0"\n', "base")
    git(root, "remote", "add", "origin", str(origin))
    git(root, "push", "-q", "-u", "origin", "main")
    return root


def test_precheck_accepts_a_clean_synchronized_main_and_a_higher_version(repo):
    assert TASK.check(repo, {"version": "0.1.1"}) is None
    assert TASK.check(repo, {"version": "0.1.0"}) is None   # prepared earlier, tag missing
    assert "X.Y.Z" in TASK.check(repo, {"version": "v0.1.1"})
    assert "kleiner" in TASK.check(repo, {"version": "0.0.9"})
    git(repo, "tag", "-a", "v0.1.1", "-m", "x")
    assert "existiert schon" in TASK.check(repo, {"version": "0.1.1"})


def test_precheck_blocks_dirty_unsynced_other_branches_and_public_workspaces(repo):
    (repo / "x.txt").write_text("x")
    assert "ungesicherte" in TASK.check(repo, {"version": "0.1.1"})
    (repo / "x.txt").unlink()
    commit(repo, "y.txt", "y", "local only")
    assert "nicht synchron" in TASK.check(repo, {"version": "0.1.1"})
    git(repo, "switch", "-q", "-c", "feat/a")
    assert "nur auf main" in TASK.check(repo, {"version": "0.1.1"})
    git(repo, "switch", "-q", "main")
    (repo / ".agentic/config.yaml").write_text("publication: github+pypi\n")
    assert "publication: none oder publication: github" in TASK.check(repo, {"version": "0.1.1"})   # first


def test_prompt_has_both_phases_and_skips_phase_one_when_prepared(repo):
    fresh = TASK.prompt(repo, {"version": "0.1.1"})
    assert "Phase 1 — release branch" in fresh and "release/0.1.1" in fresh
    assert "approval signature" in fresh and "ENABLE_LIVE_PUBLISH" in fresh
    assert "RELEASE_POLICY.md" in fresh
    # AGP_RELEASE_CHANGELOG_SUMMARY_V1 (live 0.1.1: the changelog got only "Prepare private release")
    assert '"Unreleased" section' in fresh and "never a" in fresh and "one-line stub" in fresh
    prepared = TASK.prompt(repo, {"version": "0.1.0"})
    assert "Phase 1 is already done" in prepared and "release/0.1.0" not in prepared


def test_contract_scope_and_verifier():
    contract = TASK.contract(Path("/r"), {"version": "0.1.1"})
    assert contract["completion_contract"] == sv_contract("0.1.1")
    assert TASK.ci_gate_merge and TASK.offers_recover_on_interrupt and TASK.confirm
    assert "agentic-kit release-publish" not in TASK.approved_scope   # the tag push always asks
    assert {"agentic-kit transfer pr-create-complete", "agentic-kit work start"} <= TASK.approved_scope


def sv_contract(version):
    return {"kind": sv.KIND, "verifier": "released", "params": {"version": version}}


def test_verifier_needs_the_annotated_tag_on_origin_in_main(repo):
    ok, finding = sv.verify(repo, sv_contract("0.1.0"))
    assert not ok and "no annotated tag" in finding
    git(repo, "tag", "v0.1.0")                                  # lightweight
    assert "no annotated tag" in sv.verify(repo, sv_contract("0.1.0"))[1]
    git(repo, "tag", "-d", "v0.1.0")
    git(repo, "tag", "-a", "v0.1.0", "-m", "Release 0.1.0")
    assert "not on origin" in sv.verify(repo, sv_contract("0.1.0"))[1]
    git(repo, "push", "-q", "origin", "v0.1.0")
    ok, finding = sv.verify(repo, sv_contract("0.1.0"))
    assert ok, finding
    assert "pyproject.toml at v0.1.1 does not name" in _tag_wrong_version(repo)


def _tag_wrong_version(repo):
    git(repo, "tag", "-a", "v0.1.1", "-m", "wrong")
    git(repo, "push", "-q", "origin", "v0.1.1")
    return sv.verify(repo, sv_contract("0.1.1"))[1]


def test_release_publish_dry_run_is_free_and_execute_asks():
    catalog = KitCommandCatalog.from_data({"meta": {"manifest_sha": "x"}, "commands": [
        {"qualified_name": "agentic-kit release-publish", "path": ["release-publish"],
         "surface": "orchestrator", "safety": "BOUNDED", "replaces_raw": [], "params": []}]}, "test")
    dry = 'ARGV = ["agentic-kit", "release-publish", "--version", V, "--dry-run", "--json"]\n'
    assert approval_required_commands(dry, catalog) == []
    live = ('ARGV = ["agentic-kit", "release-publish", "--version", V, "--execute", "--allow-execute", '
            '"--expected-signature", SIG]\n')
    assert approval_required_commands(live, catalog) == ["agentic-kit release-publish"]
    appended = dry + 'ARGV += ["--execute"]\n'   # flags appended at run time count as well
    assert approval_required_commands(appended, catalog) == ["agentic-kit release-publish"]


def test_release_dialog_suggests_the_next_patch_version():
    from agp_cockpit.ui.release_dialog import next_patch
    assert next_patch("0.1.0") == "0.1.1" and next_patch("1.9.9") == "1.9.10" and next_patch("x") == ""


def test_resume_after_phase_one_despite_the_merged_release_branch(repo):
    """AGP_RELEASE_RESUME_PHASE2_V1 (live 2026-10-04): #204 merged 0.1.1, origin/release/0.1.1
    stayed, the terminal file of the dry run broke on the remote side; the task must restart
    at the tag."""
    from agp_cockpit.core.standard_tasks import release_resume_version
    assert release_resume_version(repo) == "0.1.0"          # main names 0.1.0, no tag yet
    git(repo, "push", "-q", "origin", "main:release/0.1.0")  # the squash-merged branch stayed
    git(repo, "push", "-q", "origin", "main:release/0.1.1")
    git(repo, "fetch", "-q", "origin")
    assert TASK.check(repo, {"version": "0.1.0"}) is None     # resume: only the tag follows
    assert "existiert schon" in TASK.check(repo, {"version": "0.1.1"})   # a new release still refuses
    assert "Phase 1 is already done" in TASK.prompt(repo, {"version": "0.1.0"})
    git(repo, "tag", "-a", "v0.1.0", "-m", "x")
    assert release_resume_version(repo) == ""
    assert "existiert schon" in TASK.check(repo, {"version": "0.1.0"})   # tag present: nothing to resume
    assert "entfällt der Release-Branch" in TASK.confirm
    # AGP_RELEASE_RESUME_SCOPE_V1 (proposal 7): the resume start click grants only main sync.
    git(repo, "tag", "-d", "v0.1.0")
    assert TASK.scope(repo, {"version": "0.1.0"}) == {"agentic-kit transfer sync-main",
                                                      "agentic-kit transfer pull-current"}
    assert "agentic-kit transfer pr-create-complete" in TASK.scope(repo, {"version": "0.1.1"})
    assert "no branch, push or pull request is needed or approved" in TASK.prompt(repo, {"version": "0.1.0"})
    assert "do not\nask NEEDS_HUMAN for them" in TASK.prompt(repo, {"version": "0.1.1"})


def test_release_dialog_preview_names_the_resume():
    from agp_cockpit.ui.release_dialog import release_preview
    assert release_preview("0.1.1", "0.1.1") == "Release-Branch schon gemergt · nur noch Tag: v0.1.1"
    assert release_preview("0.1.2", "0.1.1") == "Branch: release/0.1.2 · Tag: v0.1.2"
    assert release_preview("", "0.1.1") == "Branch: release/… · Tag: v…"
