const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const CONTENT_JS = path.join(ROOT, "chrome_extension", "content.js");
const SEND_JS = path.join(ROOT, "chrome_extension", "cockpit_send.js");   // AGP_SEND_MODULE_V1

function source() {
  return fs.readFileSync(CONTENT_JS, "utf8") + "\n" + fs.readFileSync(SEND_JS, "utf8");
}

function functionBody(src, name) {
  const start = src.indexOf(`async function ${name}(`);
  if (start < 0) throw new Error(`missing function ${name}`);
  const brace = src.indexOf("{", start);
  if (brace < 0) throw new Error(`missing body for ${name}`);
  let depth = 0;
  for (let i = brace; i < src.length; i += 1) {
    if (src[i] === "{") depth += 1;
    if (src[i] === "}") {
      depth -= 1;
      if (depth === 0) return src.slice(start, i + 1);
    }
  }
  throw new Error(`unterminated function ${name}`);
}

test("G4 requires four independent bounded send-acceptance signals", async () => {
  const src = source();
  const body = functionBody(src, "waitForSentUserMessage");

  expect(body).toContain("visibleUserMessages");
  expect(body).toContain("normalizeObservedMessageText");
  expect(body).toMatch(/via\s*:\s*["']user_message["']/);

  expect(body).toMatch(/composer_(cleared|changed)|via\s*:\s*["']composer_(cleared|changed)["']/);

  expect(body).toMatch(/generation_(started|active)|chatgpt_(busy|generating)|via\s*:\s*["']generation_(started|active)["']/);

  expect(body).toMatch(/assistantNow|lastAssistantText/);
  expect(body).toContain("SEND_ASSISTANT_ACTIVITY_OBSERVED");
  expect(body).toContain("authoritative_acceptance:false");

  expect(body).toMatch(/return\s*\{\s*confirmed\s*:\s*false\s*,\s*via\s*:\s*["\']timeout["\']/);
});

test("G4 keeps acknowledgement bounded and does not treat click-attempt as success", async () => {
  const src = source();
  const waitBody = functionBody(src, "waitForSentUserMessage");
  const sendBody = functionBody(src, "sendPromptDomDegraded");

  expect(waitBody).toMatch(/for\s*\(let\s+i\s*=\s*0;\s*i\s*<\s*\d+/);
  expect(waitBody).toMatch(/setTimeout/);

  const clickIndex = Math.max(
    sendBody.indexOf("button.click()"),
    sendBody.indexOf("requestSubmit()"),
    sendBody.indexOf("dispatchEvent(down)")
  );
  const promptSentIndex = sendBody.indexOf('STATE.lastEvent = "PROMPT_SENT"');
  expect(clickIndex).toBeGreaterThanOrEqual(0);
  expect(promptSentIndex).toBeGreaterThan(clickIndex);

  expect(sendBody).toMatch(/acknowledg/);
  expect(sendBody).toMatch(/if\s*\(\s*!acknowledgement\.confirmed\s*\)/);
});

test("G4 encodes the observed real-browser regression", async () => {
  const src = source();
  expect(src).toMatch(/assistant_(response|activity)/);
  expect(src).toContain("SEND_UNCONFIRMED");
});
