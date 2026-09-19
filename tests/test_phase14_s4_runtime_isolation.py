from pathlib import Path

import pytest

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.runtime_root_policy import (
    UnsafeRuntimeRoot,
    require_stable_production_runtime_root,
)


def test_injected_runtime_root_is_separate_from_repo(tmp_path):
    repo=tmp_path/"repo"; repo.mkdir(); rr=tmp_path/"runtime"
    runtime=BridgeRuntimeServer(repo,port=0,runtime_root=rr)
    assert runtime.local_root == rr.resolve()
    assert (rr/"token.txt").is_file()
    assert not (repo/".local/agp-cockpit/bridge/token.txt").exists()

@pytest.mark.parametrize("p",[Path("/tmp/agp"),Path("/private/tmp/agp"),Path("/private/var/folders/x/y/T/pytest-of-user/pytest-1/test_app")])
def test_transient_production_root_rejected(p):
    with pytest.raises(UnsafeRuntimeRoot): require_stable_production_runtime_root(p)

def test_stable_application_support_like_root_accepted(monkeypatch):
    monkeypatch.setenv("HOME", "/Users/agp-cockpit-test-user")
    p=Path.home()/"Library"/"Application Support"/"AGP Cockpit"/"bridge"
    assert require_stable_production_runtime_root(p)==p.resolve()

def test_stop_is_idempotent(tmp_path):
    r=BridgeRuntimeServer(tmp_path,port=0,runtime_root=tmp_path/"runtime"); r.start(); r.stop(); r.stop()
    assert r.server._server is None and r.server._thread is None
