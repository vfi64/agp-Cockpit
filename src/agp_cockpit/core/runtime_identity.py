from __future__ import annotations

import json
import math
import time
from pathlib import Path
from urllib.parse import urlparse

from agp_cockpit.adapters.macos_extension import (
    _manifest_build_id,
    _manifest_version,
    local_extension_root,
)


def _conversation_id(url: str) -> str:
    parts = [part for part in urlparse(url).path.split("/") if part]
    return parts[1] if len(parts) >= 2 and parts[0] == "c" else ""


def runtime_identity_status(
    repository_root: Path,
    runtime_root: Path,
    *,
    expected_conversation_url: str = "",
    max_handshake_age_seconds: float = 300.0,
) -> dict:
    """Return deterministic readiness evidence for the delivered desktop path."""
    repository_root = repository_root.expanduser().resolve()
    runtime_root = runtime_root.expanduser().resolve()
    staged = local_extension_root()
    marker_path = staged / ".agp-stage.json"
    handshake_path = runtime_root / "extension.json"
    expected_download = repository_root / "Download"
    expected_runner = expected_download / "run_next.py"
    reasons: list[str] = []
    marker: dict | None = None
    handshake: dict | None = None
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        reasons.append("staged-extension-identity-missing")
    try:
        handshake = json.loads(handshake_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        reasons.append("fresh-extension-handshake-missing")

    try:
        expected_version = _manifest_version(staged)
        expected_build_id = _manifest_build_id(staged)
    except Exception:  # noqa: BLE001 - readiness must fail closed.
        expected_version = ""
        expected_build_id = ""
        reasons.append("staged-extension-manifest-invalid")

    if marker is not None:
        if marker.get("repository_root") != str(repository_root):
            reasons.append("repository-root-mismatch")
        if marker.get("download_directory") != str(expected_download):
            reasons.append("download-directory-mismatch")
        if marker.get("run_next") != str(expected_runner):
            reasons.append("run-next-path-mismatch")
    
    if not expected_runner.is_file():
        reasons.append("run-next-missing")
    if marker is not None:
        if marker.get("version") != expected_version:
            reasons.append("staged-version-mismatch")
        if marker.get("build_id") != expected_build_id:
            reasons.append("staged-build-id-mismatch")
    handshake_timestamp = 0.0
    if handshake is not None:
        try:
            handshake_timestamp = float(handshake.get("timestamp_unix", 0.0))
        except (TypeError, ValueError):
            handshake_timestamp = 0.0
        if (
            not math.isfinite(handshake_timestamp)
            or time.time() - handshake_timestamp > max_handshake_age_seconds
        ):
            reasons.append("handshake-stale")
        if str(handshake.get("version", "")).strip() != expected_version:
            reasons.append("handshake-version-mismatch")
        if str(handshake.get("build_id", "")).strip() != expected_build_id:
            reasons.append("handshake-build-id-mismatch")
        if not str(handshake.get("page_url", "")).startswith("https://chatgpt.com/"):
            reasons.append("handshake-page-mismatch")
        expected_conversation_id = _conversation_id(expected_conversation_url)
        actual_conversation_id = _conversation_id(str(handshake.get("page_url", "")))
        if expected_conversation_id and actual_conversation_id != expected_conversation_id:
            reasons.append("handshake-conversation-mismatch")

    return {
        "ready": not reasons,
        "reasons": reasons,
        "repository_root": str(repository_root),
        "runtime_root": str(runtime_root),
        "staged_extension": str(staged),
        "download_directory": str(expected_download),
        "run_next": str(expected_runner),
        "expected_version": expected_version,
        "expected_build_id": expected_build_id,
        "handshake_version": str(handshake.get("version", "")) if handshake else "",
        "handshake_build_id": str(handshake.get("build_id", "")) if handshake else "",
        "handshake_timestamp_unix": handshake_timestamp,
        "expected_conversation_id": _conversation_id(expected_conversation_url),
        "handshake_conversation_id": (
            _conversation_id(str(handshake.get("page_url", "")))
            if handshake else ""
        ),
    }
