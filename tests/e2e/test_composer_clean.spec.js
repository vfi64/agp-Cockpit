// AGP_COMPOSER_CLEAN_START_V1 (live 2026-10-02): a failed send left the
// bootstrap text and the command digest in the composer; the next start
// appended to it. Cockpit leftovers are removed, the human's content never.
const { test, expect } = require("@playwright/test");
const AGP_SELECTORS_SRC = require("fs").readFileSync(require("path").join(__dirname, "../../chrome_extension/chatgpt_selectors.js"), "utf8");   // AGP_SELECTOR_TABLE_V1: loaded first, as in the manifest
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const EVIDENCE = fs.readFileSync(path.join(ROOT, "chrome_extension/native_message_evidence.js"), "utf8");
const BACKGROUND = fs.readFileSync(path.join(ROOT, "chrome_extension/background.js"), "utf8");
const BLOCK = BACKGROUND.slice(BACKGROUND.indexOf("const AGP_COCKPIT_TEXT"),
                               BACKGROUND.indexOf("async function agpCleanComposer("));
// AGP_SELECTOR_TABLE_V1: the cleanup's page expressions run inside agpPageExpression(), as in
// agpCleanComposer(), so the page gets the selector table the same way Chrome does.
// eslint-disable-next-line no-new-func
const api = new Function(AGP_SELECTORS_SRC + EVIDENCE + BLOCK +
  "; return {agpComposerCleanup, agpComposerInspect, agpResolveComposer, agpPageExpression};")();

const chip = (name, label = "Datei entfernen") =>
  `<div class="chip"><span>${name}</span><button aria-label="${label}" onclick="this.parentElement.remove()">x</button></div>`;
const page_ = ({text = "", chips = []} = {}) => `<!doctype html><html><body><main><form>
  ${chips.join("")}
  <div contenteditable="true" role="textbox" id="prompt-textarea" style="height:60px">${text}</div>
  <button aria-label="Weitere Optionen…">…</button>
  <button aria-label="Senden" data-testid="send-button">↑</button>
</form></main></body></html>`;

async function cleanup(page, options) {
  const cdp = await page.context().newCDPSession(page);
  const evaluate = expression => page.evaluate(api.agpPageExpression(expression));
  const sendCommand = (method, params) => cdp.send(method, params || {});
  const normalize = value => String(value || "").replace(/\s+/g, " ").trim();
  return api.agpComposerCleanup(evaluate, sendCommand, normalize, options);
}
const composerText = page => page.evaluate(() => document.getElementById("prompt-textarea").innerText.trim());
const chipNames = page => page.evaluate(() => Array.from(document.querySelectorAll(".chip span")).map(e => e.textContent));

test("leftover bootstrap text and Cockpit attachments are removed", async ({page}) => {
  await page.setContent(page_({text:"AGP-SEND-b9802b3cc76121a6<br>AGP COCKPIT MISSION — FIRST SINGLE STEP",
    chips:[chip("agentic-kit-comma…"), chip("1588_agp_t5_return_bundle.json", "Remove file")]}));
  const result = await cleanup(page);
  expect(result.ok).toBe(true);
  expect(result.stage).toBe("COMPOSER_CLEANED");
  expect(result.removed_files.sort()).toEqual(["1588_agp_t5_return_bundle.json", "agentic-kit-comma…"]);
  expect(await composerText(page)).toBe("");
  expect(await chipNames(page)).toEqual([]);
});

test("the human's own text is never deleted", async ({page}) => {
  await page.setContent(page_({text:"Meine eigene Notiz"}));
  const result = await cleanup(page);
  expect(result.ok).toBe(false);
  expect(result.stage).toBe("COMPOSER_HAS_FOREIGN_TEXT");
  expect(await composerText(page)).toBe("Meine eigene Notiz");
});

test("foreign attachments stop the send and nothing is removed", async ({page}) => {
  await page.setContent(page_({chips:[chip("Urlaub.pdf"), chip("agentic-kit-command-digest.json")]}));
  const result = await cleanup(page);
  expect(result.stage).toBe("COMPOSER_HAS_FOREIGN_FILES");
  expect(await chipNames(page)).toEqual(["Urlaub.pdf", "agentic-kit-command-digest.json"]);
});

test("the native transport keeps the evidence of this send and clears only text", async ({page}) => {
  await page.setContent(page_({text:"AGP-SEND-0123456789abcdef old", chips:[chip("1590_x_return_bundle.json")]}));
  const result = await cleanup(page, {files:false});
  expect(result.ok).toBe(true);
  expect(await composerText(page)).toBe("");
  expect(await chipNames(page)).toEqual(["1590_x_return_bundle.json"]);
});

test("an empty composer is left alone; option buttons are not attachments", async ({page}) => {
  await page.setContent(page_());
  const result = await cleanup(page);
  expect(result).toEqual({ok:true, stage:"COMPOSER_EMPTY", cleared_text:false, removed_files:[], unrecognised:[]});
});

test("a Cockpit chip without a recognisable remove control is reported with its shape", async ({page}) => {
  await page.setContent(page_({chips:[`<div class="chip"><span>agentic-kit-comma…</span><div role="button" aria-label="Optionen">⋯</div></div>`]}));
  const result = await cleanup(page);
  expect(result.ok).toBe(true);
  expect(result.unrecognised[0].name).toBe("agentic-kit-comma…");
  expect(result.unrecognised[0].buttons.some(b => b.aria_label === "Optionen")).toBe(true);
});
