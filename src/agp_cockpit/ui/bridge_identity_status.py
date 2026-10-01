from __future__ import annotations

from collections.abc import Mapping


def format_bridge_identity_status(status: Mapping[str, object]) -> str:
    """Render delivered and browser-observed extension identity for the UI."""
    expected_version = str(status.get("expected_version", "")).strip()
    expected_build = str(status.get("expected_build_id", "")).strip()
    observed_version = str(status.get("handshake_version", "")).strip()
    observed_build = str(status.get("handshake_build_id", "")).strip()
    reasons = {str(reason) for reason in status.get("reasons", [])}

    if not observed_version and not observed_build:
        summary = "nicht erkannt"
    elif "handshake-stale" in reasons:
        summary = "erkannt, aber Signal veraltet"
    elif {
        "handshake-version-mismatch",
        "handshake-build-id-mismatch",
    } & reasons:
        summary = "Versionskonflikt"
    else:
        summary = "aktiv und passend"

    return "\n".join(
        (
            f"Status: {summary}",
            f"Bereitgestellt: v{expected_version or '—'}",
            f"Im Browser erkannt: v{observed_version or '—'}",
            f"Bereitgestellter Build: {expected_build or '—'}",
            f"Erkannter Build: {observed_build or '—'}",
        )
    )
