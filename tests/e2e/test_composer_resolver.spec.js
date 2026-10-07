// AGP_COMPOSER_RESOLVER_V1
// Live 2026-09-30 on a new chat (https://chatgpt.com/): the focus step chose
// the first [contenteditable][role=textbox] in document order, blurred the
// focused visible composer and ended in COMPOSER_FOCUS_NOT_VERIFIED. A hidden
// previous-conversation view also exposed the old step-1480 card.
const { test, expect } = require("@playwright/test");
const AGP_SELECTORS_SRC = require("fs").readFileSync(require("path").join(__dirname, "../../chrome_extension/chatgpt_selectors.js"), "utf8");   // AGP_SELECTOR_TABLE_V1: loaded first, as in the manifest
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const EVIDENCE = fs.readFileSync(path.join(ROOT, "chrome_extension/native_message_evidence.js"), "utf8");
const CONTENT = fs.readFileSync(path.join(ROOT, "chrome_extension/content.js"), "utf8");
// AGP_INGRESS_MODULE_V1: the card functions live in cockpit_ingress.js; expose them as before.
const CARD_FUNCTIONS = fs.readFileSync(path.join(ROOT, "chrome_extension/cockpit_ingress.js"), "utf8") +
  "\n;(() => { const ingress = AGP_INGRESS.create({state:{}});" +
  " for (const [name, fn] of Object.entries(ingress)) globalThis[name] = fn; })();\n";
const DOM_ADAPTER = path.join(ROOT, "chrome_extension/chatgpt_dom.js");   // AGP_DOM_ADAPTER_V1

const NEW_CHAT = `<!doctype html><html><body>
  <div id="old-thread" style="display:none">
    <div contenteditable="true" role="textbox" id="stale">old draft</div>
    <button>1480_agp_terminal.json Code</button>
  </div>
  <div inert><div contenteditable="true" role="textbox" id="inert-box" style="height:20px">x</div></div>
  <main><form><div contenteditable="true" role="textbox" id="live" style="height:40px"></div></form></main>
</body></html>`;

test("the hidden or inert textbox is never the composer; the visible one is", async ({page}) => {
  await page.setContent(NEW_CHAT);
  await page.addScriptTag({content:AGP_SELECTORS_SRC});
  await page.addScriptTag({content:EVIDENCE});
  expect(await page.evaluate(() => agpResolveComposer().id)).toBe("live");
});

test("the focused visible composer wins and focusing it succeeds (the live failure)", async ({page}) => {
  await page.setContent(NEW_CHAT);
  await page.addScriptTag({content:AGP_SELECTORS_SRC});
  await page.addScriptTag({content:EVIDENCE});
  const result = await page.evaluate(() => {
    document.getElementById("live").focus();
    const composer = agpResolveComposer();
    const before = document.activeElement;
    if (before && before !== composer) before.blur();
    composer.focus();
    return {id:composer.id, focused:document.activeElement === composer};
  });
  expect(result).toEqual({id:"live", focused:true});
});

test("serialized resolver works inside the snapshot as background.js evaluates it", async ({page}) => {
  await page.setContent(NEW_CHAT);
  await page.evaluate(() => { document.getElementById("live").textContent = "AGP-SEND-0123456789abcdef hello"; });
  await page.addScriptTag({content:AGP_SELECTORS_SRC});
  await page.addScriptTag({content:EVIDENCE});
  const expression = await page.evaluate(() =>
    `(${agpNativeMessageSnapshot.toString()})(${agpResolveComposer.toString()})`);
  const snapshot = await page.evaluate(expression);
  expect(snapshot.composer_text).toBe("AGP-SEND-0123456789abcdef hello");
});

test("cards inside a hidden previous conversation are not candidates", async ({page}) => {
  await page.setContent(NEW_CHAT);
  await page.addScriptTag({content:AGP_SELECTORS_SRC});
  await page.addScriptTag({path:DOM_ADAPTER});
  await page.addScriptTag({content:CARD_FUNCTIONS});
  expect(await page.evaluate(() => expectedStepAttachmentCandidates(1480, "terminal").length)).toBe(0);
});
