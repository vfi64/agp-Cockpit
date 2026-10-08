// AGP_K07_ASSISTANT_ACTIVITY_WAIT_V1: drives the actual content-script tick and
// its wait-expiry helpers with stubs (live 2026-10-04, step 1689).
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const code = section("  async function tick()", "  // AGP_LEGACY_PATHS_REMOVED_V1");

function run({waitedMs, lastActivityAgoMs=null, generation=false, document=undefined, mutate=0}) {
  const now = Date.now();
  const stops = [];
  const events = [];
  const STATE = {running:true, paused:false, runGeneration:1, nextLocalStep:1689,
                 waitingForAssistant:true, assistantWaitStartedAt:now - waitedMs,
                 processingAssistant:false, pendingAttachmentKey:"", lastProcessedAssistantAttachmentKey:""};
  if (lastActivityAgoMs !== null) STATE.assistantLastActivityAt = now - lastActivityAgoMs;
  const context = vm.createContext({
    STATE, LIMITS:{minAssistantChars:1, stablePollsRequired:2}, Date, Math, Number, String, Array,
    retireIfOrphaned:() => false, pollOperatorControl:async () => {}, pollExplicitTaskStartRequest:async () => {}, refreshLiveMissionStatus:async () => {},
    expectedStepFileVisible:() => false, newAssistantTextAfterBaseline:() => "",
    reportAssistantWaitObservation:async () => {}, chatgptGenerationActive:() => generation,
    clientEvent:async (name, details) => { events.push([name, details]); },
    stop:async (message, reason) => { stops.push([message, reason]); }, render:() => {},
    document,
  });
  vm.runInContext(fs.readFileSync("chrome_extension/chatgpt_selectors.js", "utf8"), context);   // AGP_SELECTOR_TABLE_V1
  vm.runInContext(fs.readFileSync("chrome_extension/chatgpt_dom.js", "utf8"), context);   // AGP_DOM_ADAPTER_V1
  vm.runInContext(code, context);
  if (mutate) vm.runInContext(`ASSISTANT_DOM_MUTATIONS += ${mutate};`, context);
  return vm.runInContext("tick()", context).then(() => ({STATE, stops, events}));
}

(async () => {
  // 1. No activity for more than 180 s: the old behaviour, with the cause named.
  let r = await run({waitedMs:181000});
  assert.equal(r.stops.length, 1);
  assert.match(r.stops[0][0], /^K07_ASSISTANT_RESPONSE_TIMEOUT after 181s \(180s without visible activity\)/);
  assert.equal(r.stops[0][1], "K07_ASSISTANT_WAIT_TIMEOUT");
  assert.equal(r.events[0][0], "K07_ASSISTANT_WAIT_TIMEOUT");
  assert.equal(r.events[0][1].idle, true);
  assert.equal(r.STATE.waitingForAssistant, false);

  // 2. Long wait, but activity 60 s ago: keep waiting (step 1689 would not stop).
  r = await run({waitedMs:400000, lastActivityAgoMs:60000});
  assert.equal(r.stops.length, 0);
  assert.equal(r.STATE.waitingForAssistant, true);

  // 3. Idle for 250 s, but new DOM changes now: activity, keep waiting.
  r = await run({waitedMs:300000, lastActivityAgoMs:250000, mutate:3});
  assert.equal(r.stops.length, 0);
  assert.ok(Date.now() - r.STATE.assistantLastActivityAt < 1000);

  // 4. A generating stop button keeps the wait alive ...
  r = await run({waitedMs:300000, lastActivityAgoMs:250000, generation:true});
  assert.equal(r.stops.length, 0);

  // 5. ... and so does a German "Stoppen" composer button without the old test id.
  const stoppen = {disabled:false, getAttribute:key => key === "aria-label" ? "Stoppen" : null};
  const document = {querySelector:() => null, getElementById:() => null, body:null,
                    querySelectorAll:selector => selector.includes("form button") ? [stoppen] : []};
  r = await run({waitedMs:300000, lastActivityAgoMs:250000, document});
  assert.equal(r.stops.length, 0);

  // 6. The hard maximum still ends an endless wait.
  r = await run({waitedMs:901000, generation:true});
  assert.equal(r.stops.length, 1);
  assert.match(r.stops[0][0], /^K07_ASSISTANT_RESPONSE_TIMEOUT after 901s \(maximum wait of 900s\)/);
  assert.equal(r.events[0][1].idle, false);
  console.log("assistant activity wait: 6 scenarios PASS");
})().catch(error => { console.error(error); process.exit(1); });
