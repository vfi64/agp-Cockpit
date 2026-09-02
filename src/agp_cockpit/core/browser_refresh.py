from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
import time


@dataclass(frozen=True)
class BrowserRefreshRequest:
    generation: int
    reason: str
    requested_at_unix: float


def refresh_request_path(repository_root: Path) -> Path:
    return repository_root / ".local" / "agp-cockpit" / "browser" / "refresh_request.json"


def handled_refresh_path(repository_root: Path) -> Path:
    return repository_root / ".local" / "agp-cockpit" / "browser" / "handled_refresh.json"


def request_browser_refresh(
    repository_root: Path,
    *,
    reason: str = "operator",
) -> BrowserRefreshRequest:
    root = repository_root.expanduser().resolve()
    path = refresh_request_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)

    request = BrowserRefreshRequest(
        generation=time.time_ns(),
        reason=str(reason)[:120],
        requested_at_unix=time.time(),
    )

    payload = {
        "generation": request.generation,
        "reason": request.reason,
        "requested_at_unix": request.requested_at_unix,
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
    except Exception:
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
        except Exception:
            pass
        time.sleep(poll_seconds)

    return False
