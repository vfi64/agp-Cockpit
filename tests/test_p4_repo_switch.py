"""Plan P4 Repo wechseln (AGP_REPOSITORY_SWITCH_V1, AGP_CONVERSATION_BINDING_V1)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import repository_switch as rsw
from agp_cockpit.core.conversation_binding import (
    ConversationBindingStore,
    conversation_id,
)

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def make_repo(base: Path, name: str, *, origin=True, workspace=True) -> Path:
    root = base / name          # conftest puts HOME into tmp_path
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "a.txt").write_text("a\n")
    if workspace:
        (root / ".agentic").mkdir()
        (root / ".agentic" / "config.yaml").write_text("x: 1\n")
    git(root, "add", "-A")
    git(root, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    if origin:
        git(root, "remote", "add", "origin", "https://github.com/example/repo.git")
    return root


KIT = SimpleNamespace(version="1.0.13")


def test_check_blocks_what_cannot_be_steered(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert rsw.check(tmp_path / "missing").blockers == ("Ordner existiert nicht.",)
    assert rsw.check(plain).blockers == ("Kein git-Repository.",)
    repo = make_repo(tmp_path, "r", origin=False)
    result = rsw.check(repo, kit_discover=lambda _r: KIT, gh_status=lambda _r: True)
    assert not result.ok and "origin" in result.blockers[0]
    assert rsw.check(repo, current=repo).blockers == ("Das ist bereits das aktuelle Repository.",)


def test_check_warns_for_missing_kit_workspace_and_gh(tmp_path):
    repo = make_repo(tmp_path, "r", workspace=False)
    result = rsw.check(repo, kit_discover=lambda _r: None, gh_status=lambda _r: False)
    assert result.ok
    assert any("nicht installiert" in w for w in result.warnings)
    assert any("KEIN_KIT" in w for w in result.warnings)
    assert any("gh ist nicht angemeldet" in w for w in result.warnings)
    assert "neuen ChatGPT-Chat" in result.text()


def test_provision_writes_only_untracked_transport_paths(tmp_path):
    repo = make_repo(tmp_path, "r")
    runner = ROOT / "Download" / "run_next.py"
    actions = rsw.provision(repo, runner_source=runner)
    assert (repo / "Download" / "run_next.py").read_bytes() == runner.read_bytes()
    assert any("info/exclude" in a for a in actions)
    (repo / ".local" / "agp-cockpit").mkdir(parents=True)
    (repo / ".local" / "agp-cockpit" / "x.json").write_text("{}")
    status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True,
                            check=True)
    assert status.stdout == ""                       # nothing visible to git or the Kit
    assert rsw.provision(repo, runner_source=runner) == []   # idempotent


def test_provision_never_overwrites_a_tracked_runner_or_the_cockpit_checkout(tmp_path):
    repo = make_repo(tmp_path, "r")
    (repo / "Download").mkdir()
    (repo / "Download" / "run_next.py").write_text("# theirs\n")
    git(repo, "add", "-A")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "runner")
    with pytest.raises(PermissionError):
        rsw.provision(repo, runner_source=ROOT / "Download" / "run_next.py")
    assert rsw.provision(ROOT) == []


def test_canonical_runner_is_the_versioned_one():
    assert rsw.canonical_runner() == ROOT / "Download" / "run_next.py"


def test_recent_list_dedupes_orders_and_limits(tmp_path):
    for i in range(10):
        rsw.remember(tmp_path, tmp_path / f"r{i}")
    rsw.remember(tmp_path, tmp_path / "r3")
    items = rsw.load_recent(tmp_path)
    assert len(items) == rsw.RECENT_LIMIT and items[0].endswith("r3") and items.count(items[0]) == 1


def test_conversation_binding(tmp_path):
    store = ConversationBindingStore(tmp_path)
    assert conversation_id("https://chatgpt.com/") == ""
    assert store.bind("https://chatgpt.com/", Path("/a")) is False          # fresh chat, no id yet
    assert store.bind("https://chatgpt.com/c/abc", Path("/a")) is True
    assert store.bind("https://chatgpt.com/c/abc?model=x", Path("/b")) is False   # never rebinds
    assert store.block_reason("https://chatgpt.com/c/abc", Path("/a")) is None
    assert "neuen Chat" in store.block_reason("https://chatgpt.com/c/abc", Path("/b"))


def test_existing_bridge_is_reused_only_for_the_same_repository(tmp_path):
    from agp_cockpit.app_bootstrap import bridge_serves_repository
    payload = {"runtime": {"repository_root": str(tmp_path)}, "contract": {"repository_root": str(tmp_path)}}
    assert bridge_serves_repository(payload, tmp_path)
    assert not bridge_serves_repository(payload, tmp_path / "other")
    assert not bridge_serves_repository({}, tmp_path)


def test_any_git_work_tree_is_a_repository_context(tmp_path):
    from agp_cockpit.adapters.macos_context import looks_like_repository_context
    plain = tmp_path / "plain"
    plain.mkdir()
    assert not looks_like_repository_context(plain)
    assert looks_like_repository_context(make_repo(tmp_path, "r", workspace=False))


def test_relaunch_command():
    from agp_cockpit.adapters.macos_relaunch import relaunch_command
    frozen = relaunch_command(frozen=True, executable="/x/AGP Cockpit.app/Contents/MacOS/AGP Cockpit")
    assert frozen[:2] == ["/bin/sh", "-c"] and "open -n '/x/AGP Cockpit.app'" in frozen[2]
    assert frozen[2].startswith("sleep 3;")
    source = relaunch_command(frozen=False, executable="/usr/bin/python3")
    assert source[2].endswith("-m agp_cockpit")


def test_perform_switch_order_and_failure(tmp_path):
    from agp_cockpit.ui.repo_switch_dialog import perform_switch
    current = make_repo(tmp_path, "current")
    target = make_repo(tmp_path, "target")
    calls = []
    ok = rsw.SwitchCheck(str(target), facts={"workspace": "ja"})
    actions = perform_switch(target, current=current, app_support=tmp_path / "as",
                             persist=lambda root: calls.append(("persist", root)),
                             relaunch=lambda: calls.append(("relaunch",)),
                             check=lambda c, current: ok, provision=lambda root: ["prov"])
    assert actions == ["prov"] and calls == [("persist", target), ("relaunch",)]
    assert rsw.load_recent(tmp_path / "as")[:2] == [str(target), str(current)]
    bad = rsw.SwitchCheck(str(target), blockers=("Kein git-Repository.",))
    calls.clear()
    with pytest.raises(ValueError):
        perform_switch(target, current=current, app_support=tmp_path / "as", persist=calls.append,
                       relaunch=lambda: calls.append("r"), check=lambda c, current: bad)
    assert calls == []


def test_staged_extension_marker_follows_the_repository(tmp_path):
    from agp_cockpit.adapters import macos_extension as me
    first = me.stage_extension(ROOT)
    other = make_repo(tmp_path, "other")
    again = me.stage_extension(other)
    marker = json.loads((again / ".agp-stage.json").read_text())
    assert again == first and marker["repository_root"] == str(other.resolve())
    assert marker["run_next"] == str(other.resolve() / "Download" / "run_next.py")


def test_freshness_guard_compares_with_the_cockpit_checkout_in_other_repositories(tmp_path):
    from agp_cockpit.core.build_freshness import freshness_root
    assert freshness_root(ROOT) == ROOT
    assert freshness_root(make_repo(tmp_path, "other")) == ROOT


def test_packaged_app_carries_the_runner():
    spec = (ROOT / "packaging" / "macos" / "agp_cockpit.spec").read_text()
    assert '"run_next.py"), "runner")' in spec


def test_dialog_enables_switch_only_for_a_passing_check(tmp_path):
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display")
    from agp_cockpit.ui.repo_switch_dialog import RepoSwitchDialog
    switched = []
    results = {"good": rsw.SwitchCheck(str(tmp_path / "good")),
               "bad": rsw.SwitchCheck(str(tmp_path / "bad"), blockers=("Kein git-Repository.",))}
    dialog = RepoSwitchDialog(root, current=tmp_path / "cur", app_support=tmp_path / "as",
                              on_switch=lambda r: switched.append(r) or ["x"],
                              check=lambda c, current: results[Path(c).name])
    dialog.evaluate(tmp_path / "bad")
    assert str(dialog.switch_button["state"]) == "disabled" and "✗ Kein git-Repository." in dialog.report.get()
    dialog.evaluate(tmp_path / "good")
    assert str(dialog.switch_button["state"]) == "normal"
    dialog._switch()
    assert switched == [tmp_path / "good"] and "startet neu" in dialog.report.get()
    root.destroy()
    del dialog, root
    import gc
    gc.collect()
