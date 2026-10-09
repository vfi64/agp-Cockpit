"""Package „Hygiene“ (owner 2026-10-07): one-line changelog entries, an exact build id and the
Kit manifest's remote effects next to the Cockpit's own list."""
import re
import sys
from pathlib import Path

from agp_cockpit.core import kit_command_catalog as kc
from agp_cockpit.core import release_hygiene as rh

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))


# --- AGP_ONE_LINE_CHANGELOG_V1 ---------------------------------------------------------------

def test_the_real_unreleased_section_has_one_line_entries():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert rh.wrapped_entry_lines(text) == [], "join wrapped Unreleased bullets into one line (#252)"


def test_a_pull_request_with_a_wrapped_entry_is_rejected_on_every_branch(tmp_path):
    import test_release_hygiene as t
    root = t.workspace(tmp_path)
    t.git(root, "init", "-q", "-b", "main")
    t.git(root, "switch", "-q", "-c", "feat/x")
    (root / "CHANGELOG.md").write_text(t.CHANGELOG.format(unreleased="- First line\n  continued\n"),
                                       encoding="utf-8")
    pr = t.order(t.PR.format(body=', "--body", "release-note-category: Fixed"'))
    found = rh.changelog_violations(pr, root)
    assert len(found) == 1 and "AGP_ONE_LINE_CHANGELOG_V1" in found[0] and "continued" in found[0]
    (root / "CHANGELOG.md").write_text(t.CHANGELOG.format(unreleased="- First line continued\n"),
                                       encoding="utf-8")
    assert rh.changelog_violations(pr, root) == []


# --- exact build id ---------------------------------------------------------------------------

def test_the_build_id_is_exactly_the_release_or_a_numbered_rebuild_of_it():
    """Release 0.2.1 (#250): a substring replace produced ``-r5`` twice; now the rule is exact:
    without Unreleased entries the build is the release build, with entries a rebuild ``-r<N>``."""
    from agp_cockpit.version import APP_VERSION, BRIDGE_BUILD_ID, build_id_from_text
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    js = (ROOT / "chrome_extension/build_identity.js").read_text(encoding="utf-8")
    assert build_id_from_text(js) == BRIDGE_BUILD_ID          # AGP_BUILD_ID_DERIVED_V1
    release = f"release-{APP_VERSION}"
    if rh.pending_entries(text):                     # KIT-GF-060: released entries may still sit there
        assert re.fullmatch(re.escape(release) + r"-r[1-9]\d*", BRIDGE_BUILD_ID), BRIDGE_BUILD_ID
    else:
        assert release == BRIDGE_BUILD_ID


def test_the_first_slice_after_a_release_removes_the_released_unreleased_entries():
    """AGP_UNRELEASED_NOT_RELEASED_V1 (owner 2026-10-08): the Kit's release-prep leaves the entries
    it released under Unreleased (KIT-GF-060). A rebuild (-r<N>) may not carry them on, or the next
    release would publish them twice."""
    from agp_cockpit.version import BRIDGE_BUILD_ID
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if re.search(r"-r\d+$", BRIDGE_BUILD_ID):
        stale = [line for line in rh.unreleased_entries(text) if line in rh.released_entries(text)]
        assert stale == [], f"remove released entries from Unreleased: {stale[:3]}"


# --- AGP_MANIFEST_REMOTE_EFFECTS_V1 ------------------------------------------------------------

def _catalog():
    catalog = kc.KitCommandCatalog.load(ROOT)
    assert catalog is not None
    return catalog


def test_every_declared_write_effect_needs_an_approval():
    catalog = _catalog()
    declared = [c for c in catalog.commands if catalog.declared_effects(c)]
    assert len(declared) >= 20
    assert all(catalog.has_remote_effect(c) for c in declared)
    doi = catalog.command("agentic-kit post-release-doi-closeout")
    # Kit 1.0.20 declares network_read (it reads Zenodo, --write changes local files only); the
    # Cockpit has not classified the orchestrator, so it still asks (AGP_UNKNOWN_EFFECT_ASKS_V1).
    assert catalog.declared_effects(doi) == () and catalog.has_remote_effect(doi)
    status = catalog.command("agentic-kit ci status")
    assert catalog.declared_effects(status) == () and not catalog.has_remote_effect(status)  # network_read


def test_known_manifest_understatements_are_exactly_these():
    """KIT-GF-057: Kit 1.0.19 said "none" where the Cockpit knew a remote effect. Kit 1.0.20
    declares every command of the Cockpit's list (verified at adoption); a new understatement
    fails here."""
    catalog = _catalog()
    understated = {
        " ".join(c["path"]) for c in catalog.commands
        if " ".join(c["path"]) in kc.REMOTE_EFFECT_COMMANDS and not catalog.declared_effects(c)
    }
    assert understated == set()
    for name in ("pr-closeout", "transfer publish-last-report"):   # local only (Kit 1.0.20)
        command = catalog.command("agentic-kit " + name)
        assert catalog.declared_effects(command) == () and not catalog.has_remote_effect(command)
