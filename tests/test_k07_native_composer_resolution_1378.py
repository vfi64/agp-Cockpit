from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_native_transport_uses_canonical_composer_fallbacks():
 s=(ROOT/'chrome_extension/browser_native_transport.js').read_text()
 assert 'document.querySelector("#prompt-textarea")' in s
 assert 'textarea[data-id="root"]' in s
 assert 'document.querySelector("textarea")' in s
 assert '[contenteditable="true"][role="textbox"]' in s
 assert 'native transport composer not found' in s
