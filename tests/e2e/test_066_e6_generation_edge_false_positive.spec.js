const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const CONTENT_JS = path.join(ROOT, "chrome_extension", "cockpit_send.js");   // AGP_SEND_MODULE_V1

function extractFunction(text, name) {
  const re = new RegExp("(?:(?:async)\\s+)?function\\s+" + name + "\\s*\\(");
  const m = re.exec(text);
  if (!m) throw new Error(name + " missing");
  const brace = text.indexOf("{", m.index + m[0].length);
  if (brace < 0) throw new Error(name + " body missing");

  let depth = 0;
  let quote = null;
  let escape = false;
  let lineComment = false;
  let blockComment = false;

  for (let i = brace; i < text.length; i += 1) {
    const ch = text[i];
    const next = i + 1 < text.length ? text[i + 1] : "";

    if (lineComment) {
      if (ch === "\n") lineComment = false;
      continue;
    }
    if (blockComment) {
      if (ch === "*" && next === "/") {
        blockComment = false;
        i += 1;
      }
      continue;
    }
    if (quote) {
      if (escape) escape = false;
      else if (ch === "\\") escape = true;
      else if (ch === quote) quote = null;
      continue;
    }

    if (ch === "/" && next === "/") {
      lineComment = true;
      i += 1;
      continue;
    }
    if (ch === "/" && next === "*") {
      blockComment = true;
      i += 1;
      continue;
    }
    if (ch === "'" || ch === '"' || ch === "`") {
      quote = ch;
      continue;
    }
    if (ch === "{") depth += 1;
    else if (ch === "}") {
      depth -= 1;
      if (depth === 0) return text.slice(m.index, i + 1);
    }
  }
  throw new Error(name + " unterminated");
}

test("E6 generation acknowledgement requires a new generation edge", async () => {
  const src = fs.readFileSync(CONTENT_JS, "utf8");
  const waitBody = extractFunction(src, "waitForSentUserMessage");

  expect(waitBody).toMatch(/generationNow\s*&&\s*!beforeGenerationActive/);

  expect(waitBody).not.toMatch(
    /if\s*\(\s*generationNow\s*\)\s*\{\s*return\s*\{\s*confirmed\s*:\s*true\s*,\s*via\s*:\s*["']generation_active["']/
  );
});

test("E6 composer mutation remains provisional", async () => {
  const src = fs.readFileSync(CONTENT_JS, "utf8");
  const waitBody = extractFunction(src, "waitForSentUserMessage");
  expect(waitBody).toContain("provisionalComposerEvidence");
  expect(waitBody).not.toMatch(/confirmed\s*:\s*true\s*,\s*via\s*:\s*["']composer_(?:cleared|changed)["']/);
});

test("E6 positive acknowledgement still has independent decisive signals", async () => {
  const src = fs.readFileSync(CONTENT_JS, "utf8");
  const waitBody = extractFunction(src, "waitForSentUserMessage");
  expect(waitBody).toMatch(/via\s*:\s*["']user_message["']/);
  expect(waitBody).toContain("SEND_GENERATION_STARTED_OBSERVED");
  expect(waitBody).toContain("SEND_ASSISTANT_ACTIVITY_OBSERVED");
  expect(waitBody).toContain("authoritative_acceptance:false");
  expect(waitBody).toMatch(/confirmed\s*:\s*false/);
  expect(waitBody).toMatch(/via\s*:\s*["']timeout["']/);
});
