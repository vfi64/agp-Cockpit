import re
from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chrome_extension" / "content.js"

def src():
    return SRC.read_text(encoding="utf-8") + "\n" + SEND_JS

def extract_function(text, name):
    m = re.search(rf'(?:(?:async)\s+)?function\s+{re.escape(name)}\s*\(', text)
    assert m, f"{name} missing"
    brace = text.find("{", m.end())
    assert brace >= 0
    depth = 0
    quote = None
    esc = False
    for i in range(brace, len(text)):
        ch = text[i]
        if quote:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():i+1]
    raise AssertionError(f"{name} unterminated")

def test_send_button_keeps_existing_contract_and_adds_submit_fallback():
    # AGP_DOM_ADAPTER_V1 (slice 3b): the contract lives in the adapter; content.js no longer
    # wraps it (AGP_DEGRADED_DOM_PATH_REMOVED_V1: only the removed DOM sender clicked it).
    adapter = (ROOT / "chrome_extension" / "chatgpt_dom.js").read_text(encoding="utf-8")
    adapter += (ROOT / "chrome_extension" / "chatgpt_selectors.js").read_text(encoding="utf-8")   # AGP_SELECTOR_TABLE_V1
    for selector in ('button[data-testid="send-button"]', 'button[aria-label*="Send"]',
                     'button[aria-label*="Senden"]', 'button[type="submit"]'):
        assert selector in adapter
    block = extract_function(adapter, "sendButton")
    assert "function sendButton(anchor = null)" in block
    assert 'const form = anchor && anchor.closest ? anchor.closest("form") : null;' in block
    assert "isUsableSendControl" in block
