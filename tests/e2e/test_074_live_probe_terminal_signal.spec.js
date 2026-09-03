const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const source = fs.readFileSync(
  path.resolve(__dirname, "../../chrome_extension/content.js"),
  "utf8"
);

test("074 terminal mission signals bypass live-probe work-order assertions", async () => {
  expect(source).toContain("AGP_LIVE_PROBE_TERMINAL_SIGNAL_074");
  expect(source).toContain('["DONE", "NEEDS_HUMAN"].includes(terminalState)');
  expect(source).toContain("assertExactLiveProbeWorkOrder(text);");
  expect(source).toContain("assertBoundedMultiTurnLiveProbeWorkOrder(text);");

  const marker = source.indexOf("AGP_LIVE_PROBE_TERMINAL_SIGNAL_074");
  const submit = source.indexOf("async function submitAssistant(text)");
  const firstAssert = source.indexOf("assertExactLiveProbeWorkOrder(text);", submit);

  expect(submit).toBeGreaterThanOrEqual(0);
  expect(marker).toBeGreaterThan(submit);
  expect(firstAssert).toBeGreaterThan(marker);
});

test("074 terminal states are narrowly limited", async () => {
  const segmentStart = source.indexOf("AGP_LIVE_PROBE_TERMINAL_SIGNAL_074");
  const segmentEnd = source.indexOf('STATE.lastEvent = "TURN_SUBMIT_STARTED"', segmentStart);
  const segment = source.slice(segmentStart, segmentEnd);

  expect(segment).toContain('"DONE"');
  expect(segment).toContain('"NEEDS_HUMAN"');
  expect(segment).not.toContain('"FAILED"');
  expect(segment).not.toContain('"PASS"');
});
