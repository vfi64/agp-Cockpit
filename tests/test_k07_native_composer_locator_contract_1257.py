from pathlib import Path
N=Path('chrome_extension/browser_native_transport.js').read_text()
B=Path('chrome_extension/background.js').read_text()
C=Path('chrome_extension/content.js').read_text()
def test_native_locator_accepts_current_chatgpt_role_textbox():
 assert "'[contenteditable=\"true\"][role=\"textbox\"]'" in N
def test_native_and_cdp_paths_share_role_textbox_fallback():
 assert 'document.querySelector(\'[contenteditable="true"][role="textbox"]\')' in B
 assert '[contenteditable="true"][role="textbox"]' in N
def test_native_still_fails_closed_on_missing_or_nonempty_composer():
 assert 'native transport composer not found' in N
 assert 'native transport requires an empty composer; refusing to overwrite existing text' in N
