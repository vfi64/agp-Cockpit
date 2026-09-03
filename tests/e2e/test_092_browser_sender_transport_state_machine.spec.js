const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");

const SRC = fs.readFileSync(
  path.join(__dirname, "../../chrome_extension/content.js"),
  "utf8"
);

function sendPromptBody() {
  const start = SRC.indexOf("async function sendPrompt(");
  const nextAsync = SRC.indexOf("\n  async function ", start + 10);
  const nextFunction = SRC.indexOf("\n  function ", start + 10);
  const candidates = [nextAsync, nextFunction].filter(v => v > start);
  const end = candidates.length ? Math.min(...candidates) : SRC.length;
  return SRC.slice(start, end);
}

test("092 browser sender declares one explicit transport state model", async () => {
  for (const state of [
    "IDLE",
    "DRAFT_WRITTEN",
    "SUBMIT_ATTEMPTED",
    "WAITING_FOR_ACCEPTANCE",
    "ACCEPTED",
    "SAFE_RETRY_ELIGIBLE",
    "RETRY_ATTEMPTED",
    "INDETERMINATE",
    "FAILED_CONFIRMATION"
  ]) {
    expect(SRC).toContain(`${state}:"${state}"`);
  }
  expect(SRC).toContain("function createSendTransport(prompt)");
});

test("092 transport transitions structurally wrap first acknowledgement wait", async () => {
  const body = sendPromptBody();
  const firstWait = body.indexOf("waitForSentUserMessage(");
  expect(firstWait).toBeGreaterThan(-1);

  const attempted = body.lastIndexOf(
    "transport.transition(SEND_TRANSPORT.SUBMIT_ATTEMPTED",
    firstWait
  );
  const waiting = body.lastIndexOf(
    "transport.transition(SEND_TRANSPORT.WAITING_FOR_ACCEPTANCE",
    firstWait
  );

  expect(attempted).toBeGreaterThan(-1);
  expect(waiting).toBeGreaterThan(attempted);
  expect(firstWait).toBeGreaterThan(waiting);
});

test("092 keeps acknowledgement declaration syntactically singular", async () => {
  const body = sendPromptBody();
  expect(body).not.toContain("acknowledgement = await transport.transition");
});

test("092 preserves exactly one bounded retry state transition", async () => {
  const body = sendPromptBody();
  expect(body).toContain("transport.transition(SEND_TRANSPORT.SAFE_RETRY_ELIGIBLE");
  expect(body).toContain("transport.retryCount += 1;");
  expect(body).toContain("transport.transition(SEND_TRANSPORT.RETRY_ATTEMPTED");
  const retryCountMatches = body.match(/transport\.retryCount \+= 1;/g) || [];
  expect(retryCountMatches).toHaveLength(1);
});

test("092 terminal transport states precede legacy result states", async () => {
  const body = sendPromptBody();

  const failed = body.indexOf(
    "transport.transition(SEND_TRANSPORT.FAILED_CONFIRMATION"
  );
  const unconfirmed = body.indexOf('STATE.lastEvent = "SEND_UNCONFIRMED"');
  expect(failed).toBeGreaterThan(-1);
  expect(unconfirmed).toBeGreaterThan(failed);

  const accepted = body.indexOf(
    "transport.transition(SEND_TRANSPORT.ACCEPTED"
  );
  const sent = body.indexOf('STATE.lastEvent = "PROMPT_SENT"');
  expect(accepted).toBeGreaterThan(-1);
  expect(sent).toBeGreaterThan(accepted);
});
