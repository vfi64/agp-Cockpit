from __future__ import annotations

import json
import urllib.request
from pathlib import Path

from agp_cockpit.adapters.macos_settings import bridge_token_path

# AGP_START_WAITS_FOR_EXTENSION_V1 (live 2026-10-07, r5): „Abschließen“ was clicked seven
# seconds after „Neu bauen und neu starten“, while the Chrome extension still reported r4; the
# bridge refused the start (handshake-build-id-mismatch) one second before the extension came
# up with r5. These reasons settle by themselves within seconds after a rebuild or restart.
SETTLING_REASONS = ("handshake-build-id-mismatch", "handshake-version-mismatch",
                    "handshake-stale", "fresh-extension-handshake-missing")
SETTLE_ATTEMPTS = 30          # one per second
GATE_ENV = "AGP_COCKPIT_EXTENSION_GATE"


def extension_settling(repository_root: Path) -> str:
    """The extension reasons that will settle after a rebuild, "" when the extension is current."""
    import os
    if os.environ.get(GATE_ENV) == "off":   # tests without a browser (tests/conftest.py)
        return ""
    from agp_cockpit.adapters.macos_settings import bridge_runtime_root
    from agp_cockpit.core.runtime_identity import runtime_identity_status
    try:
        identity = runtime_identity_status(Path(repository_root), bridge_runtime_root())
    except Exception:  # noqa: BLE001 - the bridge decides at the start request
        return ""
    if identity.get("ready"):
        return ""
    return ", ".join(r for r in identity.get("reasons", []) if r in SETTLING_REASONS)


def request_task_start(mission_id:str,*,task_id:str='',base_url:str='http://127.0.0.1:9876')->dict:
    """Ask the bridge to start ``mission_id``.

    AGP_START_ABANDONS_ON_FAILURE_V1 (live 2026-10-07, r5): a refused start left the mission
    that the Cockpit had just created on READY; READY counts as running, so it blocked every
    new start until the owner stopped it in the browser. A refused start now stops exactly
    that mission (the bridge ignores the stop when another mission is current)."""
    token=bridge_token_path().read_text(encoding='utf-8').strip()
    req=urllib.request.Request(
        base_url+'/v1/task/start-request',
        data=json.dumps({'mission_id':mission_id,'task_id':task_id}).encode(),
        headers={'Content-Type':'application/json','X-AGP-Token':token},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req,timeout=5) as resp: return json.loads(resp.read().decode())
    except Exception as exc:
        abandon_mission(mission_id, f"Start abgelehnt: {exc}", base_url=base_url)
        raise


def abandon_mission(mission_id: str, reason: str, *, base_url: str = 'http://127.0.0.1:9876') -> bool:
    """Stop ``mission_id`` if it is still the current mission; True when the bridge stopped it."""
    try:
        token = bridge_token_path().read_text(encoding='utf-8').strip()
        req = urllib.request.Request(
            base_url + '/v1/file-loop/control',
            data=json.dumps({'action': 'STOP', 'reason': reason[:300], 'mission_id': mission_id}).encode(),
            headers={'Content-Type': 'application/json', 'X-AGP-Token': token},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode()).get('mission_state') == 'STOPPED'
    except Exception:  # noqa: BLE001 - best effort; the start failure itself is reported
        return False
