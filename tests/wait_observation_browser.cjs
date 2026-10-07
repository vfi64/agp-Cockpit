// AGP_INGRESS_MODULE_V1 regression (live r11, step 1888): the actual wait observation of
// content.js runs with the ingress module bound exactly as content.js binds it — no
// ReferenceError, and it reports the expected-step candidates of the module.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const start = source.indexOf("  async function reportAssistantWaitObservation(");
const code = source.slice(start, source.indexOf("\n  }\n", start) + 5);
const bind = source.slice(source.indexOf("  const {\n", source.indexOf("AGP_INGRESS.create(")),
                          source.indexOf("} = INGRESS;") + "} = INGRESS;".length);

const events = [];
const card = {getAttribute: name => (name === "aria-label" ? "1888_wait.py" : null), textContent: "1888_wait.py"};
const context = {
  STATE: {nextLocalStep: 1888, lastAssistantObservationAt: 0},
  document: {querySelectorAll: () => [card]},
  clientEvent: async (name, details) => { events.push([name, details]); },
  assistantBaselineIds: () => new Set(),
  chatgptGenerationActive: () => false,
};
vm.createContext(context);
vm.runInContext(fs.readFileSync("chrome_extension/chatgpt_selectors.js", "utf8"), context);
vm.runInContext(fs.readFileSync("chrome_extension/chatgpt_dom.js", "utf8"), context);
// Not the harness: it would expose every module function in the context and hide a missing binding.
vm.runInContext(fs.readFileSync("chrome_extension/cockpit_ingress.js", "utf8"), context);
const ingress = vm.runInContext("AGP_INGRESS", context).create({state: context.STATE});
context.INGRESS = ingress;
ingress.expectedStepAttachmentCandidates = step => (step === 1888 ? [{name: "1888_wait.py"}] : []);
vm.runInContext(bind.replace("const {", "var {") + "\n" + code, context);
context.reportAssistantWaitObservation("waiting").then(() => {
  assert.equal(events.length, 1);
  assert.equal(events[0][0], "K07_ASSISTANT_WAIT_OBSERVATION");
  assert.equal(events[0][1].expected_candidates, 1);
  console.log("wait_observation_browser: PASS");
}).catch(error => { console.error(error); process.exit(1); });
