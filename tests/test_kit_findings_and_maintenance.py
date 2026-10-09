import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import kit_findings as kf
from agp_cockpit.core import maintenance as mt

ROOT = Path(__file__).resolve().parents[1]


# --- AGP_KIT_FINDINGS_VIEW_V1 -------------------------------------------------

def test_the_real_register_loads_and_contains_the_2026_10_findings():
    findings = kf.load(ROOT)
    ids = {f.id for f in findings}
    assert {"KIT-GF-010", "KIT-GF-023", "KIT-GF-026", "KIT-GF-027", "KIT-GF-028"} <= ids
    ci = next(f for f in findings if f.id == "KIT-GF-026")
    assert ci.mitigations and ci.mitigations[0]["marker"] == "AGP_CI_GATE_V2"
    assert "Cockpit überbrückt" in ci.detail_text("1.0.13")
    assert "offen" in kf.summary(findings, "1.0.13")


def test_effective_status_compares_fixed_in_with_the_installed_kit():
    def finding(**kw):
        base = {"id": "X", "title": "t", "severity": "high", "status": "OPEN", "first_observed": "2026-10-01"}
        base.update(kw)
        return kf.KitFinding(**base)
    assert finding().effective_status("1.0.13") == kf.OPEN
    assert finding(status="FIXED", fixed_in="1.0.14").effective_status("1.0.13") == kf.FIXED_NOT_INSTALLED
    assert finding(status="FIXED", fixed_in="1.0.14").effective_status("1.0.14") == kf.FIXED_UNVERIFIED
    assert finding(status="FIXED", fixed_in="1.0.14").effective_status(None) == kf.FIXED_NOT_INSTALLED
    assert finding(status="VERIFIED_FIXED", fixed_in="1.0.14").effective_status("1.0.13") == kf.VERIFIED


def test_a_cockpit_retest_that_reproduces_the_defect_overrides_the_kit_closure():
    """AGP_KIT_FINDING_REPRODUCED_V1 (KIT-GF-042, Kit 1.0.17, GF-E058)."""
    closed = {"kit_state": "CLOSED", "fixed_in": "1.0.17"}

    def finding(**kw):
        base = {"id": "X", "title": "t", "severity": "high", "status": "OPEN", "first_observed": "2026-10-01"}
        base.update(kw)
        return kf.KitFinding(**base)
    assert finding(kit=closed).effective_status("1.0.17") == kf.FIXED_UNVERIFIED
    refuted = finding(kit=closed, reproduced_in="1.0.17")
    assert refuted.effective_status("1.0.17") == kf.OPEN
    assert "besteht mit Kit 1.0.17 weiter" in refuted.detail_text("1.0.17")
    later_fix = finding(kit={"kit_state": "CLOSED", "fixed_in": "1.0.18"}, reproduced_in="1.0.17")
    assert later_fix.effective_status("1.0.17") == kf.FIXED_NOT_INSTALLED
    assert later_fix.effective_status("1.0.18") == kf.FIXED_UNVERIFIED
    assert finding(kit={"kit_state": "CLOSED", "fixed_in": ""}, reproduced_in="1.0.17").effective_status("1.0.17") == kf.OPEN


def test_the_real_register_tracks_the_kit_1_0_18_adoption():
    """Statuses as seen with 1.0.18 installed (kept: the window computes them per installed Kit)."""
    by_id = {f.id: f for f in kf.load(ROOT)}
    for fid in ("KIT-GF-041", "KIT-GF-042", "KIT-GF-044", "KIT-GF-045", "KIT-GF-046"):
        assert by_id[fid].effective_status("1.0.18") == kf.VERIFIED
    assert by_id["KIT-GF-042"].reproduced_in == "1.0.17"                    # GF-E058 stays on record
    assert by_id["KIT-GF-042"].mitigations[-1]["marker"] == "AGP_CI_UPDATE_GUARD_V1"
    for fid in ("KIT-GF-030", "KIT-GF-031", "KIT-GF-039", "KIT-GF-040", "KIT-GF-043"):
        assert by_id[fid].effective_status("1.0.18") == kf.FIXED_UNVERIFIED
    for fid in ("KIT-GF-025", "KIT-GF-028", "KIT-GF-047", "KIT-GF-050"):
        assert by_id[fid].effective_status("1.0.18") == kf.FIXED_NOT_INSTALLED   # fixed in 1.0.19
    for fid in ("KIT-GF-022", "KIT-GF-048"):                               # fixed in 1.0.20
        assert by_id[fid].effective_status("1.0.18") == kf.FIXED_NOT_INSTALLED
    assert by_id["KIT-GF-049"].effective_status("1.0.18") == kf.VERIFIED   # fixed in 1.0.21, GF-E089


def test_the_real_register_tracks_the_kit_1_0_19_adoption():
    """Kit 1.0.19 (2026-10-06): five fixes released, four findings from its first public run."""
    by_id = {f.id: f for f in kf.load(ROOT)}
    assert by_id["KIT-GF-024"].effective_status("1.0.19") == kf.VERIFIED       # GF-E076
    for fid in ("KIT-GF-025", "KIT-GF-028", "KIT-GF-047", "KIT-GF-050"):
        assert by_id[fid].effective_status("1.0.19") == kf.FIXED_UNVERIFIED
        assert by_id[fid].kit["fixed_in"] == "1.0.19"
    for fid in ("KIT-GF-048", "KIT-GF-053", "KIT-GF-054", "KIT-GF-055", "KIT-GF-056"):
        assert by_id[fid].effective_status("1.0.19") == kf.FIXED_NOT_INSTALLED, fid   # fixed in 1.0.20
    assert by_id["KIT-GF-052"].effective_status("1.0.19") == kf.FIXED_NOT_INSTALLED   # fixed in 1.0.21
    assert by_id["KIT-GF-049"].effective_status("1.0.19") == kf.VERIFIED              # GF-E089
    assert by_id["KIT-GF-051"].effective_status("1.0.19") == kf.OPEN


def test_the_real_register_tracks_the_kit_1_0_20_adoption():
    """Kit 1.0.20 (2026-10-08): ten fixes released; GF-057 verified at adoption (GF-E080)."""
    by_id = {f.id: f for f in kf.load(ROOT)}
    assert by_id["KIT-GF-057"].effective_status("1.0.20") == kf.VERIFIED
    for fid in ("KIT-GF-022", "KIT-GF-048", "KIT-GF-053", "KIT-GF-054", "KIT-GF-055",
                "KIT-GF-056", "KIT-GF-058", "KIT-GF-059"):
        assert by_id[fid].effective_status("1.0.20") == kf.FIXED_UNVERIFIED, fid
        assert by_id[fid].kit["fixed_in"] == "1.0.20"
    assert by_id["KIT-GF-051"].effective_status("1.0.20") == kf.OPEN
    # P11c retest (GF-E081): the GitHub route still ran the Kit-repository reference check here.
    assert by_id["KIT-GF-049"].reproduced_in == "1.0.20"
    for fid in ("KIT-GF-052", "KIT-GF-035"):                               # fixed later (1.0.21 / main)
        assert by_id[fid].effective_status("1.0.20") == kf.FIXED_NOT_INSTALLED, fid


def test_the_real_register_tracks_the_kit_1_0_21_adoption():
    """Kit 1.0.21 (2026-10-09, GF-E087): four fixes released, GF-023/035 only on Kit main."""
    by_id = {f.id: f for f in kf.load(ROOT)}
    for fid in ("KIT-GF-049", "KIT-GF-052", "KIT-GF-060", "KIT-GF-061"):
        assert by_id[fid].fixed_in == "1.0.21" and by_id[fid].kit["fixed_in"] == "1.0.21", fid
    for fid in ("KIT-GF-049", "KIT-GF-060"):                                  # GF-E089 rehearsal
        assert by_id[fid].effective_status("1.0.21") == kf.VERIFIED, fid
    for fid in ("KIT-GF-052", "KIT-GF-061"):
        assert by_id[fid].effective_status("1.0.21") == kf.FIXED_UNVERIFIED, fid
    for fid in ("KIT-GF-023", "KIT-GF-035"):                                  # Kit main, unreleased
        assert by_id[fid].effective_status("1.0.21") == kf.FIXED_NOT_INSTALLED, fid
    for fid in ("KIT-GF-051", "KIT-GF-062", "KIT-GF-063", "KIT-GF-064"):
        assert by_id[fid].effective_status("1.0.21") == kf.OPEN, fid


def test_window_filters_and_shows_details(tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    try:
        register = tmp_path / kf.REGISTER
        register.parent.mkdir(parents=True)
        register.write_text(json.dumps({"families": [
            {"id": "KIT-GF-A", "title": "open one", "severity": "critical", "status": "OPEN",
             "observed": "seen", "first_observed": "2026-10-01"},
            {"id": "KIT-GF-B", "title": "fixed one", "severity": "low", "status": "FIXED", "fixed_in": "2.0.0"},
        ]}))
        from agp_cockpit.ui.kit_findings_window import KitFindingsWindow
        window = KitFindingsWindow(root, repository_root=tmp_path, installed_version="1.0.13")
        assert window.tree.get_children() == ("KIT-GF-A",)          # default filter: open
        assert "Beobachtet:\nseen" in window.detail.get("1.0", "end")
        window.filter_var.set("Behoben")
        window.populate()
        assert window.tree.get_children() == ("KIT-GF-B",)
        assert window.tree.item("KIT-GF-B")["values"][3] == kf.FIXED_NOT_INSTALLED
        window.filter_var.set("Alle")
        window.populate()
        assert len(window.tree.get_children()) == 2
        assert "2 Befunde · 1 offen" in window.summary_var.get()
    finally:
        root.destroy()


def test_system_tab_has_the_buttons():
    source = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert 'text="Kit-Befunde …"' in source and 'text="Aufräumen …"' in source


# --- AGP_MAINTENANCE_CLEANUP_V1 -------------------------------------------------

def _touch(path: Path, age_days: float, now: float, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    stamp = now - age_days * 86400
    os.utime(path, (stamp, stamp))
    return path


def test_plan_keeps_recent_steps_young_files_and_run_next(tmp_path):
    now = time.time()
    for step in range(1, 61):
        _touch(tmp_path / "Download" / f"{step}_x.py", 40, now)
    _touch(tmp_path / "Download" / "run_next.py", 400, now)
    _touch(tmp_path / "Download" / "5_young.json", 1, now)
    _touch(tmp_path / ".local/agp-cockpit/delivery/1_x_return_bundle.json", 40, now)
    _touch(tmp_path / ".local/agp-cockpit/delivery/9_x_return_bundle.json", 2, now)
    _touch(tmp_path / ".local/agp-cockpit/tmp/1550/a.txt", 3, now)
    os.utime(tmp_path / ".local/agp-cockpit/tmp/1550", (now - 3 * 86400,) * 2)
    _touch(tmp_path / ".local/agp-cockpit/archive/cited-evidence/1099_x.json", 400, now)
    result = mt.plan(tmp_path, now=now)
    names = {c.path.name for c in result.candidates}
    assert names >= {f"{step}_x.py" for step in range(1, 11)}          # steps 1-10 are outside the newest 50
    assert "11_x.py" not in names and "run_next.py" not in names and "5_young.json" not in names
    assert "1_x_return_bundle.json" in names and "9_x_return_bundle.json" not in names
    assert "1550" in names and "1099_x.json" not in names
    assert result.kit_argv is None and "Kit nicht gefunden" in mt.describe(result)


def test_execute_deletes_only_what_a_fresh_plan_still_lists(tmp_path):
    now = time.time()
    for step in range(1, 56):
        _touch(tmp_path / "Download" / f"{step}_x.py", 40, now)
    approved = mt.plan(tmp_path, now=now)
    assert {c.path.name for c in approved.candidates} == {f"{s}_x.py" for s in range(1, 6)}
    _touch(tmp_path / "Download" / "3_x.py", 0, now)              # touched again after the preview
    outcome = mt.execute(tmp_path, approved, now=now)
    assert outcome["deleted"] == 4 and (tmp_path / "Download/3_x.py").exists()
    assert not (tmp_path / "Download/1_x.py").exists() and (tmp_path / "Download/6_x.py").exists()
    assert any(s.endswith("3_x.py") for s in outcome["skipped"])


def test_kit_gc_previews_and_then_executes(tmp_path):
    calls = []

    def runner(argv, **_):
        calls.append(argv[1:])
        return SimpleNamespace(returncode=0, stdout="TMP_LOG_GC\nSTATUS=DRY_RUN\n", stderr="")

    result = mt.plan(tmp_path, kit_binary=Path("/k/agentic-kit"), runner=runner)
    assert calls == [["artifact-gc", "--tmp-logs"]] and "DRY_RUN" in result.kit_preview
    mt.execute(tmp_path, result, runner=runner)
    assert calls[-1] == ["artifact-gc", "--tmp-logs", "--execute"]
