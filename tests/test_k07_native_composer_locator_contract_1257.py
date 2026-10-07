from pathlib import Path

N=Path('chrome_extension/browser_native_transport.js').read_text()
B=Path('chrome_extension/background.js').read_text()
C=Path('chrome_extension/content.js').read_text()
T=Path('chrome_extension/chatgpt_selectors.js').read_text()   # AGP_SELECTOR_TABLE_V1
def test_native_locator_accepts_current_chatgpt_role_textbox():
 chain = T[T.index("nativeComposerChain: ["):]
 chain = chain[:chain.index("],")]
 assert "'[contenteditable=\"true\"][role=\"textbox\"]'" in chain
 assert "table.nativeComposerChain" in N
def test_native_and_cdp_paths_share_role_textbox_fallback():
 # AGP_COMPOSER_RESOLVER_V1: a first-match document.querySelector picked a
 # hidden textbox on a new chat (live 2026-09-30). Both paths now use the one
 # visibility-aware resolver; behavior: tests/e2e/test_composer_resolver.spec.js
 E=Path('chrome_extension/native_message_evidence.js').read_text()
 assert 'AGP_SELECTORS.composer' in E
 assert '[contenteditable="true"][role="textbox"]' in T
 assert '[contenteditable="true"][role="textbox"]' not in B
 assert B.count('(${agpResolveComposer.toString()})()') >= 4
 assert 'globalThis.agpResolveComposer' in N
 assert '[contenteditable="true"][role="textbox"]' not in N
def test_native_still_fails_closed_on_missing_or_nonempty_composer():
 assert 'native transport composer not found' in N
 assert 'native transport requires an empty composer; refusing to overwrite existing text' in N
