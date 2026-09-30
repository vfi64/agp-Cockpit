from agp_cockpit.ui.bridge_identity_status import format_bridge_identity_status


def identity(**overrides):
    status = {
        "expected_version": "0.3.11",
        "expected_build_id": "build-new",
        "handshake_version": "0.3.11",
        "handshake_build_id": "build-new",
        "reasons": [],
    }
    status.update(overrides)
    return status


def test_matching_browser_bridge_identity_is_visible():
    rendered = format_bridge_identity_status(identity())

    assert "Status: aktiv und passend" in rendered
    assert "Bereitgestellt: v0.3.11" in rendered
    assert "Im Browser erkannt: v0.3.11" in rendered
    assert "Erkannter Build: build-new" in rendered


def test_mismatched_browser_bridge_identity_is_explicit():
    rendered = format_bridge_identity_status(
        identity(
            handshake_version="0.3.10",
            handshake_build_id="build-old",
            reasons=[
                "handshake-version-mismatch",
                "handshake-build-id-mismatch",
            ],
        )
    )

    assert "Status: Versionskonflikt" in rendered
    assert "Bereitgestellt: v0.3.11" in rendered
    assert "Im Browser erkannt: v0.3.10" in rendered


def test_missing_or_stale_browser_bridge_identity_is_not_reported_as_active():
    missing = format_bridge_identity_status(
        identity(handshake_version="", handshake_build_id="")
    )
    stale = format_bridge_identity_status(
        identity(reasons=["handshake-stale"])
    )

    assert "Status: nicht erkannt" in missing
    assert "Im Browser erkannt: v—" in missing
    assert "Status: erkannt, aber Signal veraltet" in stale
