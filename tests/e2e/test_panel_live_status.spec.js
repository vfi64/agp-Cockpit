// AGP_PANEL_LIVE_STATUS_V1: pure helpers of the live panel (no browser needed).
const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const ROOT = path.resolve(__dirname, "../..");
function helpers() {
  const context = {};
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(ROOT, "chrome_extension/native_message_evidence.js"), "utf8"), context);
  return context;
}

test("the live merge updates only the counters of the same mission", () => {
  const {agpMergeLiveMission} = helpers();
  const current = {mission_id:"m1", state:"READY", title:"Abschließen", turn_count:0, step_count:0};
  const merged = agpMergeLiveMission(current, {mission_id:"m1", state:"DONE", title:"x", turn_count:1, step_count:1});
  expect(JSON.parse(JSON.stringify(merged))).toEqual(
    {mission_id:"m1", state:"READY", title:"Abschließen", turn_count:1, step_count:1});
  expect(agpMergeLiveMission(current, {mission_id:"m2", turn_count:5})).toBeNull();
  expect(agpMergeLiveMission(current, null)).toBeNull();
});

test("the phase text shows the running work order and the waiting time", () => {
  const {agpMissionPhaseText} = helpers();
  const now = 1_000_000;
  expect(agpMissionPhaseText({processingStartedAt:now - 252_000, processingFile:"1744_pr_create_complete.py"}, now))
    .toBe("1744_pr_create_complete.py läuft lokal seit 4:12");
  expect(agpMissionPhaseText({waitingForAssistant:true, assistantWaitStartedAt:now - 9_000}, now))
    .toBe("wartet auf ChatGPT seit 0:09");
  expect(agpMissionPhaseText({}, now)).toBe("");
});
