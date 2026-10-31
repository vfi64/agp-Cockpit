"""AGP_SYSTEM_CHECK_V1: read-only checks with a fix for every problem."""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import system_check as sc

ROOT = Path(__file__).resolve().parents[1]


def test_a_broken_check_is_a_finding_not_a_crash():
    def boom(_root):
        raise RuntimeError("kaputt")
    results = sc.run_all(Path("/r"), checks=(lambda _r: sc.Check("A", sc.OK, "gut"), boom))
    assert [r.level for r in results] == [sc.OK, sc.FAIL]
    assert results[1].name == "Bridge" and "kaputt" in results[1].detail and results[1].fix
    assert sc.summary(results).endswith("1 Problem(e), 0 Hinweis(e) — Lösungswege stehen dabei.")
    assert sc.summary(results[:1]).endswith("alles in Ordnung.")
    assert sc.summary([sc.Check("x", sc.WARN, "")]).endswith("alles nutzbar, 1 Hinweis(e).")


def test_every_check_has_a_name_in_order():
    assert len(sc.CHECKS) == len(sc.NAMES)


def test_github_cli(monkeypatch, tmp_path):
    assert sc._github_cli(tmp_path).level == sc.WARN            # conftest: AGP_COCKPIT_GH_BINARY=none
    monkeypatch.setenv("AGP_COCKPIT_GH_BINARY", "/usr/bin/gh")
    ok = lambda argv, **_k: subprocess.CompletedProcess(argv, 0, "", "")
    assert sc._github_cli(tmp_path, runner=ok).level == sc.OK
    no = lambda argv, **_k: subprocess.CompletedProcess(argv, 1, "", "not logged in")
    check = sc._github_cli(tmp_path, runner=no)
    assert check.level == sc.FAIL and check.fix == "Im Terminal: gh auth login"


def test_kit_version_against_the_ci_pin(monkeypatch, tmp_path):
    from agp_cockpit.core import kit_installation
    (tmp_path / "src/agp_cockpit").mkdir(parents=True)
    (tmp_path / "src/agp_cockpit/version.py").write_text('BRIDGE_BUILD_ID = "x"\n', encoding="utf-8")
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / ".github/workflows/gate.yaml").write_text('pip install "agentic-project-kit==1.0.19"\n',
                                                         encoding="utf-8")
    monkeypatch.setattr(kit_installation, "discover", lambda _root: SimpleNamespace(version="1.0.19"))
    assert sc._kit(tmp_path).level == sc.OK
    monkeypatch.setattr(kit_installation, "discover", lambda _root: SimpleNamespace(version="1.0.20"))
    check = sc._kit(tmp_path)
    assert check.level == sc.WARN and "1.0.19" in check.detail
    monkeypatch.setattr(kit_installation, "discover", lambda _root: None)
    assert sc._kit(tmp_path).level == sc.FAIL


def test_extension_names_the_fix(monkeypatch, tmp_path):
    from agp_cockpit.core import runtime_identity
    monkeypatch.setattr(runtime_identity, "runtime_identity_status",
                        lambda *_a, **_k: {"ready": False, "reasons": ["handshake-stale"]})
    check = sc._extension(tmp_path)
    assert check.level == sc.FAIL and check.fix == "Den ChatGPT-Tab in Chrome neu laden."
    monkeypatch.setattr(runtime_identity, "runtime_identity_status",
                        lambda *_a, **_k: {"ready": True, "handshake_build_id": "release-0.2.2-r16"})
    assert sc._extension(tmp_path).detail == "meldet Build release-0.2.2-r16"


def test_disk_and_repository(monkeypatch, tmp_path):
    monkeypatch.setattr(sc.shutil, "disk_usage", lambda _p: SimpleNamespace(free=1024 ** 3))
    assert sc._disk(tmp_path).level == sc.WARN
    monkeypatch.setattr(sc.shutil, "disk_usage", lambda _p: SimpleNamespace(free=50 * 1024 ** 3))
    assert sc._disk(tmp_path).detail == "50 GB frei"
    assert sc._repository(tmp_path).level == sc.FAIL               # not a git checkout
    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "-c", "user.name=t", "-c", "user.email=t@e.invalid",
                    "commit", "-q", "--allow-empty", "-m", "x"], check=True)
    assert sc._repository(tmp_path).level == sc.OK
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    assert sc._repository(tmp_path).level == sc.WARN


def test_the_window_shows_marks_and_fixes():
    import tkinter as tk

    from agp_cockpit.ui.system_check_window import SystemCheckWindow
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    try:
        results = [sc.Check("Bridge", sc.OK, "erreichbar"),
                   sc.Check("GitHub-CLI", sc.FAIL, "nicht angemeldet", "Im Terminal: gh auth login")]
        window = SystemCheckWindow(root, repository_root=Path("/r"), run=lambda _p: results)
        for _ in range(50):
            root.update()
            if window.results:
                break
            root.after(20)
        texts = [w.cget("text") for w in window.body.winfo_children()]
        assert "✗" in texts and "GitHub-CLI" in texts and "nicht angemeldet\n→ Im Terminal: gh auth login" in texts
        assert window.summary_var.get().endswith("1 Problem(e), 0 Hinweis(e) — Lösungswege stehen dabei.")
        assert str(window.again_button.cget("state")) == "normal"
    finally:
        root.destroy()


def test_the_system_tab_offers_the_check():
    source = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert 'text="Systemcheck …", command=self.open_system_check' in source


def test_kit_release_shows_the_kits_own_answer(monkeypatch, tmp_path):
    """AGP_KIT_RELEASE_CHECK_V1: the line repeats `kit status --check-release` (KIT-GF-092); the Cockpit never
    asks the package index itself."""
    import json

    from agp_cockpit.core import kit_installation
    monkeypatch.setattr(kit_installation, "discover",
                        lambda _root: SimpleNamespace(version="1.1.9", binary=Path("/venv/bin/agentic-kit")))
    calls = []

    def answer(release, rc=0, stderr=""):
        def run(argv, **kwargs):
            calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, rc, json.dumps({"result_status": "PASS", "release_check": release})
                                               if release is not None else "", stderr)
        return run

    current = sc._kit_release(tmp_path, runner=answer({"installed": "1.1.9", "latest_release": "1.1.9",
                                                         "installation_kind": "wheel", "result": "CURRENT"}))
    assert current.level == sc.OK and "neueste stabile Release" in current.detail
    argv, kwargs = calls[-1]
    assert argv == ["/venv/bin/agentic-kit", "kit", "status", "--root", str(tmp_path), "--check-release", "--json"]
    assert kwargs["cwd"] == str(tmp_path) and kwargs["timeout"] == sc.KIT_RELEASE_TIMEOUT
    newer = sc._kit_release(tmp_path, runner=answer({"installed": "1.1.9", "latest_release": "1.1.10",
                                                       "installation_kind": "wheel", "result": "UPDATE_AVAILABLE"}))
    assert newer.level == sc.WARN and "1.1.10 verfügbar" in newer.detail and "übernehmen" in newer.fix
    editable = sc._kit_release(tmp_path, runner=answer({"installed": "1.1.9", "latest_release": "1.1.10",
                                                          "installation_kind": "editable",
                                                          "result": "UPDATE_AVAILABLE"}))
    assert "Wiederherstellen" in editable.fix
    stale = sc._kit_release(tmp_path, runner=answer({"installed": "1.1.4", "latest_release": "1.1.9",
                                                       "installation_kind": "editable",
                                                       "result": "UPDATE_AVAILABLE"}))
    assert stale.level == sc.WARN and "veralteten Paketdaten" in stale.detail and "KIT-GF-093" in stale.fix
    assert "Wiederherstellen" not in stale.fix          # never advise a pull the checkout does not need
    ahead = sc._kit_release(tmp_path, runner=answer({"installed": "1.1.9", "latest_release": "1.1.8",
                                                       "installation_kind": "editable", "result": "AHEAD"}))
    assert ahead.level == sc.OK and "Entwicklerinstallation" in ahead.detail
    offline = sc._kit_release(tmp_path, runner=answer({"result": "UNKNOWN", "reason": "index_unavailable:TimeoutError"}))
    assert offline.level == sc.WARN and "index_unavailable" in offline.detail and "Netz" in offline.fix
    old = sc._kit_release(tmp_path, runner=answer(None, rc=2, stderr="No such option: --check-release"))
    assert old.level == sc.WARN and "ab Kit 1.1.9" in old.detail

    def hang(argv, **_kwargs):
        raise subprocess.TimeoutExpired(argv, sc.KIT_RELEASE_TIMEOUT)
    assert sc._kit_release(tmp_path, runner=hang).level == sc.WARN
    monkeypatch.setattr(kit_installation, "discover", lambda _root: None)
    assert sc._kit_release(tmp_path).level == sc.WARN


def test_the_cockpit_does_not_query_the_package_index_itself():
    source = (ROOT / "src/agp_cockpit/core/system_check.py").read_text(encoding="utf-8")
    assert "pypi" not in source.lower() and "urllib" not in source and "--check-release" in source
