// AGP_SEND_NOT_READY_RETRY_V1: the actual sendPrompt/sendPromptFailed of
// cockpit_send.js (AGP_SEND_MODULE_V1) with stubs — one diagnosed retry after a text-only clean.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/cockpit_send.js", "utf8");
const start = source.indexOf("  async function sendPrompt(prompt) {");
const end = source.indexOf("  async function sendPromptDomDegraded(prompt)", start);
const code = source.slice(start, end);

async function run({failures, cleanOk = true}) {
  const calls = [];
  let attempts = 0;
  const context = {
    STATE:{}, AGP_ALLOW_DEGRADED_DOM_FALLBACK:false,
    clientEvent:async (name, details) => { calls.push(["event", name, details]); },
    sleep:async (ms) => { calls.push(["sleep", ms]); },
    sendPromptNative:async () => {
      attempts += 1;
      if (attempts <= failures) {
        const error = new Error("native transport rejected");
        error.response = {stage:"SEND_BUTTON_NOT_READY", form_buttons:[{aria_label:"x"}], readiness_wait_ms:30000};
        throw error;
      }
      return "sent";
    },
    chrome:{runtime:{sendMessage:async (message) => { calls.push(["message", message]); return {ok:cleanOk, stage:"COMPOSER_CLEANED"}; }}},
  };
  vm.createContext(context);
  vm.runInContext(code + "; globalThis.sendPrompt = sendPrompt;", context);
  let result = null;
  let error = null;
  try { result = await context.sendPrompt("p"); } catch (err) { error = err; }
  return {calls, attempts, result, error};
}

(async () => {
  let r = await run({failures:1});
  assert.equal(r.result, "sent");
  assert.equal(r.attempts, 2);
  const names = r.calls.map(c => c[1] && c[0] === "event" ? c[1] : c[0]);
  assert.deepEqual(names, ["SEND_BUTTON_NOT_READY_DIAGNOSED", "message", "sleep", "SEND_RETRY_AFTER_NOT_READY"]);
  assert.equal(JSON.stringify(r.calls[1][1]), JSON.stringify({type:"AGP_K07_CLEAN_COMPOSER", files:false}));
  assert.equal(r.calls[2][1], 15000);

  r = await run({failures:2});
  assert.ok(r.error && r.attempts === 2);   // only one retry
  assert.ok(r.calls.some(c => c[1] === "NATIVE_TRANSPORT_FAILED"));

  r = await run({failures:1, cleanOk:false});
  assert.ok(r.error && r.attempts === 1);   // no retry over an unclean composer
  console.log("send_not_ready_retry ok");
})().catch(error => { console.error(error); process.exit(1); });
