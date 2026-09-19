from pathlib import Path

B=Path("chrome_extension/background.js").read_text()
C=Path("chrome_extension/content.js").read_text()
def test_sink():
 assert B.count("agpK07NativeTrace1165(")==5
 assert "[AGP_K07_NATIVE_TRACE_1161]" not in B
 assert 'message.type === "AGP_K07_NATIVE_TRACE_1165"' in C
 assert 'clientEvent("K07_NATIVE_TRACE"' in C
