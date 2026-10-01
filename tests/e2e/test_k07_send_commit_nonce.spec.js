// AGP_K07_SEND_COMMIT_NONCE_V1
// Runs the real background.js native transport against a real browser DOM.
// CDP commands are forwarded to the Playwright page, so every commit decision
// is made by the delivered observation code, not by a mock of it.
//
// The fixture reproduces the live 2026-09-28/29 divergence class: user turns
// without role/test-id/heading wrappers, a fixed five-turn render window,
// a collapsed long projection and a URL change on send.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "../..");
const BACKGROUND = fs.readFileSync(path.join(ROOT, "chrome_extension/background.js"), "utf8");
const EVIDENCE = fs.readFileSync(path.join(ROOT, "chrome_extension/native_message_evidence.js"), "utf8");

const FIXTURE = `<!doctype html><html><body>
<div id="thread"></div>
<form>
  <div id="prompt-textarea" contenteditable="true" style="min-height:20px;width:600px"></div>
  <button type="button" data-testid="send-button" style="width:60px;height:24px">Send</button>
</form>
<script>
  window.__sendMode = "commit";
  const thread = document.getElementById("thread");
  function addTurn(text) {
    const section = document.createElement("section");
    section.className = "turn";
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    section.append(bubble);
    thread.append(section);
    while (thread.children.length > 5) thread.firstElementChild.remove();
  }
  for (let i = 0; i < 5; i += 1) addTurn("older user turn " + i);
  const composer = document.getElementById("prompt-textarea");
  composer.addEventListener("keydown", event => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    const text = composer.innerText;
    composer.textContent = "";
    if (window.__sendMode === "drop") return;
    history.pushState({}, "", "/c/fixture-" + Date.now());
    setTimeout(() => addTurn(text.length > 300 ? text.slice(0, 300) + "…" : text), 300);
  });
</script>
</body></html>`;

async function openFixture(page, mode) {
  await page.route("https://chatgpt.fixture/**", route =>
    route.fulfill({contentType:"text/html", body:FIXTURE}));
  await page.goto("https://chatgpt.fixture/");
  await page.evaluate(value => { window.__sendMode = value; }, mode);
}

function loadBackground(page) {
  const context = {
    console,
    setTimeout,
    importScripts() {},
    chrome:{
      storage:{session:{async get() { return {}; }, async set() {}}},
      downloads:{async search() { return []; }},
      runtime:{onMessage:{addListener() {}}, async sendMessage() {}, reload() {}},
      alarms:{create() {}, onAlarm:{addListener() {}}},
      tabs:{async query() { return []; }, async reload() {}, async sendMessage() {}},
      debugger:{
        async attach() {},
        async detach() {},
        async sendCommand(_target, method, params = {}) {
          if (method === "Runtime.evaluate") {
            return {result:{value:await page.evaluate(params.expression)}};
          }
          if (method === "Input.insertText") {
            await page.keyboard.insertText(params.text);
            return {};
          }
          if (method === "Input.dispatchKeyEvent" && params.type === "keyDown" && params.key === "Enter") {
            await page.keyboard.press("Enter");
          }
          return {};
        },
      },
    },
  };
  vm.createContext(context);
  vm.runInContext(EVIDENCE, context);
  vm.runInContext(BACKGROUND, context);
  return context;
}

const LONG_PROMPT = "AGP COCKPIT MISSION — FIRST SINGLE STEP\n\nOverall mission:\n" +
  "CHAT SWITCH STANDARD TASK ".repeat(40);
const MARKER = "AGP-SEND-0123456789abcdef";

test.setTimeout(90000);

test("nonce commit evidence confirms a send the rendered-turn matcher cannot see", async ({page}) => {
  await openFixture(page, "commit");
  const background = loadBackground(page);
  const ack = await background.agpNativeTransportV1(
    {request_id:"r-nonce", operation:"insert_and_submit", text:`${MARKER}\n${LONG_PROMPT}`, commit_marker:MARKER},
    {tab:{id:1}},
  );
  expect(ack.stage).toBe("USER_TURN_COMMITTED");
  expect(ack.commit.commit_via).toBe("commit_marker");
});

test("without a nonce the same committed turn stays indeterminate (live false negative)", async ({page}) => {
  await openFixture(page, "commit");
  const background = loadBackground(page);
  const ack = await background.agpNativeTransportV1(
    {request_id:"r-legacy", operation:"insert_and_submit", text:LONG_PROMPT},
    {tab:{id:1}},
  );
  expect(ack.stage).toBe("USER_TURN_INDETERMINATE");
});

test("an emptied composer without a persisted turn is never commit evidence", async ({page}) => {
  await openFixture(page, "drop");
  const background = loadBackground(page);
  const ack = await background.agpNativeTransportV1(
    {request_id:"r-drop", operation:"insert_and_submit", text:`${MARKER}\n${LONG_PROMPT}`, commit_marker:MARKER},
    {tab:{id:1}},
  );
  expect(ack.stage).not.toBe("USER_TURN_COMMITTED");
  expect(ack.diagnostics.after_composer_chars).toBe(0);
});

test("a marker that is not the first prompt line is refused", async ({page}) => {
  await openFixture(page, "commit");
  const background = loadBackground(page);
  // The promise comes from a vm context (another realm); @playwright/test 1.62
  // rejects `.rejects` on it (CI #481). Settle it explicitly instead.
  const failure = await background.agpNativeTransportV1(
    {request_id:"r-bad", operation:"insert_and_submit", text:LONG_PROMPT, commit_marker:MARKER},
    {tab:{id:1}},
  ).then(() => null, error => error);
  expect(failure).not.toBeNull();
  expect(String(failure.message)).toContain("invalid native transport commit marker");
});
