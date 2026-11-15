"""AGP_KIT_ADOPT_BUILD_REVISION_V1 (workflow-friction plan C2, V7): since Kit 1.4.0 „Kit übernehmen“
leaves the adoption line under Unreleased (Kit K4). The build-id rule then wants release-<v>-r<N>; PR #436
needed a follow-up only for that. After the adoption check passed, the Cockpit raises its own build
revision on chore/kit-<v>, and the stale-app guard does not lock „Abschließen“ for that revision."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from agp_cockpit.core import build_freshness as bf
from agp_cockpit.core import build_revision as br
from agp_cockpit.core import release_hygiene as rh
from agp_cockpit.core import standard_tasks as st
from agp_cockpit.core import standard_verifier as sv
from agp_cockpit.version import build_id_from_text

ROOT = Path(__file__).resolve().parents[1]
ADOPTION = "- Adopt Agentic Project Kit 1.4.0 (previously 1.3.0).\n"
CHANGELOG = "# Changelog\n\n## Unreleased\n\n{unreleased}\n## v0.4.1 - 2026-11-13\n\n- Earlier entry\n"


def _with_revision(text: str, version: str, number: int) -> str:
    """The real file with its revision set to (version, number); APP_VERSION stays."""
    changed, count = re.subn(r"""(BUILD_REVISION\s*=\s*[(\[]\s*["'])[^"']+(["']\s*,\s*)\d+""",
                             lambda m: f"{m.group(1)}{version}{m.group(2)}{number}", text)
    assert count == 1
    return changed


def checkout(tmp_path: Path, *, revision=("0.4.0", 1), unreleased: str = ADOPTION, branch="chore/kit-1.4.0"):
    """The Cockpit's real build identity files (version 0.4.1) with the given revision."""
    for relative in (br.VERSION_FILE, br.EXTENSION_FILE):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = (ROOT / relative).read_text(encoding="utf-8")
        text = re.sub(r"""^((?:AGP_)?APP_VERSION\s*=\s*["'])[^"']+""", r"\g<1>0.4.1", text, flags=re.MULTILINE)
        target.write_text(_with_revision(text, *revision), encoding="utf-8")
    (tmp_path / br.CHANGELOG_FILE).write_text(CHANGELOG.format(unreleased=unreleased), encoding="utf-8")
    (tmp_path / ".git").mkdir(exist_ok=True)
    (tmp_path / ".git/HEAD").write_text(f"ref: refs/heads/{branch}\n", encoding="utf-8")
    return tmp_path


def build_ids(root: Path) -> set[str]:
    return {build_id_from_text((root / path).read_text(encoding="utf-8"))
            for path in (br.VERSION_FILE, br.EXTENSION_FILE)}


def test_an_adoption_line_raises_the_revision_in_both_files_once(tmp_path):
    root = checkout(tmp_path)
    assert build_ids(root) == {"release-0.4.1"}
    assert br.align(root) == [br.VERSION_FILE, br.EXTENSION_FILE]
    assert build_ids(root) == {"release-0.4.1-r1"}
    assert 'BUILD_REVISION = ("0.4.1", 1)' in (root / br.VERSION_FILE).read_text(encoding="utf-8")
    assert 'AGP_BUILD_REVISION = ["0.4.1", 1];' in (root / br.EXTENSION_FILE).read_text(encoding="utf-8")
    assert br.align(root) == []                                   # idempotent: the verifier may run again
    assert build_ids(root) == {"release-0.4.1-r1"}


def test_the_raised_revision_passes_the_build_id_rule_without_a_follow_up(tmp_path):
    """Plan C2 acceptance 2: the adoption branch passes test_hygiene's rule as it is."""
    root = checkout(tmp_path)
    br.align(root)
    text = (root / br.CHANGELOG_FILE).read_text(encoding="utf-8")
    assert rh.pending_entries(text)
    for build in build_ids(root):
        assert re.fullmatch(r"release-0\.4\.1-r[1-9]\d*", build)


def test_nothing_changes_without_pending_entries_or_with_a_current_rebuild(tmp_path):
    assert br.align(checkout(tmp_path / "none", unreleased="")) == []
    assert build_ids(tmp_path / "none") == {"release-0.4.1"}
    released = checkout(tmp_path / "released", unreleased="- Earlier entry\n")    # KIT-GF-060 leftover
    assert br.align(released) == []
    rebuilt = checkout(tmp_path / "rebuilt", revision=("0.4.1", 3))
    assert br.align(rebuilt) == [] and build_ids(rebuilt) == {"release-0.4.1-r3"}


def test_another_repository_is_left_alone(tmp_path):
    (tmp_path / br.CHANGELOG_FILE).write_text(CHANGELOG.format(unreleased=ADOPTION), encoding="utf-8")
    assert br.align(tmp_path) == []
    checkout(tmp_path)
    (tmp_path / br.EXTENSION_FILE).unlink()
    assert br.align(tmp_path) == []
    assert build_ids_python_only(tmp_path) == "release-0.4.1"


def build_ids_python_only(root: Path) -> str:
    return build_id_from_text((root / br.VERSION_FILE).read_text(encoding="utf-8"))


def test_inconsistent_identity_files_block_instead_of_guessing(tmp_path):
    root = checkout(tmp_path)
    js = root / br.EXTENSION_FILE
    js.write_text(_with_revision(js.read_text(encoding="utf-8"), "0.3.9", 2), encoding="utf-8")
    with pytest.raises(br.RevisionError, match="BUILD_REVISION differs"):
        br.align(root)
    root = checkout(tmp_path / "v")
    js = root / br.EXTENSION_FILE
    js.write_text(js.read_text(encoding="utf-8").replace('AGP_APP_VERSION = "0.4.1"', 'AGP_APP_VERSION = "0.4.0"'),
                  encoding="utf-8")
    with pytest.raises(br.RevisionError, match="APP_VERSION differs"):
        br.align(root)
    assert build_ids_python_only(root) == "release-0.4.1"                          # nothing written


def test_the_real_identity_files_have_exactly_one_anchor_each():
    for relative in (br.VERSION_FILE, br.EXTENSION_FILE):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert len(br._VERSION.findall(text)) == 1 and len(br._REVISION.findall(text)) == 1, relative


def test_the_passing_adoption_check_raises_the_revision_and_says_so(tmp_path):
    root = checkout(tmp_path)
    assert sv.complete_kit_adoption(root, False, "the installed Kit is 1.3.0") == (False,
                                                                                   "the installed Kit is 1.3.0")
    assert build_ids(root) == {"release-0.4.1"}                   # no write before a passing check
    ok, finding = sv.complete_kit_adoption(root, True, "Kit 1.4.0 installed and pinned")
    assert ok and "build revision raised" in finding and br.VERSION_FILE in finding
    assert build_ids(root) == {"release-0.4.1-r1"}
    assert sv.complete_kit_adoption(root, True, "again") == (True, "again")
    js = root / br.EXTENSION_FILE
    js.write_text(_with_revision(js.read_text(encoding="utf-8"), "0.3.9", 2), encoding="utf-8")
    ok, finding = sv.complete_kit_adoption(root, True, "Kit 1.4.0 installed and pinned")
    assert not ok and "could not follow the adoption" in finding


def test_the_guard_does_not_lock_finishing_the_adoption_branch(tmp_path):
    root = checkout(tmp_path, revision=("0.4.1", 1))
    fresh = bf.check(root, "release-0.4.1", frozen=False)
    assert not fresh.stale and fresh.message == ""
    assert fresh.note.startswith("Kit 1.4.0 wird übernommen") and "neu bauen" in fresh.note
    assert bf.stale_block_reason(root) == ""


def test_the_guard_exemption_is_narrow(tmp_path):
    feature = checkout(tmp_path / "feat", revision=("0.4.1", 1), branch="feat/x")
    assert bf.check(feature, "release-0.4.1", frozen=False).stale
    plain = checkout(tmp_path / "plain", revision=("0.4.0", 1))                     # release-0.4.1, no -r
    assert bf.check(plain, "release-0.4.0-r2", frozen=False).stale
    newer = checkout(tmp_path / "newer", revision=("0.4.1", 2))                     # older app version runs
    assert bf.check(newer, "release-0.4.0-r5", frozen=False).stale
    same = checkout(tmp_path / "same", revision=("0.4.1", 1))
    assert not bf.check(same, "release-0.4.1-r1", frozen=False).stale                # rebuilt already
    assert bf.check(same, "release-0.4.1-r1", frozen=False).note == ""
    main = checkout(tmp_path / "main", revision=("0.4.1", 1), branch="main")        # after the merge
    assert "ist neuer als die laufende App" in bf.check(main, "release-0.4.1", frozen=False).message


def test_prompt_and_contract_say_the_cockpit_raises_the_revision():
    task = st.BY_KEY["kit-adopt"]
    prompt = task.prompt(ROOT, {"version": "1.4.0"})
    assert "raises its own build revision" in prompt and "do not edit any file" in prompt
    criteria = task.contract(ROOT, {"version": "1.4.0"})["acceptance_criteria"]
    assert any("AGP_KIT_ADOPT_BUILD_REVISION_V1" in line for line in criteria)
