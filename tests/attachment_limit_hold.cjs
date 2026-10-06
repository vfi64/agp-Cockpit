// AGP_ATTACHMENT_LIMIT_HOLD_V1: drives the actual content-script tick/stop with stubs.
// The live failure of 2026-10-06 (step 63) must hold the task, not count errors,
// and re-process the same visible command file once the named time has passed.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const code = section("  async function stop(", "  function scheduleTick()") + section("  async function tick()", "  const LIVE_PROBE");
const LIMIT = 'Error: ChatGPT composer did not show the selected result evidence files: {"before":{"composer_sample":' +
  '["Du hast das Limit für Dateianhänge erreicht","Erneut versuchen 6. Okt., 19:49","063_gf';

async function main() {
  const calls = [];
  let attempts = 0;
  let now = new Date(2026, 9, 6, 18, 2).getTime();
  const RealDate = Date;
  class FakeDate extends RealDate {
    constructor(...args) { super(...(args.length ? args : [now])); }
    static now() { return now; }
  }
  const context = {
    Date:FakeDate,
    STATE:{running:true, paused:false, runGeneration:1, turns:13, errors:0, nextLocalStep:63,
           waitingForAssistant:true, assistantWaitStartedAt:now, processingAssistant:false,
           pendingAttachmentKey:"", lastProcessedAssistantAttachmentKey:"", transportHoldUntil:0},
    PENDING_SEND_TRANSPORT:null, AGP_FORMAT_REPAIR_ATTEMPTS:0, AGP_REMOTE_FILE_REGENERATE_ATTEMPTS:0,
    LIMITS:{minAssistantChars:1, stablePollsRequired:2, maxErrors:3},
    clientEvent:async (name, details) => { calls.push("event:" + name + " " + JSON.stringify(details || {})); },
    resetCandidate:() => {}, render:() => {}, clearInterval:() => {}, retireIfOrphaned:() => false,
    api:async (path, options) => { calls.push(path + (options && options.body ? " " + options.body : "")); return {}; },
    pollOperatorControl:async () => {}, pollExplicitTaskStartRequest:async () => {}, refreshLiveMissionStatus:async () => {},
    expectedStepFileVisible:() => true, chatgptGenerationActive:() => false,
    newAssistantTextAfterBaseline:() => "", reportAssistantWaitObservation:async () => {},
    expectedStepTerminalCandidates:() => [],
    assistantPythonAttachmentCandidates:() => [{name:"63_gf050b_origin_diff_scope.py"}],
    assistantAttachmentKey:c => c[0].name,
    lastAssistantText:() => "",
    requestRemoteFileRegeneration:async () => false,
    processCompletedAssistant:async () => {
      attempts += 1;
      if (attempts === 1) throw new Error(LIMIT);
      return true;                         // re-delivered
    },
  };
  vm.createContext(context);
  vm.runInContext(code, context);
  await context.tick();   // settling
  await context.tick();   // consume -> attachment limit
  assert.equal(attempts, 1);
  assert.equal(context.STATE.running, true);
  assert.equal(context.STATE.errors, 0);
  assert.equal(context.STATE.lastEvent, "K07_ATTACHMENT_LIMIT_HOLD");
  assert.match(context.STATE.note, /19:50/);
  assert.equal(context.STATE.assistantWaitStartedAt, 0);
  assert.equal(calls.some(call => call.startsWith("/v1/file-loop/control")), false);
  assert.ok(calls.some(call => call.startsWith("event:K07_ATTACHMENT_LIMIT_HOLD")));

  now += 60 * 60 * 1000;                   // 19:02: still holding
  await context.tick(); await context.tick();
  assert.equal(attempts, 1);

  now += 50 * 60 * 1000;                   // 19:52: retry the same visible file
  await context.tick();   // hold ends, settling
  await context.tick();   // consume -> re-delivered
  assert.equal(attempts, 2);
  assert.equal(context.STATE.transportHoldUntil, 0);
  assert.ok(calls.some(call => call.startsWith("event:K07_ATTACHMENT_LIMIT_RETRY")));
  assert.equal(context.STATE.lastProcessedAssistantAttachmentKey, "63_gf050b_origin_diff_scope.py");
  assert.equal(context.STATE.running, true);
}

main().then(() => console.log("attachment limit hold ok")).catch(error => { console.error(error); process.exit(1); });
