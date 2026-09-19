from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_native_transport_has_single_clean_resolver():
 s=(ROOT/'chrome_extension/browser_native_transport.js').read_text()
 assert s.count('function resolveComposer()') == 1
 assert '}\n    }\n    return null;\n  }' not in s
 assert 'window.AGPBrowserNativeTransport = Object.freeze' in s
 assert 'chrome.runtime.sendMessage' in s
