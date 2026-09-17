from pathlib import Path
N=Path("chrome_extension/background.js").read_text(encoding="utf-8")
def test_trace_only():
 assert N.count("agpK07NativeTrace1165({event:") == 4
 S=N[N.index("// AGP_BROWSER_NATIVE_TRANSPORT_V1"):]
 assert '"Input.dispatchMouseEvent"' not in S
 assert S.count('"Input.dispatchKeyEvent"') == 4
 assert "// AGP_K07_TRUSTED_ENTER_COMMIT_RETRY_928" in S
