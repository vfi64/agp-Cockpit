from pathlib import Path


def test_production_installation_docs():
    text = Path("chrome_extension/README.md").read_text(encoding="utf-8")
    required = [
        "~/Library/Application Support/AGP Cockpit/chrome_extension/",
        "~/Library/Application Support/AGP Cockpit/bridge/token.txt",
        "chrome://extensions/",
        "Extension options",
        "ERR_BLOCKED_BY_CLIENT",
        "chrome.storage.local",
        "CONNECTED",
        "STATUS_OK",
        "Error: forbidden",
    ]
    for value in required:
        assert value in text
