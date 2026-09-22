from pathlib import Path


def test_extension_handshake_uses_proven_client_event():
    source = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    assert 'event:"EXTENSION_HANDSHAKE"' in source
    assert 'build_id:globalThis.AGP_EXTENSION_BUILD_ID || ""' in source
    identity = Path("chrome_extension/build_identity.js").read_text(encoding="utf-8")
    assert 'globalThis.AGP_EXTENSION_BUILD_ID = "' in identity
    assert '"/v1/client-event"' in source
    assert '"/v1/extension-handshake"' not in source
    assert "chrome.runtime.getManifest().version" in source
    assert "setInterval(sendHandshake, 15000)" in source
    assert "setInterval(sendHandshake, 5000)" not in source
    assert "lastHandshakeUrl" in source
    assert "lastHandshakeAt" in source
    assert "now - STATE.lastHandshakeAt < 60000" in source
