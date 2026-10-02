// AGP_K07_TERMINAL_REPLY_FILE_V1: drives the actual content-script tick with a
// visible <step>_agp_terminal.json card and a stubbed bridge.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync("chrome_extension/content.js", "utf8");
const section = (start, end) => source.slice(source.indexOf(start), source.indexOf(end, source.indexOf(start)));
const code = section("  async function submitAssistantTerminalReply(", "  async function submitAssistantCommandFile(")
  + section("  async function stop(", "  function scheduleTick()")
  + section("  async function tick()", "  const LIVE_PROBE");

async function scenario({bridgeState="NEEDS_HUMAN", python=0, terminal=1}={}) {
  const calls = [];
  const sent = [];
  const events = [];
  const card = {name:"1480_agp_terminal.json", href:"", isButton:true};
  const context = {
    STATE: {running:true, paused:false, runGeneration:1, turns:3, nextLocalStep:1480,
            waitingForAssistant:true, assistantWaitStartedAt:Date.now(), processingAssistant:false,
            pendingAttachmentKey:"", lastProcessedAssistantAttachmentKey:""},
    PENDING_SEND_TRANSPORT:null, AGP_FORMAT_REPAIR_ATTEMPTS:0,
    LIMITS:{minAssistantChars:1, stablePollsRequired:2},
    pollOperatorControl:async () => {}, pollExplicitTaskStartRequest:async () => {},
    expectedStepFileVisible:() => true, chatgptGenerationActive:() => false,
    newAssistantTextAfterBaseline:() => "", reportAssistantWaitObservation:async () => {},
    assistantPythonAttachmentCandidates:() => Array.from({length:python}, () => ({name:"1480_x.py"})),
    expectedStepTerminalCandidates:() => Array.from({length:terminal}, () => card),
    assistantAttachmentKey:c => c[0].name,
    fetchSingleAssistantPythonAttachment:async candidates => {
      assert.deepEqual(candidates, [card]);
      return {filename:card.name, content:'{"state":"NEEDS_HUMAN","reason":"credentials"}', download_sha256:"abc"};
    },
    clientEvent:async (name, details) => { events.push([name, details]); },
    resetCandidate:() => {}, render:() => {}, refreshStatus:async () => { calls.push("refresh"); },
    captureAssistantBaseline:() => { calls.push("baseline"); },
    sendPrompt:async prompt => { sent.push(prompt); },
    clearInterval:() => {}, forgetBrowserDownload:async () => {}, digestAlreadyInChat:async () => false, rememberDigest:async () => {},
    api:async (path, options) => {
      calls.push(path);
      if (path === "/v1/file-loop/terminal") {
        const body = JSON.parse(options.body);
        assert.equal(body.filename, "1480_agp_terminal.json");
        assert.equal(body.download_sha256, "abc");
        if (bridgeState === "CONTINUE") {
          // AGP_CI_GREEN_COMPLETION_V1: DONE rejected by the local CI check
          return {state:"CONTINUE", remote_state:"DONE", terminal:false, step:1480, next_step:1481,
                  prompt:"AGP COCKPIT — DONE NOT ACCEPTED", human_reason:"Abschluss abgelehnt — CI red",
                  authority:"ci-gate", replayed:false};
        }
        return {state:bridgeState, remote_state:"DONE", terminal:true, human_reason:"credentials",
                authority:"remote-declared", replayed:false};
      }
      return {};
    },
  };
  vm.createContext(context);
  vm.runInContext(code, context);
  if (python > 0 || terminal > 1) {
    await context.tick();
    assert.equal(calls.includes("/v1/file-loop/terminal"), false);
    return;
  }
  await context.tick();  // first poll: settling only
  assert.equal(context.STATE.lastEvent, "K07_ASSISTANT_ATTACHMENT_SETTLING");
  assert.equal(calls.length, 0);
  await context.tick();  // second identical poll: consumed
  if (bridgeState === "CONTINUE") {
    assert.equal(context.STATE.running, true);
    assert.deepEqual(sent, ["AGP COCKPIT — DONE NOT ACCEPTED"]);
    assert.equal(context.STATE.nextLocalStep, 1481);
    assert.equal(context.STATE.waitingForAssistant, true);
    assert.equal(context.STATE.lastEvent, "K07_DONE_REJECTED_CONTINUED");
    assert.deepEqual(calls, ["/v1/file-loop/terminal", "baseline"]);
    assert.ok(!calls.includes("/v1/file-loop/control"));
    return;
  }
  assert.equal(context.STATE.running, false);
  assert.equal(context.STATE.turns, 4);
  assert.equal(context.STATE.lastEvent, bridgeState);
  assert.match(context.STATE.note, bridgeState === "DONE" ? /^Fertig \(Remote\)/ : /^Mensch muss eingreifen/);
  const expected = bridgeState === "DONE"
    ? ["/v1/file-loop/terminal", "/v1/status", "refresh"]
    : ["/v1/file-loop/terminal", "/v1/file-loop/control", "/v1/status", "refresh"];
  assert.deepEqual(calls, expected);
  assert.ok(events.some(([name]) => name === "K07_TERMINAL_REPLY_OBSERVED"));
}

(async () => {
  await scenario();
  await scenario({bridgeState:"DONE"});
  await scenario({bridgeState:"CONTINUE"});
  await scenario({python:1});     // ambiguous: .py and terminal for one step
  await scenario({terminal:2});
})().catch(error => { console.error(error); process.exitCode = 1; });
