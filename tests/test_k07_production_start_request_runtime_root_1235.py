from pathlib import Path

def test_production_root():
 from agp_cockpit.adapters.macos_settings import bridge_runtime_root
 from agp_cockpit.core.start_request import StartRequestStore
 root=bridge_runtime_root()
 assert "Application Support/AGP Cockpit/bridge" in str(root)
 assert StartRequestStore(root).path == root/"task_start_request.json"

def test_bootstrap_root():
 s=Path("src/agp_cockpit/app_bootstrap.py").read_text()
 assert "runtime_root=require_stable_production_runtime_root(bridge_runtime_root())" in s
