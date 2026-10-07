"""What the Cockpit learns about the ChatGPT page, without changing the transport.

AGP_UI_FINGERPRINT_V1 (DOM hardening step 5, owner 2026-10-07): every mission start sends the
touchpoint self-test with a fingerprint of the composer's structure (data-testid values and
the touchpoint counts, never text). A new fingerprint is a new ChatGPT UI variant; it is
recorded with its time, so a later transport failure can be related to a UI change instead
of being found by trial in DevTools.

AGP_DOM_SHAPE_SNAPSHOT_V1 (step 2): a failure after the start sends a sanitized shape of the
composer form and of the last assistant turn (tags, roles, test ids, short labels; no text).
The bridge keeps the newest ones as files beside its log, not inside the log.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from agp_cockpit.core.runtime_paths import runtime_dir

VARIANT_FILE = ("browser", "ui-variant.json")
SNAPSHOT_DIR = ("browser", "dom-snapshots")
KEEP_SNAPSHOTS = 30
NEW_VARIANT_SECONDS = 24 * 3600


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_variant(repository_root: Path) -> dict:
    try:
        data = json.loads(runtime_dir(repository_root, *VARIANT_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def record_variant(repository_root: Path, details: dict, *, now: float | None = None) -> dict | None:
    """Store the fingerprint of a touchpoint self-test; the change when it is new, else None."""
    fingerprint = str(details.get("fingerprint") or "").strip()[:64]
    if not fingerprint:
        return None
    current = read_variant(repository_root)
    if current.get("fingerprint") == fingerprint:
        return None
    stamp = time.time() if now is None else now
    signature = details.get("ui_signature")
    record = {
        "fingerprint": fingerprint,
        "signature": [str(item)[:80] for item in signature][:60] if isinstance(signature, list) else [],
        "since": stamp,
        "previous": str(current.get("fingerprint") or ""),
        "previous_signature": current.get("signature") or [],
    }
    _write_json(runtime_dir(repository_root, *VARIANT_FILE), record)
    return record


def variant_line(repository_root: Path, *, now: float | None = None) -> str:
    """One line for the System tab: the current ChatGPT UI variant and since when."""
    data = read_variant(repository_root)
    fingerprint = str(data.get("fingerprint") or "")
    if not fingerprint:
        return "ChatGPT-Oberfläche: noch keine Variante erfasst (nach dem nächsten Task-Start)"
    since = float(data.get("since") or 0)
    when = time.strftime("%d.%m. %H:%M", time.localtime(since)) if since else "?"
    line = f"ChatGPT-Oberfläche: Variante {fingerprint[:8]} · seit {when}"
    stamp = time.time() if now is None else now
    if data.get("previous") and since and stamp - since < NEW_VARIANT_SECONDS:
        line += f" · NEU (vorher {str(data['previous'])[:8]})"
    return line


def store_dom_shape(repository_root: Path, event: str, details: dict, *,
                    now: float | None = None) -> dict:
    """Move a ``dom_shape`` out of the event details into its own file (newest 30 kept)."""
    shape = details.get("dom_shape")
    if not isinstance(shape, dict):
        return details
    stamp = time.time() if now is None else now
    folder = runtime_dir(repository_root, *SNAPSHOT_DIR)
    safe_event = "".join(c if c.isalnum() or c in "_-" else "_" for c in str(event))[:60] or "EVENT"
    name = (time.strftime("%Y%m%d-%H%M%S", time.localtime(stamp))
            + f"-{int(stamp * 1000) % 1000:03d}-{safe_event}.json")
    payload = {"event": event, "time": stamp, "mission_id": str(details.get("mission_id") or ""),
               "message": str(details.get("message") or details.get("reason") or "")[:500],
               "shape": shape}
    _write_json(folder / name, payload)
    for old in sorted(folder.glob("*.json"))[:-KEEP_SNAPSHOTS]:
        try:
            old.unlink()
        except OSError:
            pass
    slim = dict(details)
    slim["dom_shape"] = {"file": name, "nodes": int(shape.get("nodes") or 0)}
    return slim
