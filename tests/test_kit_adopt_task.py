"""AGP_KIT_ADOPT_TASK_V1 (owner 2026-10-30/31, option B part 2): „Kit übernehmen“ asks the Kit whether a newer
stable release exists. Nothing to adopt: an information window and no task. A newer release for a wheel
install: a confirmed task that adopts exactly that version through the Kit's own update route; the signed
execute is the owner's decision (gated in code), the changes stay on chore/kit-<version> for „Abschließen“."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import kit_release as kr
from agp_cockpit.core import repo_state as rs
from agp_cockpit.core import standard_tasks as st
from agp_cockpit.core import standard_verifier as sv
from agp_cockpit.core.kit_command_catalog import (
    KitCommandCatalog,
    destructive_execute_commands,
)
from agp_cockpit.core.verbs import BY_KEY as VERBS
from agp_cockpit.core.verbs import availability

ROOT = Path(__file__).resolve().parents[1]
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
TASK = st.BY_KEY["kit-adopt"]


def _answer(release, monkeypatch, version="1.1.9"):
    from agp_cockpit.core import kit_installation
    monkeypatch.setattr(kit_installation, "discover",
                        lambda _root: SimpleNamespace(version=version, binary=Path("/venv/bin/agentic-kit")))

    def run(argv, **_kwargs):
        return subprocess.CompletedProcess(argv, 0, json.dumps({"result_status": "PASS", "release_check": release}), "")
    return run


def test_the_release_answer_decides_whether_anything_starts(monkeypatch, tmp_path):
    newer = kr.read(tmp_path, runner=_answer({"installed": "1.1.9", "latest_release": "1.1.10",
                                               "installation_kind": "wheel", "result": "UPDATE_AVAILABLE"},
                                              monkeypatch))
    assert newer.adoptable and newer.latest == "1.1.10"
    for release, words in (
            ({"installed": "1.1.9", "latest_release": "1.1.9", "installation_kind": "wheel", "result": "CURRENT"},
             "neueste stabile Release"),
            ({"installed": "1.1.9", "latest_release": "1.1.10", "installation_kind": "editable",
              "result": "UPDATE_AVAILABLE"}, "Wiederherstellen"),
            ({"installed": "1.1.8", "latest_release": "1.1.9", "installation_kind": "editable",
              "result": "UPDATE_AVAILABLE"}, "KIT-GF-093"),
            ({"result": "UNKNOWN", "reason": "index_unavailable:TimeoutError"}, "nicht prüfbar")):
        found = kr.read(tmp_path, runner=_answer(release, monkeypatch))
        assert not found.adoptable, release
        assert words in kr.info_text(found), (release, kr.info_text(found))


def test_the_verb_is_offered_on_ready_main_only():
    verb = VERBS[rs.KIT_UEBERNEHMEN]
    assert verb.task_key == "kit-adopt" and verb.group == "weitere" and verb.slice is None
    assert rs.KIT_UEBERNEHMEN in rs.OFFERED[rs.BEREIT] and rs.KIT_UEBERNEHMEN not in rs.OFFERED[rs.IN_ARBEIT]
    ready = rs.RepoState(rs.BEREIT, "", None, rs.OFFERED[rs.BEREIT])
    assert availability(verb, ready)[0]


def test_the_start_click_approves_only_the_branch_and_the_execute_stays_the_owners():
    assert TASK.scope(ROOT, {"version": "1.1.10"}) == st.WORK_START_SCOPE
    assert not any("kit update" in name for name in st.WORK_START_SCOPE)
    catalog = KitCommandCatalog.load(ROOT)
    plan = 'import subprocess\nsubprocess.run(["agentic-kit", "kit", "update", "--version", "1.1.10", "--json"])\n'
    signed = ('import subprocess\nsubprocess.run(["agentic-kit", "kit", "update", "--version", "1.1.10", '
              '"--execute", "--expected-signature", "abc", "--json"])\n')
    assert destructive_execute_commands(plan, catalog) == []
    assert destructive_execute_commands(signed, catalog) == ["agentic-kit kit update --execute"]


def test_prompt_and_contract_name_the_exact_version_and_no_kit_command():
    prompt = TASK.prompt(ROOT, {"version": "1.1.10"})
    assert "chore/kit-1.1.10" in prompt and "exactly version 1.1.10" in prompt and "NEEDS_HUMAN" in prompt
    assert "command digest" in prompt and "agentic-kit kit update" not in prompt and "work start" not in prompt
    contract = TASK.contract(ROOT, {"version": "1.1.10"})
    assert contract["completion_contract"]["verifier"] == "kit-adopted"
    assert contract["completion_contract"]["params"] == {"branch": "chore/kit-1.1.10", "version": "1.1.10"}
    assert not TASK.follow_up        # the star follows the repository state (AGP_NO_CHAT_SWITCH_FOLLOW_UP_V1)


def _git(root, *args):
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env=ENV, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _repo(tmp_path):
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    (work / "f.txt").write_text("1\n")
    _git(work, "add", ".")
    _git(work, "commit", "-qm", "c1")
    _git(work, "push", "-q", "origin", "HEAD:main")
    return work


def test_the_precheck_needs_ready_main_and_the_kits_current_answer(monkeypatch, tmp_path):
    work = _repo(tmp_path)
    newer = kr.KitRelease(kr.UPDATE_AVAILABLE, "1.1.9", "1.1.10", "1.1.9", False)
    monkeypatch.setattr(kr, "read", lambda _root, **_k: newer)
    assert "Kit-Version fehlt" in TASK.check(work, {})
    assert TASK.check(work, {"version": "1.1.10"}) is None
    assert "nicht 1.1.11" in TASK.check(work, {"version": "1.1.11"})
    monkeypatch.setattr(kr, "read", lambda _root, **_k: kr.KitRelease(kr.CURRENT, "1.1.10", "1.1.10", "1.1.10"))
    assert "Nichts zu übernehmen" in TASK.check(work, {"version": "1.1.10"})
    monkeypatch.setattr(kr, "read", lambda _root, **_k: newer)
    _git(work, "switch", "-qc", "chore/kit-1.1.10")
    assert "nur auf main" in TASK.check(work, {"version": "1.1.10"})
    _git(work, "switch", "-q", "main")
    assert "existiert schon" in TASK.check(work, {"version": "1.1.10"})


def test_the_verifier_needs_branch_changes_installed_kit_and_pins(tmp_path):
    work = _repo(tmp_path)
    branch = "chore/kit-1.1.10"
    ok = lambda **kw: sv.verify_kit_adopted(work, branch=branch, version="1.1.10", **kw)
    assert "expected chore/kit-1.1.10" in ok(installed="1.1.10", pins={"1.1.10"})[1]
    _git(work, "switch", "-qc", branch)
    assert "carries no changes" in ok(installed="1.1.10", pins={"1.1.10"})[1]
    (work / "AGENTS.md").write_text("manifest\n")
    assert ok(installed="1.1.9", pins={"1.1.10"}) == (False, "the installed Kit is 1.1.9, expected 1.1.10")
    assert "CI pins name 1.1.9" in ok(installed="1.1.10", pins={"1.1.9"})[1]
    assert ok(installed="1.1.10", pins={"1.1.10"})[0]
    verdict = sv.verify(work, {"verifier": "kit-adopted", "params": {"branch": branch, "version": "1.1.10"}})
    assert verdict[0] is False      # the real discovery finds no Kit in this fixture


def test_the_panel_informs_or_confirms_the_exact_version(monkeypatch, tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    try:
        from agp_cockpit.ui import standard_tasks_panel as m
        monkeypatch.setattr(m, "bridge_status", lambda: {"mission": None})
        panel = m.StandardTasksPanel(root, repository_root=tmp_path, on_open_work=lambda: None)
        shown, asked, started = [], [], []
        monkeypatch.setattr(panel, "_show_info", lambda title, text: shown.append(text))
        monkeypatch.setattr(panel, "_ask_ok", lambda title, text: asked.append(text) or True)
        monkeypatch.setattr(panel, "start_standard_task", lambda task, inputs: started.append(inputs) or True)
        assert panel.kit_adopt_answer(TASK, kr.KitRelease(kr.CURRENT, "1.1.9", "1.1.9", "1.1.9")) is False
        assert "neueste stabile Release" in shown[-1] and not asked and not started
        assert panel.kit_adopt_answer(TASK, kr.KitRelease(kr.UPDATE_AVAILABLE, "1.1.9", "1.1.10", "1.1.9")) is True
        assert asked[-1].startswith("Kit 1.1.9 → 1.1.10 übernehmen?") and started == [{"version": "1.1.10"}]
        monkeypatch.setattr(panel, "_ask_ok", lambda title, text: False)
        assert panel.kit_adopt_answer(TASK, kr.KitRelease(kr.UPDATE_AVAILABLE, "1.1.9", "1.1.10", "1.1.9")) is False
        assert len(started) == 1 and "nicht gestartet" in panel.status_var.get()
        source = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
        run_verb = source[source.index("def run_verb("):source.index("def run_kit_adopt(")]
        assert run_verb.index('task.key == "kit-adopt"') < run_verb.index("self.ask_inputs(task)")
        assert "threading.Thread(target=ask" in source    # the index request never blocks the UI thread
    finally:
        root.destroy()
