import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import kit_findings as kf
from agp_cockpit.core import kit_findings_sync as ks
from agp_cockpit.core import release_policy as rp
from agp_cockpit.core.command_file_contract import validate_command_content

ROOT = Path(__file__).resolve().parents[1]
CHANGELOG = "## v1.0.13 - 2026-09-16\n\n## v1.0.10 - 2026-09-13\n\n## v1.0.9 - 2026-09-06\n"


# --- AGP_KIT_FINDINGS_SYNC_V1 ---------------------------------------------------

def test_classify_kit_statements():
    assert ks.classify("fixed") == ks.CLOSED
    assert ks.classify("fixed_on_current_main") == ks.CLOSED
    assert ks.classify("closed_current_checkout") == ks.CLOSED
    assert ks.classify("fixed_in_v1_0_9") == ks.CLOSED
    assert ks.classify("PASS | KIT-GF-009 is externally closed for the tested boundary.") == ks.CLOSED
    assert ks.classify("partially_addressed_needs_external_retest") == ks.PARTIAL
    assert ks.classify("external_init_retested_pass_remaining") == ks.PARTIAL
    assert ks.classify("mitigated_fixed_needs_released_package_retest") == ks.PARTIAL
    assert ks.classify("open_deferred") == ks.OPEN


def test_fixed_in_follows_release_dates():
    released = ks.releases(CHANGELOG)
    assert ks.fixed_in("fixed_on_current_main", "2026-09-04", released) == "1.0.9"
    assert ks.fixed_in("fixed", "2026-09-08", released) == "1.0.10"
    assert ks.fixed_in("fixed_released_package_retest_pass", "2026-09-08", released) == "1.0.9"
    assert ks.fixed_in("fixed_in_v1_0_9", "2026-09-30", released) == "1.0.9"
    assert ks.fixed_in("PASS", "2026-09-16", released, "POST_V1_0_13_X_RELEASED_PACKAGE_RETEST.json") == "1.0.13"
    assert ks.fixed_in("closed_current_main", "2026-09-20", released) == ""      # not released yet


def _kit_checkout(tmp_path):
    reports = tmp_path / "kit" / "docs" / "reports"
    reports.mkdir(parents=True)
    (tmp_path / "kit" / "CHANGELOG.md").write_text(CHANGELOG)
    (reports / "A_20260904.json").write_text(json.dumps({"date": "2026-09-04", "finding_adjudications": [
        {"id": "KIT-GF-002", "status": "fixed_on_current_main"}, {"id": "KIT-GF-011", "status": "improved_not_closed"}]}))
    (reports / "B_20260908.json").write_text(json.dumps({"date": "2026-09-08", "finding_status": [
        {"id": "KIT-GF-002", "status": "fixed"}, {"id": "KIT-GF-003", "status": "partially_addressed"}]}))
    (reports / "C_20260916.json").write_text(json.dumps({"date": "2026-09-16", "finding_status": [
        {"id": "KIT-GF-011", "status": "open_external_released_package_evidence_required"}]}))
    return tmp_path / "kit"


def test_collect_takes_the_latest_statement_and_the_first_closed_date(tmp_path):
    overlay = ks.collect(_kit_checkout(tmp_path), "abc")
    findings = overlay["findings"]
    assert findings["KIT-GF-002"]["kit_state"] == ks.CLOSED and findings["KIT-GF-002"]["fixed_in"] == "1.0.9"
    assert findings["KIT-GF-002"]["raw"] == "fixed" and findings["KIT-GF-002"]["closed_since"].startswith("2026-09-04")
    assert findings["KIT-GF-003"]["kit_state"] == ks.PARTIAL
    assert findings["KIT-GF-011"]["kit_state"] == ks.OPEN
    assert overlay["kit_commit"] == "abc" and overlay["latest_release"] == "1.0.13"
    assert ks.collect(_kit_checkout(tmp_path / "again"), "abc") == overlay      # pure function of the checkout


def test_overlay_drives_the_effective_status_without_changing_the_register(tmp_path):
    register = tmp_path / kf.REGISTER
    register.parent.mkdir(parents=True)
    register.write_text(json.dumps({"families": [
        {"id": "KIT-GF-002", "title": "a", "status": "OPEN"}, {"id": "KIT-GF-003", "title": "b", "status": "OPEN"},
        {"id": "KIT-GF-011", "title": "c", "status": "OPEN"}, {"id": "KIT-GF-099", "title": "d", "status": "OPEN"}]}))
    ks.write_overlay(tmp_path, ks.collect(_kit_checkout(tmp_path), "abc"))
    before = register.read_text()
    states = {f.id: f.effective_status("1.0.13") for f in kf.load(tmp_path)}
    assert states == {"KIT-GF-002": kf.FIXED_UNVERIFIED, "KIT-GF-003": kf.IN_PROGRESS,
                      "KIT-GF-011": kf.OPEN, "KIT-GF-099": kf.OPEN}
    assert {f.id: f.effective_status("1.0.8") for f in kf.load(tmp_path)}["KIT-GF-002"] == kf.FIXED_NOT_INSTALLED
    assert register.read_text() == before
    detail = next(f for f in kf.load(tmp_path) if f.id == "KIT-GF-002").detail_text("1.0.13")
    assert "Kit-Repo: CLOSED — fixed" in detail and "behoben in 1.0.9" in detail


def test_fetch_clones_the_public_kit_repo_read_only(tmp_path):
    calls = []

    def runner(argv, **_):
        calls.append(argv[1:3])
        return SimpleNamespace(returncode=0, stdout="deadbeef\n", stderr="")

    _checkout, commit = ks.fetch(tmp_path, runner=runner)
    assert commit == "deadbeef"
    assert calls[0] == ["clone", "-q"] and all(c[0] in {"clone", "rev-parse"} for c in calls)


def test_tracked_register_carries_the_kit_snapshot_and_kit_gf_029():
    data = json.loads((ROOT / kf.REGISTER).read_text(encoding="utf-8"))
    assert data["kit_repo_sync"]["marker"] == "AGP_KIT_FINDINGS_SYNC_V1"
    families = {f["id"]: f for f in data["families"]}
    assert families["KIT-GF-002"]["kit_repo_status"]["kit_state"] == "CLOSED"
    assert families["KIT-GF-029"]["cockpit_mitigation"][0]["marker"] == "AGP_RELEASE_POLICY_V1"


# --- AGP_RELEASE_POLICY_V1 ---------------------------------------------------------

def order(body: str) -> str:
    return f"STEP = 1\nimport subprocess\n{body}\n"


def test_publication_steps_violate_the_release_policy():
    assert rp.violations(order('subprocess.run(["agentic-kit", "release-publish", "--json"])'), ROOT)
    assert rp.violations(order('subprocess.run(["gh", "release", "create", "v0.1.0"])'), ROOT)
    assert rp.violations(order('URL = "https://zenodo.org/api/records"'), ROOT)
    assert rp.violations(order('subprocess.run(["agentic-kit", "post-release-doi-closeout"])'), ROOT)
    assert rp.violations(order('subprocess.run(["agentic-kit", "release-check", "--version", "0.1.0"])'), ROOT) == []
    assert rp.violations(order('subprocess.run(["gh", "release", "view", "v0.1.0"])'), ROOT) == []


def test_without_a_policy_nothing_is_rejected(tmp_path):
    assert rp.violations(order('subprocess.run(["gh", "release", "create", "v1"])'), tmp_path) == []


def test_policy_violation_is_a_correctable_rejection():
    with pytest.raises(ValueError, match="semantic contract rejected: .*release policy"):
        validate_command_content(order('subprocess.run(["gh", "release", "create", "v0.1.0"])'),
                                 repository_root=ROOT)


def test_policy_documents_exist_and_agree():
    policy = json.loads((ROOT / "docs/planning/release_policy.json").read_text(encoding="utf-8"))
    text = (ROOT / "docs/planning/RELEASE_POLICY.md").read_text(encoding="utf-8")
    assert policy["publication"] == "none" and "zenodo.org" in policy["forbidden_hosts"]
    assert "No PyPI package, no Zenodo record" in text and "KIT-GF-029" in text
    # Owner's decision 2026-10-02: a hand-made Release entry in the private repo;
    # work orders still may not create one (the rejection test above).
    assert policy["owner_github_release"]["allowed"] is True
    assert "release create" in policy["forbidden_gh"] and "owner_github_release" in text


# --- AGP_SCROLLABLE_TABS_V1 and the recommendation hint ----------------------------

def test_initial_geometry_uses_the_screen():
    from agp_cockpit.ui.scrollable import initial_geometry
    # AGP_INITIAL_WINDOW_SIZE_V2: the owner's size, clamped to small screens.
    assert initial_geometry(1512, 982) == "986x726"
    assert initial_geometry(2560, 1440) == "986x726"
    assert initial_geometry(800, 600) == "760x540"


def test_tabs_scroll_when_the_window_is_too_small():
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    try:
        from tkinter import ttk

        from agp_cockpit.ui.scrollable import ScrollableTab
        root.geometry("400x200")
        tab = ScrollableTab(root, min_width=300)
        tab.pack(fill="both", expand=True)
        ttk.Frame(tab.inner, height=900, width=300).grid(row=0, column=0)
        root.update()
        assert tab.overflowing() and tab.vbar.winfo_ismapped()
        root.geometry("400x1200")
        root.update()
        assert not tab.overflowing() and not tab.vbar.winfo_ismapped()
    finally:
        root.destroy()
    source = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert source.count("ScrollableTab(self.tabs)") == 3


def test_a_recommended_verb_without_button_points_to_arbeiten():
    from agp_cockpit.core import repo_state as rs
    from agp_cockpit.ui.standard_tasks_panel import StandardTasksPanel
    facts = rs.RepoFacts(root="/r", is_git=True, branch="feat/x", head="b" * 40, origin_main="a" * 40,
                         tracking_main="a" * 40, own_commits=1, kit_version="1.0.13", workspace=True, gh_ok=True)
    state = rs.classify(facts)
    assert state.recommended == rs.ABSCHLIESSEN
    # T5: Abschließen has its button now (plan P6).
    assert StandardTasksPanel._state_hint(state).startswith("Empfohlen: Abschließen")
    no_kit = rs.classify(rs.RepoFacts(root="/r", is_git=True, branch="main", head="a" * 40,
                                      origin_main="a" * 40, tracking_main="a" * 40, own_commits=0,
                                      kit_version="1.0.13", workspace=False, gh_ok=True))
    assert no_kit.recommended == rs.REPO_UEBERNEHMEN
    hint = StandardTasksPanel._state_hint(no_kit)
    assert hint.startswith("Nächster Schritt wäre „Repo übernehmen“") and "Plan P9" in hint and "Arbeiten" in hint
