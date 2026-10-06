// AGP_CORRECTABLE_REJECTION_V1: the actual content script sends the correction
// prompt for a rejected work order and keeps the run going.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start) + 1));
const code = section("  async function submitAssistantCommandFile(", "  function composer()")
  + section("  async function processCompletedAssistant(", "\n  async function ");

(async () => {
  const calls = [];
  const sent = [];
  const context = {
    STATE:{running:true, runGeneration:1, turns:2, nextLocalStep:1540, waitingForAssistant:false},
    clientEvent:async (name) => { calls.push("event:" + name); },
    assistantPythonAttachmentCandidates:() => [{name:"1540_x.py"}],
    fetchSingleAssistantPythonAttachment:async () => ({filename:"1540_x.py", content:"print(1)", chars:8}),
    lastAssistantMessageId:() => "m1",
    // AGP_REJECTED_ORDER_KEPT_V1: the bridge kept the rejected order; the browser copy goes.
    forgetBrowserDownload:async (fetched) => { calls.push("forget:" + fetched.filename); },
    api:async (path) => {
      calls.push(path);
      return {state:"CONTINUE", terminal:false, step:1540, next_step:1541, result_file:null,
              prompt:"AGP COCKPIT — WORK ORDER NOT EXECUTED", human_reason:"Auftrag abgelehnt — x"};
    },
    captureAssistantBaseline:() => { calls.push("baseline"); },
    sendPrompt:async prompt => { sent.push(prompt); },
    resetCandidate:() => {}, render:() => {},
    Date,
  };
  vm.createContext(context);
  vm.runInContext(code, context);
  await context.processCompletedAssistant("", 1);
  assert.deepEqual(sent, ["AGP COCKPIT — WORK ORDER NOT EXECUTED"]);
  assert.equal(context.STATE.nextLocalStep, 1541);
  assert.equal(context.STATE.waitingForAssistant, true);
  assert.equal(context.STATE.running, true);
  assert.equal(context.STATE.lastEvent, "K07_WORK_ORDER_REJECTED_FOR_CORRECTION");
  assert.ok(calls.includes("/v1/file-loop/command"));
  assert.ok(calls.includes("event:K07_WORK_ORDER_REJECTED_FOR_CORRECTION"));
  assert.ok(calls.includes("forget:1540_x.py"));
})().catch(error => { console.error(error); process.exitCode = 1; });
