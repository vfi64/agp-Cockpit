// AGP_RESULT_ATTACHMENT_COMPOSER_BOUND_V1 / AGP_COMPOSER_VISIBLE_FORM_V1
// Live 2026-10-05 on the ChatGPT start page (https://chatgpt.com/): three
// composer forms, forms 0 and 1 rendered 0x0, form 2 visible and active. Each
// form owns three file inputs; the first enabled input of the document belonged
// to the invisible form 0, so the Kit command digest was attached there and the
// mission start failed before any effect. This fixture rebuilds that DOM.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const os = require("os");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "../..");
const EVIDENCE_FILE = path.join(ROOT, "chrome_extension/native_message_evidence.js");
const SOURCE_FILE = path.join(ROOT, "chrome_extension/result_file_attachment.js");
const EVIDENCE = fs.readFileSync(EVIDENCE_FILE, "utf8");

function loadAttachment() {
  const context = {setTimeout, console};
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(EVIDENCE, context);
  vm.runInContext(fs.readFileSync(SOURCE_FILE, "utf8"), context);
  return context.AGPResultFileAttachment;
}

function digestFile() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agp-r6-"));
  const file = path.join(dir, "agentic-kit-command-digest.json");
  fs.writeFileSync(file, "{}\n");
  return [file];
}

function composerForm(index, {hidden, disabled}) {
  const box = hidden ? 'style="width:0;height:0;overflow:hidden;display:flex"' : 'style="display:flex"';
  const dis = disabled ? " disabled" : "";
  return `<form id="form-${index}" ${box}>
    <div class="chips" id="chips-${index}"></div>
    <div contenteditable="true" role="textbox" aria-label="ChatGPT fragen" id="editor-${index}" style="min-height:24px;width:400px;flex-shrink:0"></div>
    <input type="file" multiple${dis}><input type="file" multiple${dis}><input type="file" multiple${dis}>
    <button type="submit" aria-label="Senden"${dis}>S</button>
  </form>`;
}

async function startPage(page, {visible = true} = {}) {
  await page.setContent(`<!doctype html><html><body><main>
    ${composerForm(0, {hidden:true, disabled:false})}
    ${composerForm(1, {hidden:true, disabled:true})}
    ${composerForm(2, {hidden:!visible, disabled:false})}
  </main>
  <script>
    for (const form of document.querySelectorAll("form")) {
      for (const input of form.querySelectorAll('input[type=file]')) {
        input.addEventListener("change", () => {
          for (const file of Array.from(input.files || [])) {
            const chip = document.createElement("div");
            chip.className = "chip";
            chip.textContent = file.name;
            form.querySelector(".chips").append(chip);
          }
          input.value = "";
        });
      }
    }
  </script></body></html>`);
}

async function chromeApiFor(page) {
  const cdp = await page.context().newCDPSession(page);
  return {
    debugger: {
      async attach() {},
      async detach() {},
      async sendCommand(_target, method, params) { return cdp.send(method, params); },
    },
  };
}

test("the resolver ignores composers inside 0x0 forms even without focus", async ({page}) => {
  await startPage(page);
  await page.addScriptTag({content:EVIDENCE});
  expect(await page.evaluate(() => agpResolveComposer().id)).toBe("editor-2");
});

test("the digest lands in the visible composer form, not the first file input of the document", async ({page}) => {
  await startPage(page);
  const api = await chromeApiFor(page);
  const result = await loadAttachment().attachResultFiles(api, {tabId:1}, digestFile(), {settleMs:0});
  expect(result.stage).toBe("RESULT_FILES_ATTACHED");
  expect(result.evidence).toBe("composer");
  expect(await page.locator("#chips-2 .chip").count()).toBe(1);
  expect(await page.locator("#chips-0 .chip").count()).toBe(0);
});

test("without a visible composer form the attachment fails closed", async ({page}) => {
  await startPage(page, {visible:false});
  const api = await chromeApiFor(page);
  const failure = await loadAttachment().attachResultFiles(api, {tabId:1}, digestFile(),
    {settleMs:0, confirmTimeoutMs:500}).then(() => null, error => error);
  expect(failure).not.toBeNull();
  expect(String(failure.message)).toContain("ChatGPT file input not found in the active composer form");
  expect(await page.locator(".chip").count()).toBe(0);
});

// AGP_NATIVE_RETRY_OWNED_DRAFT_V1: the real helper from content.js, with the
// content-script primitives it needs. Attempt 1 left this send's own draft in
// the composer; attempt 2 must clear exactly that and nothing else.
const CONTENT = fs.readFileSync(path.join(ROOT, "chrome_extension/content.js"), "utf8");
const helperStart = CONTENT.indexOf("  async function clearOwnedDraftBeforeRetry(");
const helperEnd = CONTENT.indexOf("  async function sendPromptNative(prompt)", helperStart);
const RETRY_HELPER = CONTENT.slice(helperStart, helperEnd);
const MARKER = "AGP-SEND-0123456789abcdef";
const PROMPT = `${MARKER}\nAGP COCKPIT MISSION — FIRST SINGLE STEP\n\nOverall mission: finish`;

async function retryPage(page, draft) {
  await page.setContent(`<!doctype html><html><body><form>
    <div contenteditable="true" role="textbox" id="live" style="min-height:24px"></div></form></body></html>`);
  await page.evaluate(text => { document.getElementById("live").innerText = text; }, draft);
  await page.addScriptTag({content:`
    window.events = [];
    const AGP_COMMIT_MARKER_PATTERN = /^AGP-SEND-[0-9a-f]{16}$/;
    const composer = () => document.getElementById("live");
    const normalizeObservedMessageText = text => String(text || "").replace(/\\s+/g, " ").trim();
    const observedComposerText = () => normalizeObservedMessageText(composer().innerText);
    const setComposerText = (el, text) => { el.textContent = text; };
    const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
    const clientEvent = async (event, details) => { window.events.push({event, details}); };
    ${RETRY_HELPER}
    window.retryClear = (prompt, marker) => clearOwnedDraftBeforeRetry(prompt, marker, 2)
      .then(() => "ok", error => String(error.message));
  `});
}

test("retry clears this send's own draft (exact prompt) and records it", async ({page}) => {
  await retryPage(page, PROMPT);
  expect(await page.evaluate(([p, m]) => window.retryClear(p, m), [PROMPT, MARKER])).toBe("ok");
  expect(await page.evaluate(() => document.getElementById("live").textContent)).toBe("");
  expect(await page.evaluate(() => window.events.map(e => e.event))).toEqual(["NATIVE_RETRY_OWNED_DRAFT_CLEARED"]);
});

test("retry clears a draft carrying this send's nonce even if the editor reformatted it", async ({page}) => {
  await retryPage(page, `${MARKER}\nAGP COCKPIT MISSION (reformatted)`);
  expect(await page.evaluate(([p, m]) => window.retryClear(p, m), [PROMPT, MARKER])).toBe("ok");
});

test("retry refuses foreign composer content and leaves it untouched", async ({page}) => {
  await retryPage(page, "Notiz des Owners, nicht überschreiben");
  const result = await page.evaluate(([p, m]) => window.retryClear(p, m), [PROMPT, MARKER]);
  expect(result).toContain("foreign composer content; refusing to overwrite");
  expect(await page.evaluate(() => document.getElementById("live").textContent)).toBe("Notiz des Owners, nicht überschreiben");
});

test("retry refuses a draft of another send (different nonce)", async ({page}) => {
  await retryPage(page, "AGP-SEND-ffffffffffffffff\nolder draft");
  const result = await page.evaluate(([p, m]) => window.retryClear(p, m), [PROMPT, MARKER]);
  expect(result).toContain("foreign composer content; refusing to overwrite");
});
