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
                        lambda *_a, **_k: {"ready": True, "handshake_build_id": "release-0.2.2-r13"})
    assert sc._extension(tmp_path).detail == "meldet Build release-0.2.2-r13"


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
