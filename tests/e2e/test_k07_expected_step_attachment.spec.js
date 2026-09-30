// AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1
// Live divergence 2026-09-30: ChatGPT rendered 1475_chat_switch_standard_task.py
// but no assistant-role node existed, so the loop timed out after 180 s.
// The awaited card is identified by the freshly assigned step number.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const CONTENT = fs.readFileSync(path.join(ROOT, "chrome_extension/content.js"), "utf8");
const start = CONTENT.indexOf("  function pythonAttachmentRow(anchor)");
const end = CONTENT.indexOf("  // AGP_K07_COMMAND_FILE_INGRESS_989", start);
const FUNCTIONS = CONTENT.slice(start, end);

const DOM = `<!doctype html><html><body><main>
  <section class="turn"><div>AGP-SEND-0123456789abcdef Use exactly 1475_...py; old file 1471_chat_switch_standard_task.py</div></section>
  <section class="turn"><div>older answer</div><button>1471_chat_switch_standard_task.py Code</button></section>
  <section class="turn"><div>46s nachgedacht</div>
    <div class="card"><button id="new-card">1475_chat_switch_standard_task.py Code</button></div></section>
  <div role="dialog"><button>1475_chat_switch_standard_task.py</button></div>
  <form><div contenteditable="true"><button>1475_chat_switch_standard_task.py</button></div></form>
</main></body></html>`;

test("the card carrying the expected step is found without assistant-role wrappers", async ({page}) => {
  await page.setContent(DOM);
  await page.addScriptTag({content:FUNCTIONS});
  const found = await page.evaluate(() => expectedStepAttachmentCandidates(1475)
    .map(item => ({name:item.name, id:item.node.id})));
  expect(found).toEqual([{name:"1475_chat_switch_standard_task.py", id:"new-card"}]);
});

test("older numbered cards and prose mentions are never the awaited response", async ({page}) => {
  await page.setContent(DOM);
  await page.addScriptTag({content:FUNCTIONS});
  expect(await page.evaluate(() => expectedStepAttachmentCandidates(1476).length)).toBe(0);
  expect(await page.evaluate(() => expectedStepAttachmentCandidates(147).length)).toBe(0);
});
