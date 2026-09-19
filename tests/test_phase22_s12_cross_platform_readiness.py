import platform
from pathlib import Path


def test_s12_contract_does_not_claim_native_windows_or_linux_support():
    text=Path("docs/planning/CROSS_PLATFORM_READINESS.md").read_text()
    assert "PORTABLE_CORE_READY" in text
    assert "WINDOWS_PRODUCT_READY" in text and "LINUX_PRODUCT_READY" in text
    assert "not implied" in text
    assert "must not claim Windows or Linux product support" in text

def test_portable_task_core_has_no_direct_macos_runtime_dependency():
    for rel in [
        "src/agp_cockpit/core/task_models.py",
        "src/agp_cockpit/core/task_store.py",
        "src/agp_cockpit/core/task_controller.py",
    ]:
        text=Path(rel).read_text()
        for forbidden in ("/usr/bin/osascript","Application Support","macos_runtime","macos_chatgpt"):
            assert forbidden not in text, (rel, forbidden)

def test_macos_runtime_adapter_fails_closed_off_darwin(monkeypatch):
    from agp_cockpit.adapters import macos_runtime
    monkeypatch.setattr(platform,"system",lambda:"Linux")
    assert macos_runtime.is_macos() is False
    try:
        macos_runtime.discover_macos_runtime()
    except RuntimeError as exc:
        assert "non-macOS" in str(exc)
    else:
        raise AssertionError("macOS adapter must fail closed on non-Darwin")

def test_non_darwin_portable_durable_controller_smoke(monkeypatch,tmp_path):
    monkeypatch.setattr(platform,"system",lambda:"Linux")
    from agp_cockpit.core.task_controller import DurableTaskController
    c=DurableTaskController("s12-portable",tmp_path/"portable.sqlite")
    assert c.snapshot["state"] in {"ACTIVE","WAITING_FOR_REMOTE"}
    epoch=c.bind_remote_context("portable-simulated-remote")
    assert epoch == 1
    assert c.binding_has_execution_authority(epoch)
    refreshed=c.remote_context_refresh()
    assert refreshed["task_id"]=="s12-portable"

def test_existing_first_run_diagnostics_explicitly_classify_non_macos():
    text=Path("src/agp_cockpit/first_run_diagnostics.py").read_text()
    assert "platform.system()" in text
    assert "Current v0.1 desktop target is macOS." in text
    assert "macOS user-settings location is not authoritative on this host." in text
