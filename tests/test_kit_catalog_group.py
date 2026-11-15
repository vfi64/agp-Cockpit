"""AGP_KIT_CATALOG_GROUP_V1 (workflow-friction plan C5).

The findings window read only the Cockpit's register, which lists findings a Cockpit slice entered; the Kit's
catalog has more (KIT-GF-090, 096-098, 100-120 at Kit 1.4.0). The installed Kit answers ``greenfield status
--json`` (K9), and entries the register does not list are a group of their own. The Cockpit reads only id,
title, Kit state, fixed in and the report name, judges nothing and never writes them into its register.
"""
from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import kit_findings as kf

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path("/venv/bin/agentic-kit")

CATALOG = {
    "schema_version": 1, "kind": "external_findings_status", "counts": {"CLOSED": 3},
    "findings": [
        {"id": "KIT-GF-1", "title": "in the register", "kit_state": "CLOSED", "fixed_in": "1.0.0",
         "report": "docs/reports/a.json", "external_retest": {"commands": ["x"]}, "prs": [1]},
        {"id": "KIT-GF-109", "title": "pip cache in injected CI", "kit_state": "CLOSED", "fixed_in": "1.4.0",
         "report": "docs/reports/k.json", "external_retest": {"commands": ["agentic-kit check"]}, "prs": [2810]},
        {"id": "KIT-GF-090", "title": "missing release tags", "kit_state": "CLOSED", "fixed_in": "1.1.8",
         "report": "docs/reports/t.json", "kit_release_evidence": {"x": 1}},
    ],
}


def _register(root: Path, *families: dict) -> None:
    path = root / kf.REGISTER
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"families": list(families)}), encoding="utf-8")


def _kit(monkeypatch, version: str = "1.4.0") -> None:
    import agp_cockpit.core.kit_installation as ki
    monkeypatch.setattr(ki, "discover", lambda root: SimpleNamespace(binary=BINARY, version=version))


def _answer(stdout: str = "", stderr: str = "", returncode: int = 0):
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, returncode, stdout, stderr)
    return runner, calls


def test_the_installed_kit_is_asked_for_its_catalog_read_only(monkeypatch, tmp_path):
    _kit(monkeypatch)
    runner, calls = _answer(json.dumps(CATALOG, indent=2))
    catalog = kf.read_catalog(tmp_path, runner=runner)
    ((argv, kwargs),) = calls
    assert argv == [str(BINARY), "greenfield", "status", "--json"]
    assert kwargs["cwd"] == str(tmp_path) and kwargs["timeout"] == kf.CATALOG_TIMEOUT and kwargs["check"] is False
    assert not catalog.reason
    assert [e["id"] for e in catalog.entries] == ["KIT-GF-1", "KIT-GF-109", "KIT-GF-090"]
    # only the four fields and the report name are read; retest contracts, PRs and evidence stay in the Kit
    assert all(set(e) == {"id", "title", "kit_state", "fixed_in", "report"} for e in catalog.entries)


@pytest.mark.parametrize("stdout,stderr,returncode,expected", [
    (json.dumps({"result_status": "BLOCKED", "error": "invalid finding status"}), "", 2,
     "greenfield status lieferte keinen Katalog: invalid finding status"),
    ("Usage: agentic-kit [OPTIONS]", "Error: No such command 'greenfield'.", 2,
     "greenfield status lieferte keinen Katalog: Error: No such command 'greenfield'."),
    ("", "", 0, "greenfield status lieferte keinen Katalog"),
    (json.dumps({"findings": "none"}), "", 0, "greenfield status lieferte keinen Katalog"),
])
def test_an_unusable_answer_gives_a_reason_and_no_entries(monkeypatch, tmp_path, stdout, stderr, returncode,
                                                          expected):
    _kit(monkeypatch)
    runner, _ = _answer(stdout, stderr, returncode)
    catalog = kf.read_catalog(tmp_path, runner=runner)
    assert catalog.entries == () and catalog.reason == expected


def test_no_kit_or_no_answer_gives_a_reason(monkeypatch, tmp_path):
    import agp_cockpit.core.kit_installation as ki
    monkeypatch.setattr(ki, "discover", lambda root: None)
    assert kf.read_catalog(tmp_path, runner=lambda *a, **k: pytest.fail("no Kit, no call")).reason == \
        "kein Kit installiert"
    _kit(monkeypatch)

    def slow(argv, **kwargs):
        raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
    assert kf.read_catalog(tmp_path, runner=slow).reason == "das Kit antwortet nicht (TimeoutExpired)"


def test_only_entries_missing_in_the_register_form_the_group_and_the_register_wins(monkeypatch, tmp_path):
    _register(tmp_path, {"id": "KIT-GF-1", "title": "the register's title", "severity": "low", "status": "OPEN",
                         "first_observed": "2026-10-01"})
    _kit(monkeypatch)
    runner, _ = _answer(json.dumps(CATALOG))
    register = kf.load(tmp_path)
    extra = kf.catalog_only(register, kf.read_catalog(tmp_path, runner=runner))
    assert [f.id for f in extra] == ["KIT-GF-109", "KIT-GF-090"]
    assert all(f.origin == kf.KIT_CATALOG and f.severity == "" and f.first_observed == "" for f in extra)
    assert register[0].title == "the register's title" and register[0].origin == kf.REGISTER_ORIGIN
    assert register[0].effective_status("1.4.0") == kf.OPEN            # the Kit's CLOSED does not touch it
    # the register file is never written
    assert json.loads((tmp_path / kf.REGISTER).read_text())["families"][0]["title"] == "the register's title"
    assert kf.catalog_only(register, None) == [] and kf.catalog_only(register, kf.KitCatalog(reason="x")) == []


@pytest.mark.parametrize("state,fixed_in,installed,expected", [
    ("CLOSED", "1.3.0", "1.4.0", kf.FIXED_UNVERIFIED),
    ("CLOSED", "1.4.0", "1.3.0", kf.FIXED_NOT_INSTALLED),
    ("CLOSED", "unreleased", "9.9.9", kf.FIXED_NOT_INSTALLED),
    ("PARTIAL", "", "1.4.0", kf.IN_PROGRESS),
    ("OPEN", "", "1.4.0", kf.OPEN),
    ("NOT_APPLICABLE", "", "1.4.0", kf.NOT_APPLICABLE),
])
def test_the_status_of_a_catalog_entry_is_the_kits_state_against_the_installed_kit(state, fixed_in, installed,
                                                                                    expected):
    catalog = kf.KitCatalog(entries=({"id": "KIT-GF-200", "title": "t", "kit_state": state, "fixed_in": fixed_in,
                                      "report": ""},))
    (finding,) = kf.catalog_only([], catalog)
    assert finding.effective_status(installed) == expected


def test_the_detail_names_the_kit_as_source(monkeypatch, tmp_path):
    _kit(monkeypatch)
    runner, _ = _answer(json.dumps(CATALOG))
    extra = kf.catalog_only([], kf.read_catalog(tmp_path, runner=runner))
    text = next(f for f in extra if f.id == "KIT-GF-109").detail_text("1.4.0")
    assert text.startswith("KIT-GF-109 — pip cache in injected CI")
    assert "Status: behoben, nicht bestätigt (Kit-Katalog: CLOSED, behoben in 1.4.0)" in text
    assert "Nur im Kit-Katalog" in text and "agentic-kit greenfield status" in text
    assert "Bericht im Kit-Repo: docs/reports/k.json" in text
    assert "Schwere" not in text and "Register:" not in text


def test_the_summary_line_of_the_catalog():
    entries = tuple({"id": f"KIT-GF-{n}", "title": "", "kit_state": "CLOSED", "fixed_in": "", "report": ""}
                    for n in (1, 2, 3))
    catalog = kf.KitCatalog(entries=entries)
    assert kf.catalog_summary([], None) == "Kit-Katalog wird gelesen …"
    assert kf.catalog_summary([], kf.KitCatalog(reason="kein Kit installiert")) == \
        "Kit-Katalog nicht gelesen: kein Kit installiert"
    assert kf.catalog_summary([], catalog) == "Kit-Katalog: 3 Einträge, alle auch im Register"
    assert kf.catalog_summary(kf.catalog_only([], catalog)[:2], catalog) == \
        "Kit-Katalog: 2 von 3 Einträgen fehlen im Register (eigene Gruppe „Nur im Kit-Katalog“)"


def test_the_real_register_misses_what_the_group_shows():
    """Plan section 3: the register has no entry for KIT-GF-090 and KIT-GF-100 to 108, so only the group shows them."""
    known = {f.id for f in kf.load(ROOT)}
    assert not known & {"KIT-GF-090", *(f"KIT-GF-{n}" for n in range(100, 109))}


def _tk_root():
    tk = pytest.importorskip("tkinter")
    try:
        return tk.Tk()
    except tk.TclError:
        pytest.skip("no display")


def _wait(window, condition, seconds: float = 5.0) -> None:
    deadline = time.monotonic() + seconds
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("timeout")
        window.update()
        time.sleep(0.02)


def test_window_shows_the_catalog_group_below_the_register(tmp_path):
    root = _tk_root()
    try:
        _register(tmp_path,
                  {"id": "KIT-GF-1", "title": "open one", "severity": "low", "status": "OPEN", "first_observed": "x"},
                  {"id": "KIT-GF-5", "title": "fixed one", "severity": "low", "status": "FIXED", "fixed_in": "1.0.0"})
        seen = []

        def reader(path):
            seen.append((path, threading.current_thread() is threading.main_thread()))
            return kf.KitCatalog(entries=tuple(
                {k: e[k] for k in ("id", "title", "kit_state", "fixed_in", "report")} for e in CATALOG["findings"]))
        from agp_cockpit.ui.kit_findings_window import CATALOG_GROUP, KitFindingsWindow
        window = KitFindingsWindow(root, repository_root=tmp_path, installed_version="1.3.0", catalog_reader=reader)
        _wait(window, lambda: window.catalog is not None)
        assert seen == [(tmp_path, False)]                          # beside the UI thread, a plain path only
        assert window.catalog_var.get() == \
            "Kit-Katalog: 2 von 3 Einträgen fehlen im Register (eigene Gruppe „Nur im Kit-Katalog“)"
        assert window.tree.get_children() == ("KIT-GF-1",)           # default filter "Offen": no catalog row is open
        window.filter_var.set("Behoben")
        window.populate()
        assert window.tree.get_children() == ("KIT-GF-5", CATALOG_GROUP)
        assert window.tree.get_children(CATALOG_GROUP) == ("KIT-GF-090", "KIT-GF-109")   # by number
        assert window.tree.item(CATALOG_GROUP)["open"]
        assert window.tree.item("KIT-GF-109")["values"][3] == kf.FIXED_NOT_INSTALLED       # 1.4.0 > 1.3.0
        assert window.tree.item("KIT-GF-090")["values"][3] == kf.FIXED_UNVERIFIED          # 1.1.8 <= 1.3.0
        window.sort_by("id")                                          # reversed: the group stays below
        assert window.tree.get_children() == ("KIT-GF-5", CATALOG_GROUP)
        assert window.tree.get_children(CATALOG_GROUP) == ("KIT-GF-109", "KIT-GF-090")
        window.tree.selection_set("KIT-GF-109")
        window.show_selected()
        assert "Nur im Kit-Katalog" in window.detail.get("1.0", "end")
        window.tree.selection_set(CATALOG_GROUP)
        window.show_selected()
        assert window.detail.get("1.0", "end").startswith("Nur im Kit-Katalog: Diese Befunde")
        window.update_idletasks()
        assert window.tree.bbox("KIT-GF-109")                      # the rows below the group are shown
    finally:
        root.destroy()


def test_window_without_a_catalog_shows_the_reason_and_no_group(tmp_path):
    root = _tk_root()
    try:
        _register(tmp_path, {"id": "KIT-GF-1", "title": "open one", "severity": "low", "status": "OPEN"})
        from agp_cockpit.ui.kit_findings_window import CATALOG_GROUP, KitFindingsWindow
        window = KitFindingsWindow(root, repository_root=tmp_path, installed_version=None,
                                   catalog_reader=lambda path: kf.KitCatalog(reason="kein Kit installiert"))
        _wait(window, lambda: window.catalog is not None)
        window.filter_var.set("Alle")
        window.populate()
        assert window.tree.get_children() == ("KIT-GF-1",) and not window.tree.exists(CATALOG_GROUP)
        assert window.catalog_var.get() == "Kit-Katalog nicht gelesen: kein Kit installiert"
    finally:
        root.destroy()


def test_the_worker_touches_no_tk_object():
    """AGP_TK_GC_ON_MAIN_THREAD_V1: the worker's frame holds the reader, a path and the holder, never the window."""
    source = (ROOT / "src/agp_cockpit/ui/kit_findings_window.py").read_text(encoding="utf-8")
    worker = source.split("def load_catalog", 1)[1].split("def work() -> None:", 1)[1].split("def poll()", 1)[0]
    assert "self" not in worker and "reader(root)" in worker
