// AGP_K07_RESULT_ATTACHMENT_EVIDENCE_V2
// Drives the real result_file_attachment.js through a real CDP session
// (DOM.setFileInputFiles on real Chromium). The fixture composer consumes the
// selected files on `change`, renders chips and clears the input, which is the
// behavior that made the previous confirmation fail live on 2026-09-30 while
// the files were visibly attached.
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const os = require("os");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "../..");
const SOURCE_FILE = process.env.AGP_RESULT_ATTACHMENT_SOURCE ||
  path.join(ROOT, "chrome_extension/result_file_attachment.js");

function loadAttachment() {
  const context = {setTimeout, console};
  context.globalThis = context;
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(SOURCE_FILE, "utf8"), context);
  return context.AGPResultFileAttachment;
}

function evidenceFiles() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "agp-evidence-"));
  const names = [
    "1476_chat_switch_standard_task_run_1790768659527272000_return_bundle.json",
    "1476_run_next_output.txt",
  ];
  return names.map(name => {
    const file = path.join(dir, name);
    fs.writeFileSync(file, "{}\n");
    return file;
  });
}

async function composerPage(page, mode) {
  await page.setContent(`<!doctype html><html><body><main>
    <form>
      <div id="chips"></div>
      <div id="prompt-textarea" contenteditable="true"></div>
      <input type="file" multiple>
    </form></main>
    <script>
      const input = document.querySelector('input[type=file]');
      input.addEventListener('change', () => {
        const names = Array.from(input.files || []).map(file => file.name);
        if (${JSON.stringify(mode)} !== "ignore") {
          for (const name of names) {
            const chip = document.createElement('div');
            chip.className = 'chip';
            chip.textContent = ${JSON.stringify(mode)} === "truncated" ? name.slice(0, 18) + '…' : name;
            document.getElementById('chips').append(chip);
          }
        }
        input.value = '';
      });
    </script></body></html>`);
}

async function chromeApiFor(page) {
  const cdp = await page.context().newCDPSession(page);
  const calls = [];
  return {
    calls,
    api: {
      debugger: {
        async attach() {},
        async detach() {},
        async sendCommand(_target, method, params) {
          calls.push(method);
          return cdp.send(method, params);
        },
      },
    },
  };
}

test("files consumed and cleared by the page are confirmed from the composer", async ({page}) => {
  await composerPage(page, "full");
  const {api} = await chromeApiFor(page);
  const result = await loadAttachment().attachResultFiles(api, {tabId:1}, evidenceFiles(), {settleMs:0});
  expect(result.stage).toBe("RESULT_FILES_ATTACHED");
  expect(result.evidence).toBe("composer");
  expect(await page.locator(".chip").count()).toBe(2);
});

test("visually truncated chip names still confirm the step-scoped files", async ({page}) => {
  await composerPage(page, "truncated");
  const {api} = await chromeApiFor(page);
  const result = await loadAttachment().attachResultFiles(api, {tabId:1}, evidenceFiles(), {settleMs:0});
  expect(result.evidence).toBe("composer");
});

test("a page that ignores the selection fails closed with diagnostics", async ({page}) => {
  await composerPage(page, "ignore");
  const {api} = await chromeApiFor(page);
  // The promise comes from a vm context (another realm); @playwright/test 1.62
  // rejects `.rejects` on it (CI #481). Settle it explicitly instead.
  const failure = await loadAttachment().attachResultFiles(api, {tabId:1}, evidenceFiles(),
    {settleMs:0, confirmTimeoutMs:1000}).then(() => null, error => error);
  expect(failure).not.toBeNull();
  expect(String(failure.message)).toContain("did not show the selected result evidence files");
});

test("re-delivery reuses evidence already attached in the composer", async ({page}) => {
  await composerPage(page, "full");
  const files = evidenceFiles();
  const first = await chromeApiFor(page);
  await loadAttachment().attachResultFiles(first.api, {tabId:1}, files, {settleMs:0});
  const second = await chromeApiFor(page);
  const result = await loadAttachment().attachResultFiles(second.api, {tabId:1}, files, {settleMs:0});
  expect(result.evidence).toBe("already_in_composer");
  expect(second.calls).not.toContain("DOM.setFileInputFiles");
  expect(await page.locator(".chip").count()).toBe(2);
});
