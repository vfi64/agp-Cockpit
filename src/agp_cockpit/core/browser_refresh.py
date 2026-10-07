from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BrowserRefreshRequest:
    generation: int
    reason: str
    requested_at_unix: float


SAME_TARGET_SECONDS = 600


def refresh_request_path(repository_root: Path) -> Path:
    return repository_root / ".local" / "agp-cockpit" / "browser" / "refresh_request.json"


def handled_refresh_path(repository_root: Path) -> Path:
    return repository_root / ".local" / "agp-cockpit" / "browser" / "handled_refresh.json"


def request_browser_refresh(
    repository_root: Path,
    *,
    reason: str = "operator",
    target_build_id: str = "",
) -> BrowserRefreshRequest:
    root = repository_root.expanduser().resolve()
    path = refresh_request_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    # AGP_SINGLE_REFRESH_V1 (live 2026-10-07, r5 -> r6): the handshake and the startup
    # worker both asked for the new build 130 ms apart; the second generation reloaded
    # the already current extension again and orphaned the freshly reloaded ChatGPT tab
    # (the owner had to reload it by hand). One request per target build and minute.
    if target_build_id:
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            current = None
        if (isinstance(current, dict) and current.get("target_build_id") == str(target_build_id)[:120]
                and time.time() - float(current.get("requested_at_unix") or 0) < SAME_TARGET_SECONDS):
            return BrowserRefreshRequest(generation=int(current["generation"]),
                                         reason=str(current.get("reason") or ""),
                                         requested_at_unix=float(current.get("requested_at_unix") or 0))

    request = BrowserRefreshRequest(
        generation=time.time_ns(),
        reason=str(reason)[:120],
        requested_at_unix=time.time(),
    )

    payload = {
        "generation": request.generation,
        "reason": request.reason,
        "requested_at_unix": request.requested_at_unix,
        # AGP_EXTENSION_AUTO_REFRESH_V2: the build this refresh should load;
        # the bridge asks at most once per target build (no reload loop).
        "target_build_id": str(target_build_id)[:120],
    }

    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)
    return request


def read_browser_refresh_request(
    repository_root: Path,
) -> BrowserRefreshRequest | None:
    path = refresh_request_path(repository_root.expanduser().resolve())
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return BrowserRefreshRequest(
            generation=int(data["generation"]),
            reason=str(data.get("reason", "")),
            requested_at_unix=float(data.get("requested_at_unix", 0.0)),
        )
    except Exception:  # noqa: BLE001 - malformed request means no pending refresh.
        return None


def wait_for_refresh_handled(
    repository_root: Path,
    generation: int,
    *,
    timeout_seconds: float = 30.0,
    poll_seconds: float = 0.5,
) -> bool:
    path = handled_refresh_path(repository_root.expanduser().resolve())
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if int(data.get("generation", 0)) >= generation:
                return True
        except Exception:  # noqa: BLE001, S112 - file may be mid-atomic-write.
            continue
        time.sleep(poll_seconds)

    return False


def refresh_request_target(repository_root: Path) -> str:
    """Target build of the current refresh request ("" if none or unreadable)."""
    try:
        data = json.loads(refresh_request_path(repository_root.expanduser().resolve()).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(data.get("target_build_id") or "") if isinstance(data, dict) else ""
