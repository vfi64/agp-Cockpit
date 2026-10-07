// AGP_K07_FAIL_FAST_REJECTION_V1 + AGP_BUILD_IDENTITY_GATE_V1 + AGP_STOP_REASON_V1
// Drives the actual content-script tick/startAuto/stop with stubs.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const stopCode = section("  async function stop(", "  function scheduleTick()");

function baseContext(calls) {
  return {
    STATE:{running:true, paused:false, runGeneration:1, turns:0, errors:0, nextLocalStep:1486,
           waitingForAssistant:true, assistantWaitStartedAt:Date.now(), processingAssistant:false,
           pendingAttachmentKey:"", lastProcessedAssistantAttachmentKey:""},
    PENDING_SEND_TRANSPORT:null, AGP_FORMAT_REPAIR_ATTEMPTS:0,
    LIMITS:{minAssistantChars:1, stablePollsRequired:2, maxErrors:3},
    clientEvent:async (name) => { calls.push("event:" + name); },
    resetCandidate:() => {}, render:() => {}, clearInterval:() => {}, retireIfOrphaned:() => false, forgetBrowserDownload:async () => {}, digestAlreadyInChat:async () => false, rememberDigest:async () => {},
    api:async (path, options) => {
      calls.push(path + (options && options.body ? " " + options.body : ""));
      return {};
    },
  };
}

async function rejectionStopsOnFirstError() {
  const calls = [];
  const context = Object.assign(baseContext(calls), {
    pollOperatorControl:async () => {}, pollExplicitTaskStartRequest:async () => {}, refreshLiveMissionStatus:async () => {},
    expectedStepFileVisible:() => true, chatgptGenerationActive:() => false,
    newAssistantTextAfterBaseline:() => "", reportAssistantWaitObservation:async () => {},
    expectedStepTerminalCandidates:() => [],
    assistantPythonAttachmentCandidates:() => [{name:"1486_x.py"}],
    assistantAttachmentKey:c => c[0].name,
    lastAssistantText:() => "",
    processCompletedAssistant:async () => {
      const error = new Error("ValueError: invalid command file");
      error.bridgeRejected = true;
      throw error;
    },
  });
  vm.createContext(context);
  vm.runInContext(stopCode + section("  async function tick()", "  const LIVE_PROBE"), context);
  await context.tick();   // settling
  await context.tick();   // consume -> rejected
  assert.equal(context.STATE.running, false);
  assert.equal(context.STATE.errors, 1);
  assert.ok(calls.includes("event:K07_BRIDGE_REJECTED"));
  const control = calls.find(call => call.startsWith("/v1/file-loop/control"));
  assert.match(control, /"action":"STOP"/);
  assert.match(control, /Vom Cockpit abgelehnt: ValueError: invalid command file/);
}

async function transientErrorIsRetried() {
  const calls = [];
  const context = Object.assign(baseContext(calls), {
    pollOperatorControl:async () => {}, pollExplicitTaskStartRequest:async () => {}, refreshLiveMissionStatus:async () => {},
    expectedStepFileVisible:() => true, chatgptGenerationActive:() => false,
    newAssistantTextAfterBaseline:() => "", reportAssistantWaitObservation:async () => {},
    expectedStepTerminalCandidates:() => [],
    assistantPythonAttachmentCandidates:() => [{name:"1486_x.py"}],
    assistantAttachmentKey:c => c[0].name,
    lastAssistantText:() => "",
    processCompletedAssistant:async () => { throw new Error("K07 command-file browser download timed out"); },
  });
  vm.createContext(context);
  vm.runInContext(stopCode + section("  async function tick()", "  const LIVE_PROBE"), context);
  await context.tick();
  await context.tick();
  assert.equal(context.STATE.running, true);
  assert.equal(calls.some(call => call.startsWith("/v1/file-loop/control")), false);
}

async function buildMismatchRefusesStart() {
  const calls = [];
  const context = Object.assign(baseContext(calls), {
    refreshStatus:async () => ({state:"READY", bridge_build_id:"old-build",
      mission:{mission_id:"m", state:"READY", mission_text:"x"}}),
    sendPrompt:async () => { calls.push("SEND"); },
    location:{href:"https://chatgpt.com/"},
  });
  context.STATE.running = false;
  context.globalThis = context;
  context.AGP_EXTENSION_BUILD_ID = "new-build";
  vm.createContext(context);
  const startCode = section("  async function startAuto()", "  // AGP_START_AUTO_CLICK_PATH_077");
  vm.runInContext(stopCode + startCode, context);
  await assert.rejects(context.startAuto(), /Build passt nicht: Cockpit-App old-build, Extension new-build/);
  assert.equal(calls.includes("SEND"), false);
  assert.ok(calls.includes("event:BUILD_MISMATCH_START_REFUSED"));
  assert.ok(calls.some(call => call.startsWith("/v1/file-loop/control") && call.includes("Build passt nicht")));
}


async function bootstrapAttachesKitDigest(attachOk) {
  const calls = [];
  const context = Object.assign(baseContext(calls), {
    refreshStatus:async () => ({state:"READY", bridge_build_id:"b", kit_command_digest_path:"/r/.local/agp-cockpit/kit/agentic-kit-command-digest.json",
      kit_manifest_sha:"ce455b7df8c5", mission:{mission_id:"m", state:"READY", mission_text:"x"}}),
    sendPrompt:async () => { calls.push("SEND"); },
    location:{href:"https://chatgpt.com/"},
    digest:async () => "h", lastAssistantText:() => "", chatgptGenerationActive:() => false,
    captureAssistantBaseline:() => {}, expectedStepFileVisible:() => false, sleep:async () => {},
    missionBootstrapPrompt:() => "BOOT", scheduleTick:() => {},
    agpMissionTouchpointCheck:() => ({ok:true, reason:"", snapshot:{}}),
    chrome:{runtime:{sendMessage:async (message) => {
      if (message.type === "AGP_K07_CLEAN_COMPOSER") { calls.push("CLEAN"); return {ok:true, stage:"COMPOSER_EMPTY"}; }
      calls.push("ATTACH " + message.type + " " + message.files.join(","));
      return attachOk ? {ok:true, evidence:"composer"} : {ok:false, error:"not shown"};
    }}},
  });
  context.STATE.running = false;
  context.globalThis = context;
  context.AGP_EXTENSION_BUILD_ID = "b";
  vm.createContext(context);
  vm.runInContext(stopCode + section("  async function startAuto()", "  // AGP_START_AUTO_CLICK_PATH_077"), context);
  if (attachOk) {
    await context.startAuto();
    const attach = calls.findIndex(call => call.startsWith("ATTACH AGP_K07_ATTACH_FILES /r/.local/agp-cockpit/kit/agentic-kit-command-digest.json"));
    assert.ok(attach >= 0 && attach < calls.indexOf("SEND"));
    assert.ok(calls.indexOf("CLEAN") >= 0 && calls.indexOf("CLEAN") < attach);   // AGP_COMPOSER_CLEAN_START_V1
    assert.ok(calls.includes("event:KIT_COMMAND_DIGEST_ATTACHED"));
  } else {
    await assert.rejects(context.startAuto(), /Kit command digest could not be attached: not shown/);
    assert.equal(calls.includes("SEND"), false);
  }
}

// AGP_MISSION_TOUCHPOINT_SELFTEST_V1: a failed self-test stops the start before
// the composer is cleaned, a file is attached or anything is sent.
async function touchpointFailureStopsBeforeTheComposer() {
  const calls = [];
  let now = 1000;
  const context = Object.assign(baseContext(calls), {
    refreshStatus:async () => ({state:"READY", bridge_build_id:"b", kit_command_digest_path:"/r/digest.json",
      kit_manifest_sha:"ce455b7df8c5", mission:{mission_id:"m", state:"READY", mission_text:"x"}}),
    sendPrompt:async () => { calls.push("SEND"); },
    location:{href:"https://chatgpt.com/"},
    digest:async () => "h", lastAssistantText:() => "", chatgptGenerationActive:() => false,
    captureAssistantBaseline:() => {}, expectedStepFileVisible:() => false,
    sleep:async ms => { now += Number(ms || 0); },
    Date:{now:() => now},
    missionBootstrapPrompt:() => "BOOT", scheduleTick:() => {},
    agpMissionTouchpointCheck:() => { calls.push("CHECK"); return {ok:false, reason:"file_input_not_found", snapshot:{forms:3}}; },
    agpMissionTouchpointMessage:reason => "AGP_TOUCHPOINT_" + reason.toUpperCase() + ": Selbsttest",
    chrome:{runtime:{sendMessage:async (message) => { calls.push("MSG " + message.type); return {ok:true}; }}},
  });
  context.STATE.running = false;
  context.globalThis = context;
  context.AGP_EXTENSION_BUILD_ID = "b";
  vm.createContext(context);
  vm.runInContext(stopCode + section("  async function startAuto()", "  // AGP_START_AUTO_CLICK_PATH_077"), context);
  await assert.rejects(context.startAuto(), /AGP_TOUCHPOINT_FILE_INPUT_NOT_FOUND/);
  assert.ok(calls.filter(call => call === "CHECK").length > 1);          // retried while the page renders
  assert.equal(calls.some(call => call.startsWith("MSG ")), false);       // no clean, no attach
  assert.equal(calls.includes("SEND"), false);
  assert.ok(calls.includes("event:MISSION_TOUCHPOINT_SELFTEST"));
  assert.ok(calls.includes("event:MISSION_TOUCHPOINT_SELFTEST_FAILED"));
  assert.ok(calls.some(call => call.startsWith("/v1/file-loop/control") && call.includes("AGP_TOUCHPOINT_FILE_INPUT_NOT_FOUND")));
}

(async () => {
  await touchpointFailureStopsBeforeTheComposer();
  await bootstrapAttachesKitDigest(true);
  await bootstrapAttachesKitDigest(false);
  await rejectionStopsOnFirstError();
  await transientErrorIsRetried();
  await buildMismatchRefusesStart();
})().catch(error => { console.error(error); process.exitCode = 1; });
