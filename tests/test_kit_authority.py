"""Plan P1: the installed Kit is the command authority (R1), standard tasks run
orchestrators (R2), unknown effects ask (R3), violations are corrected, not fatal."""
from __future__ import annotations

import json
import stat
from pathlib import Path
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core import kit_installation
from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.kit_command_catalog import (
    KitCommandCatalog,
    command_catalog_violations,
    orchestrator_violations,
    remote_effect_commands,
    unknown_effect_commands,
)
from agp_cockpit.core.start_request import StartRequestStore


def entry(path, surface="primitive", safety="BOUNDED", replaces=()):
    return {"qualified_name": "agentic-kit " + " ".join(path), "path": list(path), "surface": surface,
            "safety": safety, "replaces_raw": list(replaces), "params": []}


MANIFEST = {"meta": {"manifest_sha": "installed1"}, "commands": [
    entry(["work", "finish"], "orchestrator"),
    entry(["transfer", "chat-switch-complete"], "orchestrator"),
    entry(["transfer", "push-current"], replaces=["git push"]),
    entry(["transfer", "divergence-status"], "diagnostic", "READ_ONLY"),
    entry(["magic", "deploy"], "orchestrator"),          # new, unclassified orchestrator
]}


def work_order(*argvs):
    kits = "\n".join(f"K{i} = {json.dumps(['agentic-kit', *a])}" for i, a in enumerate(argvs))
    return (
        "import argparse, subprocess\nfrom pathlib import Path\n" + kits + "\n"
        'RETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n    p = argparse.ArgumentParser()\n"
        '    p.add_argument("--self-test", action="store_true")\n    p.parse_args()\n'
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n    main()\n'
    )


@pytest.fixture
def installed_kit(tmp_path, monkeypatch):
    """A Kit 'installation' whose interpreter answers the manifest probe."""
    manifest = tmp_path / "site" / "agentic-kit-commands.json"
    manifest.parent.mkdir()
    manifest.write_text(json.dumps(MANIFEST))
    interpreter = tmp_path / "kitpython"
    interpreter.write_text("#!/bin/sh\n" + f"echo '{{\"version\": \"9.9.9\", \"manifest\": \"{manifest}\"}}'\n")
    interpreter.chmod(interpreter.stat().st_mode | stat.S_IEXEC)
    binary = tmp_path / "agentic-kit"
    binary.write_text(f"#!{interpreter}\n")
    monkeypatch.setenv("AGP_COCKPIT_KIT_BINARY", str(binary))
    kit_installation._CACHE.clear()
    return binary


def test_the_installed_kit_manifest_wins_over_the_repository_copy(tmp_path, installed_kit):
    repo = tmp_path / "repo"
    (repo / "docs/reference").mkdir(parents=True)
    (repo / "docs/reference/agentic-kit-commands.json").write_text(
        json.dumps({"meta": {"manifest_sha": "stale"}, "commands": []}))
    catalog = KitCommandCatalog.load(repo)
    assert catalog.manifest_sha == "installed1"
    assert catalog.source == "installed agentic-kit 9.9.9"
    assert catalog.digest()["source"] == "installed agentic-kit 9.9.9"


def test_without_an_installed_kit_the_repository_copy_is_the_fallback(tmp_path):
    (tmp_path / "docs/reference").mkdir(parents=True)
    (tmp_path / "docs/reference/agentic-kit-commands.json").write_text(json.dumps(MANIFEST))
    catalog = KitCommandCatalog.load(tmp_path)          # conftest: discovery disabled
    assert catalog.source == "docs/reference/agentic-kit-commands.json"


def test_unknown_orchestrator_effect_counts_as_remote_and_is_marked(tmp_path):
    catalog = KitCommandCatalog.from_data(MANIFEST, "test")
    source = work_order(["magic", "deploy"])
    assert remote_effect_commands(source, catalog) == ["agentic-kit magic deploy"]
    assert unknown_effect_commands(source, catalog) == ["agentic-kit magic deploy"]
    marked = {c["command"]: c for c in catalog.digest()["commands"]}
    assert marked["agentic-kit magic deploy"]["effect"] == "unknown"
    assert "effect" not in marked["agentic-kit transfer chat-switch-complete"]
    assert not remote_effect_commands(work_order(["transfer", "chat-switch-complete"]), catalog)


def test_standard_task_work_orders_need_an_orchestrator_and_no_remote_primitive():
    catalog = KitCommandCatalog.from_data(MANIFEST, "test")
    assert orchestrator_violations(work_order(["transfer", "divergence-status"]), catalog)
    assert orchestrator_violations(work_order(["transfer", "chat-switch-complete"]), catalog) == []
    both = orchestrator_violations(work_order(["work", "finish"], ["transfer", "push-current"]), catalog)
    assert any("push-current has a remote effect" in v for v in both)
    # free tasks keep the old rule set
    assert command_catalog_violations(work_order(["transfer", "divergence-status"]), catalog) == []


# --- HTTP: correction instead of a fatal stop ---------------------------------

RUNNER = (
    "import sys, json\nfrom pathlib import Path\n"
    "n=int(sys.argv[1]);d=Path(__file__).parent\n"
    "(d/f'{n:03d}_ok_return_bundle.json').write_text(json.dumps({'status':'PASS'}))\n"
)


@pytest.fixture
def bridge(tmp_path):
    (tmp_path / "Download").mkdir()
    (tmp_path / "Download" / "run_next.py").write_text(RUNNER)
    (tmp_path / "Download" / "1479_previous.py").write_text("# executed\n")
    (tmp_path / "docs/reference").mkdir(parents=True)
    (tmp_path / "docs/reference/agentic-kit-commands.json").write_text(json.dumps(MANIFEST))
    server = BridgeRuntimeServer(tmp_path, port=0)
    info = server.start()

    def call(path, payload=None):
        request = Request(f"http://127.0.0.1:{info.port}{path}", method="POST" if payload is not None else "GET",
                          data=None if payload is None else json.dumps(payload).encode(),
                          headers={"X-AGP-Token": info.token, "Content-Type": "application/json"})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode())

    try:
        yield tmp_path, server.local_root, call
    finally:
        server.stop()


def standard_mission(call, runtime, title="Standard · Chat wechseln"):
    created = call("/v1/mission", {"title": title, "mission_text": "m", "execution_mode": "LIVE",
                                    "run_mode": "FULL_AUTO"})["mission"]
    StartRequestStore(runtime).request(created["mission_id"], task_id="T")
    return created["mission_id"]


def test_http_standard_task_without_orchestrator_is_corrected_then_bounded(bridge):
    root, runtime, call = bridge
    standard_mission(call, runtime)
    for attempt in range(1, 4):
        step = call("/v1/status")["next_local_step"]
        answer = call("/v1/file-loop/command", {
            "filename": f"{step}_status.py",
            "content": work_order(["transfer", "divergence-status"]) + f"# {attempt}\n"})
        assert answer["state"] == "CONTINUE" and "orchestrator" in answer["prompt"]
        assert answer["next_step"] == step + 1
        assert (root / "Download" / f"{step}_agp_rejected.json").is_file()
    step = call("/v1/status")["next_local_step"]
    final = call("/v1/file-loop/command", {"filename": f"{step}_status.py",
                                           "content": work_order(["transfer", "divergence-status"]) + "# 4\n"})
    assert final["state"] == "NEEDS_HUMAN" and final["terminal"] is True
    assert call("/v1/status")["mission"]["state"] == "NEEDS_HUMAN"


def test_http_standard_task_with_orchestrator_runs(bridge):
    root, runtime, call = bridge
    standard_mission(call, runtime)
    ran = call("/v1/file-loop/command", {"filename": "1480_switch.py",
                                         "content": work_order(["transfer", "chat-switch-complete"])})
    assert ran["state"] != "CONTINUE" and ran.get("terminal") is not True
    assert list((root / "Download").glob("1480_*return_bundle.json"))


def test_http_free_task_unknown_command_is_corrected_not_fatal(bridge):
    _root, runtime, call = bridge
    standard_mission(call, runtime, title="Task · frei")
    answer = call("/v1/file-loop/command", {"filename": "1480_x.py",
                                            "content": work_order(["no", "such"])})
    assert answer["state"] == "CONTINUE" and "unknown agentic-kit command" in answer["prompt"]


def test_status_names_the_installed_kit_digest(bridge, installed_kit):
    _root, _runtime, call = bridge
    status = call("/v1/status")
    digest = json.loads(Path(status["kit_command_digest_path"]).read_text())
    assert status["kit_manifest_sha"] == "installed1"
    assert digest["source"] == "installed agentic-kit 9.9.9"


def test_the_version_is_the_running_package_and_follows_its_init(tmp_path, monkeypatch):
    """AGP_KIT_RUNTIME_VERSION_V1: an editable install keeps the metadata of its install time."""
    import os
    import time
    from types import SimpleNamespace

    from agp_cockpit.core import system_check
    manifest = tmp_path / "agentic-kit-commands.json"
    manifest.write_text(json.dumps(MANIFEST))
    init = tmp_path / "__init__.py"
    init.write_text('__version__ = "1.1.5"\n')
    answer = tmp_path / "answer.json"
    answer.write_text(json.dumps({"version": "1.1.5", "metadata_version": "1.1.4",
                                  "package_init": str(init), "manifest": str(manifest)}))
    interpreter = tmp_path / "kitpython"
    interpreter.write_text(f"#!/bin/sh\ncat '{answer}'\n")
    interpreter.chmod(interpreter.stat().st_mode | stat.S_IEXEC)
    binary = tmp_path / "agentic-kit"
    binary.write_text(f"#!{interpreter}\n")
    monkeypatch.setenv("AGP_COCKPIT_KIT_BINARY", str(binary))
    kit_installation._CACHE.clear()
    kit = kit_installation.discover(tmp_path)
    assert (kit.version, kit.metadata_version) == ("1.1.5", "1.1.4")
    assert "import agentic_project_kit as k" in kit_installation.PROBE
    assert "getattr(k, '__version__', '') or meta" in kit_installation.PROBE
    answer.write_text(answer.read_text().replace('"version": "1.1.5"', '"version": "1.1.6"'))
    assert kit_installation.discover(tmp_path).version == "1.1.5"            # cached while unchanged
    later = time.time_ns() + 10**9
    os.utime(init, ns=(later, later))                                        # a pull changed the package
    assert kit_installation.discover(tmp_path).version == "1.1.6"
    monkeypatch.setattr(kit_installation, "discover",
                        lambda _root: SimpleNamespace(version="1.1.5", metadata_version="1.1.4"))
    monkeypatch.setattr(system_check, "ci_kit_pins", lambda _root: set())
    check = system_check._kit(tmp_path)
    assert check.detail == "1.1.5 · Entwicklerinstallation (Paketangabe 1.1.4)"
