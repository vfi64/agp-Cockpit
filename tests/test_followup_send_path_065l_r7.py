import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chrome_extension" / "content.js"

def src():
    return SRC.read_text(encoding="utf-8")

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
    block = extract_function(src(), "sendButton")
    assert 'button[data-testid="send-button"]' in block
    assert 'button[aria-label*="Send"]' in block
    assert 'button[aria-label*="Senden"]' in block
    assert 'button[type="submit"]' in block
    assert "function sendButton(anchor=null)" in block
    assert 'const form = anchor && anchor.closest ? anchor.closest("form") : null;' in block
    assert "isUsableSendControl" in block

def test_dom_degraded_sender_uses_bounded_wait_not_single_lookup():
    block = extract_function(src(), "sendPromptDomDegraded")
    assert "attempt < 20" in block
    assert "setTimeout(resolve, 150)" in block
    assert "button && !button.disabled" in block
    assert 'throw new Error("send button not found")' not in block

def test_dom_degraded_sender_has_bounded_enter_fallback():
    block = extract_function(src(), "sendPromptDomDegraded")
    assert 'new KeyboardEvent("keydown"' in block
    assert 'new KeyboardEvent("keyup"' in block
    assert 'key:"Enter"' in block
    assert "el.dispatchEvent(down)" in block
    assert "el.dispatchEvent(up)" in block

def test_multiturn_full_auto_and_validation_contracts_remain():
    text = src()
    assert 'run_mode:"FULL_AUTO"' in text
    assert "065 multi-turn LIVE probe rejected before local submit" in text
    assert "work order differs from bounded read-only sequence" in text
