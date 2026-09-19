from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BrowserReadinessSnapshot:
    expected_generation: int
    handled_generation: int
    extension_timestamp_unix: float
    extension_version: str
    extension_page_url: str
    ready: bool


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:  # noqa: BLE001 - readiness is a best-effort probe.
        return {}


def _startup_status_path(root: Path) -> Path:
    return root / ".local" / "agp-cockpit" / "startup" / "status.json"


def _handled_refresh_path(root: Path) -> Path:
    return root / ".local" / "agp-cockpit" / "browser" / "handled_refresh.json"


def _extension_path(root: Path) -> Path:
    return root / ".local" / "agp-cockpit" / "bridge" / "extension.json"


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def snapshot_browser_readiness(
    repository_root: Path,
    *,
    expected_generation: int,
    requested_at_unix: float,
) -> BrowserReadinessSnapshot:
    root = repository_root.expanduser().resolve()
    handled = _read_json(_handled_refresh_path(root))
    extension = _read_json(_extension_path(root))

    handled_generation = int(handled.get("generation", 0) or 0)
    extension_timestamp_unix = float(extension.get("timestamp_unix", 0.0) or 0.0)
    extension_version = str(extension.get("version", ""))
    extension_page_url = str(extension.get("page_url", ""))

    ready = bool(
        expected_generation > 0
        and handled_generation >= expected_generation
        and extension_timestamp_unix >= requested_at_unix
        and extension_version
        and extension_page_url.startswith("https://chatgpt.com/")
    )

    return BrowserReadinessSnapshot(
        expected_generation=expected_generation,
        handled_generation=handled_generation,
        extension_timestamp_unix=extension_timestamp_unix,
        extension_version=extension_version,
        extension_page_url=extension_page_url,
        ready=ready,
    )


def mark_browser_ready(
    repository_root: Path,
    snapshot: BrowserReadinessSnapshot,
) -> None:
    root = repository_root.expanduser().resolve()
    path = _startup_status_path(root)
    status = _read_json(path)
    status["extension_ready"] = True
    status["browser_state"] = "CONNECTED"
    status["extension_version"] = snapshot.extension_version
    status["extension_page_url"] = snapshot.extension_page_url
    status["refresh_generation"] = snapshot.expected_generation
    status["handled_refresh_generation"] = snapshot.handled_generation
    status["message"] = (
        "AGP Cockpit bereit: Bridge, Chrome, ChatGPT "
        "und Browser-Erweiterung sind verbunden."
    )
    _atomic_write_json(path, status)


def watch_browser_readiness(
    repository_root: Path,
    *,
    expected_generation: int,
    requested_at_unix: float,
    timeout_seconds: float = 180.0,
    poll_seconds: float = 1.0,
) -> BrowserReadinessSnapshot:
    root = repository_root.expanduser().resolve()
    deadline = time.monotonic() + timeout_seconds

    last = snapshot_browser_readiness(
        root,
        expected_generation=expected_generation,
        requested_at_unix=requested_at_unix,
    )

    while time.monotonic() < deadline:
        last = snapshot_browser_readiness(
            root,
            expected_generation=expected_generation,
            requested_at_unix=requested_at_unix,
        )
        if last.ready:
            mark_browser_ready(root, last)
            return last
        time.sleep(poll_seconds)

    return last


def start_browser_readiness_watch(
    repository_root: Path,
    *,
    expected_generation: int,
    requested_at_unix: float,
    timeout_seconds: float = 180.0,
    poll_seconds: float = 1.0,
) -> threading.Thread:
    root = repository_root.expanduser().resolve()
    thread = threading.Thread(
        target=watch_browser_readiness,
        kwargs={
            "repository_root": root,
            "expected_generation": expected_generation,
            "requested_at_unix": requested_at_unix,
            "timeout_seconds": timeout_seconds,
            "poll_seconds": poll_seconds,
        },
        name="agp-browser-readiness",
        daemon=True,
    )
    thread.start()
    return thread
