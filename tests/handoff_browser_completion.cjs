const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const {bindIngress} = require("./ingress_harness.cjs");   // AGP_INGRESS_MODULE_V1
const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const code = section("  async function stop(", "  function scheduleTick()")
  + section("  async function processCompletedAssistant(", "  function newAssistantTextAfterBaseline");

async function scenario({pending=true, delivered=true}={}) {
  const calls = [];
  const context = {
    STATE: {running:true, runGeneration:1, turns:0, nextLocalStep:1467},
    expectedStepAttachmentCandidates:() => [], expectedStepFileVisible:() => false,
    reserveRemoteStep:async () => ({}),
    PENDING_SEND_TRANSPORT:null, AGP_FORMAT_REPAIR_ATTEMPTS:0,
    clientEvent:async () => {}, lastAssistantMessageId:() => "assistant",
    fetchSingleAssistantPythonAttachment:async () => ({filename:"1467_test.py", content:"pass"}),
    assistantPythonAttachmentCandidates:() => [{}],
    resetCandidate:() => {}, render:() => {}, refreshStatus:async () => {},
    captureAssistantBaseline:() => {}, clearInterval:() => {}, retireIfOrphaned:() => false, forgetBrowserDownload:async () => {}, digestAlreadyInChat:async () => false, rememberDigest:async () => {},
    snapshotAssistantBaseline:() => ({}), applyAssistantBaseline:() => {},
    api:async (path) => {
      calls.push(path);
      if (path === "/v1/file-loop/command") return {
        state:"COMMAND_FILE", terminal:false, result_file:"result.json", prompt:"receipt",
        completion_pending:pending, cycle_id:"cycle", result_sha256:"hash", step:1467, next_step:1468
      };
      if (path === "/v1/file-loop/result-delivered") return {state:"DONE", terminal:true};
      return {};
    },
    chrome:{runtime:{sendMessage:async () => {
      calls.push("send");
      return {ok:delivered, stage:delivered ? "RESULT_ATTACHED_AND_CONTINUATION_SENT" : "FAILED"};
    }}},
  };
  vm.createContext(context);
  vm.runInContext(code, context);
  bindIngress(context);
  if (!delivered) {
    await assert.rejects(context.processCompletedAssistant("", 1), /transport failed/);
    // AGP_K07_ADVANCE_STEP_AFTER_DELIVERY_V1: a failed delivery keeps the
    // current step as the awaited identity so replay can re-deliver it.
    assert.equal(context.STATE.nextLocalStep, 1467);
    assert.equal(calls.includes("/v1/file-loop/result-delivered"), false);
  } else {
    await context.processCompletedAssistant("", 1);
    assert.equal(context.STATE.nextLocalStep, 1468);
    assert.equal(context.STATE.turns, 1);
    assert.equal(context.STATE.running, !pending);
    assert.equal(calls.includes("/v1/file-loop/control"), false);
    // AGP_STOP_REASON_V1: stop re-reads /v1/status to show the final mission state.
    if (pending) assert.deepEqual(calls, ["/v1/file-loop/command", "send", "/v1/file-loop/result-delivered", "/v1/status"]);
    else assert.deepEqual(calls, ["/v1/file-loop/command", "send", "/v1/file-loop/delivery-ack"]);
  }
  await context.stop("operator stop");
  assert.deepEqual(calls.slice(-2), ["/v1/file-loop/control", "/v1/status"]);
}
(async () => {
  await scenario();
  await scenario({pending:false});
  await scenario({delivered:false});
})().catch(error => { console.error(error); process.exitCode = 1; });
