from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_native_transport_uses_canonical_composer_fallbacks():
 # AGP_SELECTOR_TABLE_V1: the canonical order lives in chatgpt_selectors.js.
 s=(ROOT/'chrome_extension/browser_native_transport.js').read_text()
 t=(ROOT/'chrome_extension/chatgpt_selectors.js').read_text()
 canonical=t[t.index("nativeComposerCanonical:"):]
 canonical=canonical[:canonical.index("\n")]
 assert canonical.index('"#prompt-textarea"') < canonical.index('textarea[data-id="root"]') < canonical.index('"textarea"]')
 assert '[contenteditable="true"][role="textbox"]' in t
 assert 'table.nativeComposerCanonical' in s and 'document.querySelector(selector)' in s
 assert 'native transport composer not found' in s
