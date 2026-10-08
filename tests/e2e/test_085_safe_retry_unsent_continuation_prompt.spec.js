const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "../..");
// AGP_SEND_MODULE_V1: the send transport lives in cockpit_send.js.
const source = fs.readFileSync(path.join(root, "chrome_extension", "content.js"), "utf8") + "\n" +
  fs.readFileSync(path.join(root, "chrome_extension", "cockpit_send.js"), "utf8");

test("085 retry eligibility still requires exact pending prompt and no generation", async () => {
  const unconfirmed = source.indexOf("if (!acknowledgement.confirmed)");
  expect(unconfirmed).toBeGreaterThan(0);

  const tail = source.slice(unconfirmed, unconfirmed + 3200);
  expect(tail).toContain("pendingComposer === expectedPrompt");
  expect(tail).toContain("!chatgptGenerationActive()");
  expect(tail).toContain("SEND_RETRY_SAFE_PENDING_COMPOSER");
});

test("085 retry remains bounded to one extra send attempt", async () => {
  const retryState = source.indexOf(
    "transport.transition(SEND_TRANSPORT.RETRY_ATTEMPTED"
  );
  expect(retryState).toBeGreaterThan(0);

  const tail = source.slice(retryState - 900, retryState + 2200);
  const retryClicks = (tail.match(/retryButton\.click\(\)/g) || []).length;

  expect(retryClicks).toBe(1);
  expect(tail).toContain("transport.retryCount += 1");
  expect(tail).toContain("{attempt:2}");
});

test("085 weak composer mutation alone never authorizes retry", async () => {
  const unconfirmed = source.indexOf("if (!acknowledgement.confirmed)");
  expect(unconfirmed).toBeGreaterThan(0);

  const tail = source.slice(unconfirmed, unconfirmed + 3200);
  expect(tail).not.toContain('provisional === "composer_cleared"');
  expect(tail).not.toContain('provisional === "composer_changed"');
  expect(tail).toContain("pendingComposer === expectedPrompt");
  expect(tail).toContain("!chatgptGenerationActive()");
});

test("085 timeout without positive unsent evidence can remain indeterminate", async () => {
  const unconfirmed = source.indexOf("if (!acknowledgement.confirmed)");
  const indeterminate = source.indexOf(
    "transport.transition(SEND_TRANSPORT.INDETERMINATE",
    unconfirmed
  );

  expect(indeterminate).toBeGreaterThan(unconfirmed);
  const tail = source.slice(unconfirmed, indeterminate + 600);
  expect(tail).toContain("positiveUnsentEvidence");
  expect(tail).toContain("transport.retryCount > 0");
});
