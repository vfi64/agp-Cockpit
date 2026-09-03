const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");

const source = fs.readFileSync(
  path.resolve(__dirname, "../../chrome_extension/content.js"), "utf8"
);

test("077 action buttons are explicit non-submit buttons with click telemetry", async () => {
  expect(source).toContain("AGP_START_AUTO_CLICK_PATH_077");
  expect(source).toContain('b.type = "button";');
  expect(source).toContain('b.addEventListener("mousedown"');
  expect(source).toContain('b.addEventListener("click"');
  expect(source).toContain('clientEvent("UI_BUTTON_CLICKED"');
  expect(source).toContain("event.preventDefault()");
  expect(source).toContain("event.stopPropagation()");
});

test("077 Start Auto emits stage evidence before bootstrap preparation", async () => {
  const start = source.indexOf("async function startAuto()");
  const end = source.indexOf("function btn(", start);
  const body = source.slice(start, end);
  expect(body).toContain('clientEvent("AUTO_START_REQUESTED"');
  expect(body).toContain('clientEvent("AUTO_STATUS_REFRESHED"');
  expect(body).toContain('STATE.lastEvent = "MISSION_BOOTSTRAP_PREPARED"');
  expect(body.indexOf('clientEvent("AUTO_START_REQUESTED"'))
    .toBeLessThan(body.indexOf("await refreshStatus()"));
  expect(body.indexOf('clientEvent("AUTO_STATUS_REFRESHED"'))
    .toBeLessThan(body.indexOf('STATE.lastEvent = "MISSION_BOOTSTRAP_PREPARED"'));
});
