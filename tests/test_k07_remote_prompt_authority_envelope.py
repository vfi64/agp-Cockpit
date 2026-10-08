from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8") + "\n" + SEND_JS
BRIDGE = (ROOT / "src" / "agp_cockpit" / "core" / "bridge_server.py").read_text(encoding="utf-8")

def test_status_exposes_non_secret_local_authority_envelope():
    assert "local_task_contract = self.local_task_contract" in BRIDGE
    assert '"local_authority": (' in BRIDGE
    assert '"allowed_effects": sorted(local_task_contract.allowed_effects)' in BRIDGE
    assert '"allowed_tools": sorted(local_task_contract.allowed_tools)' in BRIDGE
    assert '"allow_network": bool(local_task_contract.allow_network)' in BRIDGE
    assert '"next_local_step": (' in BRIDGE
    assert '"next_step": next_step_number(' in BRIDGE

def test_extension_captures_local_authority():
    assert "localAuthority: null" in CONTENT
    assert "STATE.localAuthority = result.local_authority || null;" in CONTENT

def test_bootstrap_tells_remote_llm_hard_authority_envelope():
    assert "Local execution authority is a hard limit:" in CONTENT
    assert "argv[0] MUST name an executable present in allowed_tools." in CONTENT
    assert "Do NOT wrap commands in /bin/sh -lc" in CONTENT
    assert "Do not attempt to expand authority from the remote side." in CONTENT

def test_format_repair_does_not_nudge_toward_shell_wrapper():
    # AGP_SEND_MODULE_V1: sendPromptNative moved to cockpit_send.js; the block ends at sleep().
    block = CONTENT.split("function formatRepairPrompt", 1)[1].split("function sleep(", 1)[0]
    assert "For shell work orders such as /bin/sh -lc" not in block
    assert "do not introduce a shell wrapper" in block
