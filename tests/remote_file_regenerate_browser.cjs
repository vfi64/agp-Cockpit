// AGP_K07_REMOTE_FILE_REGENERATE_V1: a remote file whose download fails on the chat side is
// requested once more under the next step instead of stopping the task (live 2026-10-04,
// release 0.1.1, step 1712: "Herunterladen der Datei fehlgeschlagen").
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const code = section("  // AGP_K07_REMOTE_FILE_REGENERATE_V1", "  async function tick()");
assert.ok(code.includes("async function requestRemoteFileRegeneration"));

function setup({running=true, advance=true, candidates=[{name:"1712_agp_terminal.json"}], terminal=null} = {}) {
  const calls = {reserved:[], prompts:[], events:[], baseline:0};
  const STATE = {running, runGeneration:3, nextLocalStep:1712, lastProcessedAssistantAttachmentKey:"",
                 waitingForAssistant:false, assistantWaitStartedAt:0};
  const context = vm.createContext({
    STATE, Date, Number, String,
    assistantPythonAttachmentCandidates:() => candidates,
    ...(terminal ? {expectedStepTerminalCandidates:() => terminal} : {}),
    assistantAttachmentKey:list => `key:${list[0].name}`,
    reserveRemoteStep:async (reason, step) => { calls.reserved.push([reason, step]); if (advance) STATE.nextLocalStep = step + 1; },
    clientEvent:async (name, details) => { calls.events.push([name, details]); },
    digest:async text => `sha:${text}`, lastAssistantText:() => "old answer",
    captureAssistantBaseline:() => { calls.baseline += 1; }, resetCandidate:() => {}, render:() => {},
    sendPrompt:async prompt => { calls.prompts.push(prompt); },
  });
  vm.runInContext(code, context);
  const request = err => vm.runInContext("requestRemoteFileRegeneration", context)(err, 3);
  return {STATE, calls, request, context};
}

const TIMEOUT = new Error("K07 command-file browser download timed out");

(async () => {
  // 1. The first failed download asks for the same answer as a new file under the next step.
  let t = setup();
  assert.equal(await t.request(TIMEOUT), true);
  assert.deepEqual(t.calls.reserved, [["unloadable-remote-attachment", 1712]]);
  assert.equal(t.calls.prompts.length, 1);
  assert.match(t.calls.prompts[0], /^FILE TRANSFER REPAIR ONLY\. The file 1712_agp_terminal\.json /);
  assert.match(t.calls.prompts[0], /new file for local step 1713/);
  assert.match(t.calls.prompts[0], /1713_agp_terminal\.json/);
  assert.match(t.calls.prompts[0], /do not change the decision/);
  assert.equal(t.calls.events[0][0], "K07_REMOTE_FILE_REGENERATION_REQUESTED");
  assert.equal(t.calls.events[0][1].next_step, 1713);
  assert.equal(t.STATE.lastProcessedAssistantAttachmentKey, "key:1712_agp_terminal.json");   // never retried
  assert.equal(t.calls.baseline, 1);
  assert.equal(t.STATE.waitingForAssistant, true);

  // 2. Only once per answer: a second failure falls back to the old error path.
  assert.equal(await t.request(TIMEOUT), false);
  vm.runInContext("AGP_REMOTE_FILE_REGENERATE_ATTEMPTS = 0;", t.context);   // reset after a consumed file
  assert.equal(await t.request(new Error("browser download interrupted: NETWORK_FAILED")), true);

  // 3. Other errors, a stopped run or an unclear card change nothing.
  assert.equal(await setup().request(new Error("K07 composer focus could not be restored")), false);
  assert.equal(await setup({running:false}).request(TIMEOUT), false);
  t = setup({candidates:[]});
  assert.equal(await t.request(TIMEOUT), false);
  assert.equal(t.calls.prompts.length, 0);

  // 3b. AGP_K07_TERMINAL_REGENERATE_V1 (live 2026-10-07, step 1862): the lost file is a terminal
  // reply; the command-file lookup sees no .py card, the terminal lookup finds it.
  t = setup({candidates:[], terminal:[{name:"1862_agp_terminal.json"}]});
  t.STATE.nextLocalStep = 1862;
  assert.equal(await t.request(TIMEOUT), true);
  assert.deepEqual(t.calls.reserved, [["unloadable-remote-attachment", 1862]]);
  assert.match(t.calls.prompts[0], /The file 1862_agp_terminal\.json /);
  assert.match(t.calls.prompts[0], /1863_agp_terminal\.json/);

  // 4. If the bridge does not advance the step, nothing is sent.
  t = setup({advance:false});
  await assert.rejects(t.request(TIMEOUT), /could not be reserved/);
  assert.equal(t.calls.prompts.length, 0);

  // 5. Wiring: the tick's error path asks first; every reset point clears the attempt.
  const tick = section("  async function tick()", "  const LIVE_PROBE");
  assert.ok(tick.indexOf("requestRemoteFileRegeneration(err, runGeneration)") <
            tick.indexOf("if (STATE.errors >= LIMITS.maxErrors)"));
  // declaration, stop(), startAuto() and both consumed-file paths
  assert.equal(source.split("AGP_REMOTE_FILE_REGENERATE_ATTEMPTS = 0;").length - 1, 5);
  console.log("remote_file_regenerate_browser: PASS");
})().catch(err => { console.error(err); process.exit(1); });
