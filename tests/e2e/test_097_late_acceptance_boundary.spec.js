const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const SRC = fs.readFileSync(
  path.join(ROOT, "chrome_extension", "content.js"),
  "utf8"
);

test("097 timeout semantics use INDETERMINATE rather than timeout-only failure", async () => {
  expect(SRC).toContain('ACCEPTED_LATE:"ACCEPTED_LATE"');
  expect(SRC).toContain("transport.transition(SEND_TRANSPORT.INDETERMINATE");
  expect(SRC).toContain("positiveUnsentEvidence && transport.retryCount > 0");
  expect(SRC).toContain("positive evidence shows the prompt is still unsent");
});

test("097 retry eligibility requires positive unsent evidence", async () => {
  const safe = SRC.indexOf("const safeToRetry = (");
  const eligible = SRC.indexOf(
    "transport.transition(SEND_TRANSPORT.SAFE_RETRY_ELIGIBLE",
    safe
  );
  const retry = SRC.indexOf(
    "transport.transition(SEND_TRANSPORT.RETRY_ATTEMPTED",
    eligible
  );
  expect(safe).toBeGreaterThanOrEqual(0);
  expect(eligible).toBeGreaterThan(safe);
  expect(retry).toBeGreaterThan(eligible);
});

test("097 indeterminate transport is retained for late resolution", async () => {
  expect(SRC).toContain("let PENDING_SEND_TRANSPORT = null;");
  const pending = SRC.indexOf("PENDING_SEND_TRANSPORT = transport;");
  const indeterminate = SRC.indexOf(
    "transport.transition(SEND_TRANSPORT.INDETERMINATE",
    pending
  );
  const returnAfter = SRC.indexOf("return;", indeterminate);
  expect(pending).toBeGreaterThanOrEqual(0);
  expect(indeterminate).toBeGreaterThan(pending);
  expect(returnAfter).toBeGreaterThan(indeterminate);
});

test("097 new assistant completion resolves INDETERMINATE as ACCEPTED_LATE", async () => {
  const complete = SRC.indexOf('await clientEvent("ASSISTANT_RESPONSE_COMPLETE"');
  const pending = SRC.indexOf(
    "PENDING_SEND_TRANSPORT.state === SEND_TRANSPORT.INDETERMINATE",
    complete
  );
  const acceptedLate = SRC.indexOf(
    "PENDING_SEND_TRANSPORT.transition(SEND_TRANSPORT.ACCEPTED_LATE",
    pending
  );
  const terminal = SRC.indexOf("PENDING_SEND_TRANSPORT = null;", acceptedLate);
  expect(complete).toBeGreaterThanOrEqual(0);
  expect(pending).toBeGreaterThan(complete);
  expect(acceptedLate).toBeGreaterThan(pending);
  expect(terminal).toBeGreaterThan(acceptedLate);
});

test("097 late acceptance is correlated to a changed assistant response", async () => {
  expect(SRC).toContain("PENDING_SEND_TRANSPORT.beforeAssistantText");
  expect(SRC).toContain('via:"late_assistant_response"');
  expect(SRC).toContain('await clientEvent("SEND_LATE_ACCEPTED"');
});
