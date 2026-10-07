"""AGP_SELECTOR_TABLE_V1 (DOM hardening step 3, owner 2026-10-07): every selector that names
ChatGPT's page lives in chrome_extension/chatgpt_selectors.js. The content scripts read it as
the global AGP_SELECTORS (manifest: loaded first), the service worker through importScripts,
and the helpers background.js injects into the page through Runtime.evaluate get the same
table from agpPageExpression(). Real-Chromium checks: tests/e2e (composer resolver, send
probe, touchpoint self-test) load the table the same way."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "chrome_extension"
TABLE = EXT / "chatgpt_selectors.js"
BACKGROUND = (EXT / "background.js").read_text(encoding="utf-8")

# What only ChatGPT's page means: ids, test ids, author roles, ARIA labels and dialog roles.
CHATGPT_SPECIFIC = re.compile(
    r"#prompt-textarea|data-testid[\^*$]?=|data-message-author-role|data-message-id\]|"
    r"aria-label[\^*$]?=|data-is-streaming|\.cm-content|contenteditable=\\?[\"']true|"
    r"role=\\?[\"'](?:dialog|alert|textbox)|aria-modal|conversation-turn|data-id=\\?[\"']root")


def _code_lines(text):
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith(("//", "*")):
            continue
        yield number, line.split(" // ")[0]


def test_chatgpt_selectors_live_only_in_the_table():
    found = []
    for path in sorted(EXT.glob("*.js")):
        if path == TABLE:
            continue
        for number, line in _code_lines(path.read_text(encoding="utf-8")):
            if CHATGPT_SPECIFIC.search(line):
                found.append(f"{path.name}:{number}: {line.strip()[:100]}")
    assert not found, "ChatGPT selectors outside chatgpt_selectors.js:\n" + "\n".join(found)


def test_the_table_is_frozen_data_loaded_first_everywhere():
    script = ("require(process.argv[1]); const t = globalThis.AGP_SELECTORS;"
              "const deep = v => !v || typeof v !== 'object' || (Object.isFrozen(v) && Object.values(v).every(deep));"
              "console.log(JSON.stringify({deep: deep(t), same: JSON.stringify(JSON.parse(JSON.stringify(t))) === JSON.stringify(t),"
              "keys: Object.keys(t)}))")
    out = subprocess.run(["node", "-e", script, str(TABLE)],
                         cwd=ROOT, text=True, capture_output=True, check=True)
    data = json.loads(out.stdout)
    assert data["deep"] and data["same"]
    for key in ("composer", "nativeComposerChain", "userTurn", "assistantTurn", "sendButton",
                "sendButtonProbe", "generationActive", "stopButton", "fileCardDownload", "dialogClose"):
        assert key in data["keys"], key
    js = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))["content_scripts"][0]["js"]
    assert js[0] == "chatgpt_selectors.js"
    assert BACKGROUND.startswith('importScripts("chatgpt_selectors.js");')


def test_every_page_helper_runs_with_the_table():
    # background.js (composer cleanup, native transport) and result_file_attachment.js
    # (file input, presence probe) are the service-worker paths into the page world.
    assert BACKGROUND.count("expression:agpPageExpression(expression)") == 2
    assert "function agpPageExpression" not in BACKGROUND          # one definition, in the table file
    attachment = (EXT / "result_file_attachment.js").read_text(encoding="utf-8")
    assert attachment.count("globalThis.agpPageExpression(") == 2
    for name in ("background.js", "result_file_attachment.js"):
        source = (EXT / name).read_text(encoding="utf-8")
        assert source.count('"Runtime.evaluate"') == source.count("agpPageExpression(") + (
            1 if name == "background.js" else 0), name     # background: the attachment fetch has no selectors
    script = (f"require({json.dumps(str(TABLE))});"
              "const expr = agpPageExpression('AGP_SELECTORS.sendButtonProbe.length + \":\" + AGP_SELECTORS.stopButton');"
              "delete globalThis.AGP_SELECTORS; console.log(eval(expr));")
    out = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True, check=True)
    assert out.stdout.strip() == '4:[data-testid="stop-button"]'
