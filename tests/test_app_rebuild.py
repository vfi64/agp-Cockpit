"""AGP_REBUILD_BUTTON_V1 (owner 2026-10-05): rebuild and restart from the app."""

import os
import stat
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import app_rebuild as ar
from agp_cockpit.core.build_freshness import BuildFreshness

ROOT = Path(__file__).resolve().parents[1]


def fresh(running, bundle, source, stale=True):
    return BuildFreshness(running, bundle, source, stale, "m")


def test_offer_names_the_step_the_guard_asks_for():
    assert ar.offer(None) == "" and ar.offer(fresh("r1", "r1", "r1", stale=False)) == ""
    assert ar.offer(fresh("r1", "r1", "r2")) == ar.BUILD          # branch with a new build id checked out
    assert ar.offer(fresh("r1", "r2", "r2")) == ar.RESTART        # built in the terminal, app not restarted
    assert ar.offer(fresh("r1", "r2", "r3")) == ar.BUILD          # the bundle is already behind the source
    assert ar.offer(fresh("r1", "", "r2")) == ar.BUILD
    assert ar.label(ar.BUILD) == "Neu bauen und neu starten" and ar.label(ar.RESTART) == "Neu starten"


def test_build_runs_the_projects_own_script_without_restart(tmp_path):
    cmd = ar.command(tmp_path)
    assert cmd == [str(tmp_path / ".venv/bin/python"), str(tmp_path / "scripts/build_macos_app.py")]
    assert "--restart" not in cmd   # the app closes itself; no Apple Event to quit it


def test_block_reasons(tmp_path):
    assert "Task läuft" in ar.block_reason(tmp_path, task_running=True)
    assert "nicht bekannt" in ar.block_reason(None, task_running=False)
    assert "Kein Python" in ar.block_reason(tmp_path, task_running=False)
    (tmp_path / ".venv/bin").mkdir(parents=True)
    (tmp_path / ".venv/bin/python").write_text("")
    assert "Build-Skript fehlt" in ar.block_reason(tmp_path, task_running=False)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/build_macos_app.py").write_text("")
    assert ar.block_reason(tmp_path, task_running=False) == ""
    assert "Kein App-Bundle" in ar.block_reason(tmp_path, task_running=False, kind=ar.RESTART)
    ar.bundle_of(tmp_path).mkdir(parents=True)
    assert ar.block_reason(tmp_path, task_running=False, kind=ar.RESTART) == ""


def test_child_env_drops_the_frozen_apps_variables(tmp_path):
    env = ar.child_env(tmp_path, {"PATH": "/usr/bin", "_PYI_APPLICATION_HOME_DIR": "x", "_MEIPASS2": "y",
                                  "PYTHONHOME": "z", "DYLD_LIBRARY_PATH": "w", "HOME": "/h"})
    assert not any(k.startswith(("_PYI", "_MEI")) for k in env)
    assert "PYTHONHOME" not in env and "DYLD_LIBRARY_PATH" not in env and env["HOME"] == "/h"
    assert env["PATH"].split(os.pathsep)[0] == str(tmp_path / ".venv" / "bin")


def test_start_detaches_and_logs(tmp_path):
    seen = {}

    def popen(argv, **kw):
        seen.update(kw, argv=argv)
        kw["stdout"].write("built\n")
        return SimpleNamespace(poll=lambda: 0)

    rebuild = ar.start(tmp_path, popen=popen, now=lambda _fmt: "20261005-210000")
    assert seen["start_new_session"] is True and seen["cwd"] == str(tmp_path)
    assert rebuild.log == tmp_path / ".local/agp-cockpit/logs/rebuild-20261005-210000.log"
    assert rebuild.returncode() == 0 and rebuild.tail() == "built"


def test_relaunch_needs_a_bundle_and_detaches(tmp_path):
    with pytest.raises(FileNotFoundError):
        ar.relaunch(tmp_path, 1, popen=lambda *a, **k: None)
    exe = ar.bundle_of(tmp_path) / "Contents/MacOS/AGP Cockpit"
    exe.parent.mkdir(parents=True)
    exe.write_text("")
    seen = {}
    ar.relaunch(tmp_path, 4242, popen=lambda argv, **kw: seen.update(kw, argv=argv))
    assert seen["start_new_session"] is True
    assert seen["argv"][:2] == ["/bin/sh", "-c"] and seen["argv"][-2:] == ["4242", str(ar.bundle_of(tmp_path))]


@pytest.mark.skipif(not Path("/bin/sh").exists(), reason="needs /bin/sh")
def test_relauncher_opens_the_bundle_only_after_the_app_ended(tmp_path):
    fake_open = tmp_path / "bin" / "open"
    fake_open.parent.mkdir()
    marker = tmp_path / "opened"
    fake_open.write_text(f'#!/bin/sh\necho "$1" > "{marker}"\n')
    fake_open.chmod(fake_open.stat().st_mode | stat.S_IEXEC)
    app = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1.5)"])
    env = {**os.environ, "PATH": f"{fake_open.parent}{os.pathsep}{os.environ.get('PATH', '')}"}
    helper = subprocess.Popen(ar.relaunch_command(tmp_path / "AGP Cockpit.app", app.pid), env=env)
    time.sleep(0.6)
    assert not marker.exists()          # the app still runs
    app.wait()
    helper.wait(timeout=10)
    assert marker.read_text().strip() == str(tmp_path / "AGP Cockpit.app")


def test_failed_build_keeps_the_app_and_its_note():
    from agp_cockpit.ui.main_window import MainWindow
    calls = []
    window = SimpleNamespace(
        _rebuild=SimpleNamespace(returncode=lambda: 2, log=Path("/x/rebuild.log"), tail=lambda: "boom",
                                 cause=lambda: ""),
        _rebuild_note="", freshness_var=SimpleNamespace(set=calls.append),
        _rebuild_button=SimpleNamespace(configure=lambda **kw: calls.append(kw)),
        _relaunch_new_build=lambda _home: calls.append("relaunch"), after=lambda *a: calls.append("after"))
    MainWindow._watch_rebuild(window)
    assert window._rebuild is None and "fehlgeschlagen" in window._rebuild_note and "Code 2" in window._rebuild_note
    assert window._rebuild_note.count("\n") == 1 and "rebuild.log" in window._rebuild_note
    assert {"state": "normal"} in calls and "relaunch" not in calls


def test_window_wiring():
    window = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert "AGP_REBUILD_BUTTON_V1" in window and "self.winfo_toplevel().destroy" in window
    assert "osascript" not in window and "task_running()" in window
    assert 'getattr(sys, "frozen", False)' in window   # a source run never rebuilds the bundle


def test_child_env_drops_the_frozen_tcl_paths_live_2026_10_06(tmp_path):
    bundle = "/u/agp/.local/agp-cockpit/dist/AGP Cockpit.app/Contents/Frameworks"
    env = ar.child_env(tmp_path, {"PATH": "/usr/bin", "TCL_LIBRARY": f"{bundle}/_tcl_data",
                                  "TK_LIBRARY": f"{bundle}/_tk_data", "TCLLIBPATH": "x"})
    assert not {"TCL_LIBRARY", "TK_LIBRARY", "TCLLIBPATH"} & set(env)


def test_cause_names_the_root_exception(tmp_path):
    log = tmp_path / "rebuild.log"
    log.write_text("4103 INFO: x\nTraceback (most recent call last):\n  File x\nValueError: Resource '/a/_tcl_data/auto.tcl' "
                   "is not a valid file!\nTraceback (most recent call last):\nsubprocess.CalledProcessError: Command "
                   "'[...]' returned non-zero exit status 1.\n")
    rebuild = ar.Rebuild(ar.BUILD, log, None)
    assert rebuild.cause().startswith("ValueError: Resource")
