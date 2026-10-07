// AGP_INGRESS_MODULE_V1: load chrome_extension/cockpit_ingress.js into a vm context the way
// content.js creates it. Host services resolve lazily from the context (the test's stubs); a
// function the test already stubbed in the context replaces that step of the module (`self`
// seam), every other module function is exposed in the context under its old content.js name.
const fs = require("node:fs");
const vm = require("node:vm");

const SOURCE = fs.readFileSync("chrome_extension/cockpit_ingress.js", "utf8");
const HOST = ["api", "clientEvent", "composer", "assistantBaselineIds", "selectedAssistantMessageNode",
  "lastAssistantMessageId", "reserveRemoteStep", "snapshotAssistantBaseline", "applyAssistantBaseline"];

function bindIngress(context) {
  vm.runInContext(SOURCE, context);
  const host = {state: context.STATE};
  for (const name of HOST) {
    host[name] = (...args) => {
      if (typeof context[name] !== "function") throw new Error(`ingress host service missing in test: ${name}`);
      return context[name](...args);
    };
  }
  const ingress = vm.runInContext("AGP_INGRESS", context).create(host);
  for (const name of Object.keys(ingress)) {
    if (typeof context[name] === "function") ingress[name] = context[name];   // the test's stub
    else context[name] = ingress[name];
  }
  return ingress;
}

module.exports = {bindIngress};
