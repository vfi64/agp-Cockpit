const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");

const source = fs.readFileSync(
  path.resolve(__dirname, "../../chrome_extension/content.js"), "utf8"
);
// AGP_PANEL_MODULE_V1: the overlay buttons live in cockpit_panel.js.
const panel = fs.readFileSync(
  path.resolve(__dirname, "../../chrome_extension/cockpit_panel.js"), "utf8"
);

test("077 action buttons are explicit non-submit buttons with click telemetry", async () => {
  expect(source).toContain("AGP_START_AUTO_CLICK_PATH_077");
  expect(panel).toContain('b.type = "button";');
  expect(panel).toContain('b.addEventListener("mousedown"');
  expect(panel).toContain('b.addEventListener("click"');
  expect(panel).toContain('host.clientEvent("UI_BUTTON_CLICKED"');
  expect(panel).toContain("event.preventDefault()");
  expect(panel).toContain("event.stopPropagation()");
  expect(source).toContain("start:() => startAuto()");
});

test("077 Start Auto emits stage evidence before bootstrap preparation", async () => {
  const start = source.indexOf("async function startAuto()");
  const end = source.indexOf("// AGP_START_AUTO_CLICK_PATH_077", start);
  const body = source.slice(start, end);
  expect(body).toContain('clientEvent("AUTO_START_REQUESTED"');
  expect(body).toContain('clientEvent("AUTO_STATUS_REFRESHED"');
  expect(body).toContain('STATE.lastEvent = "MISSION_BOOTSTRAP_PREPARED"');
  expect(body.indexOf('clientEvent("AUTO_START_REQUESTED"'))
    .toBeLessThan(body.indexOf("await refreshStatus()"));
  expect(body.indexOf('clientEvent("AUTO_STATUS_REFRESHED"'))
    .toBeLessThan(body.indexOf('STATE.lastEvent = "MISSION_BOOTSTRAP_PREPARED"'));
});
