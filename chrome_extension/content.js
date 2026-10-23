(() => {
  const STATE = {
    running: false,
    runGeneration: 0,
    paused: false,
    operatorControlGeneration: 0,
    processingAssistant: false,
    processingStartedAt: 0,
    processingFile: "",
    lastLiveStatusAt: 0,
    lastAssistantHash: "",
    lastPrompt: "",
    turns: 0,
    startedAt: 0,
    errors: 0,
    timer: null,
    note: "",
    mission: null,
    localAuthority: null,
    nextLocalStep: 0,
    state: "IDLE",
    connected: false,
    lastRefresh: null,
    lastEvent: "INIT",
    errorId: "",
    waitingForAssistant: false,
    assistantWaitStartedAt:0,
    lastHandshakeUrl: "",
    lastHandshakeAt: 0,
    candidateHash: "",
    candidateText: "",
    candidateStablePolls: 0,
    attachmentWaitStartedAt: 0,
    transportHoldUntil: 0,
    pendingAttachmentKey: "",
    lastAssistantObservationAt: 0,
    assistantBaselineCount: 0,
    assistantBaselineMessageIds: [],
    assistantBaselineMessageId: "",
    assistantBaselineAttachmentNames: [],
    observedAssistantMessageId: "",
    lastProcessedAssistantAttachmentKey: "",
    assistantBaselineText: "",
    k07DebugTraceEnabled: false
  };

  const AGP_K07_TRACE_STORAGE_KEY = "agpK07DebugTraceEnabled";
  chrome.storage.local.get([AGP_K07_TRACE_STORAGE_KEY]).then(saved => {
    if (typeof saved[AGP_K07_TRACE_STORAGE_KEY] === "boolean") {
      STATE.k07DebugTraceEnabled = saved[AGP_K07_TRACE_STORAGE_KEY];
      render();
    }
  }).catch(() => {});

  function setK07DebugTraceEnabled(enabled, via="runtime") {
    STATE.k07DebugTraceEnabled = Boolean(enabled);
    chrome.storage.local.set({[AGP_K07_TRACE_STORAGE_KEY]:STATE.k07DebugTraceEnabled}).catch(() => {});
    void clientEvent("K07_DEBUG_TRACE_CONTROL",{enabled:STATE.k07DebugTraceEnabled, via});
    return STATE.k07DebugTraceEnabled;
  }

  globalThis.__AGP_K07_TRACE__ = {
    enable:() => setK07DebugTraceEnabled(true, "console"),
    disable:() => setK07DebugTraceEnabled(false, "console")
  };
  let AGP_DIAGNOSTICS_OPEN = false;
  let AGP_TASK_FIRST_AUTOSTART_MISSION_ID = null;
  let AGP_TASK_FIRST_AUTOSTART_GENERATION = 0;
  let AGP_TASK_FIRST_AUTOSTART_REQUEST_KEY = "";
  let AGP_TASK_FIRST_AUTOSTART_IN_FLIGHT_KEY = "";
  let AGP_TASK_FIRST_START_REQUEST_TIMER = null;
  let AGP_TASK_FIRST_START_REQUEST_PRIMED = false;
  const AGP_TASK_FIRST_AUTOSTART_ACK_STORAGE_KEY = "agpTaskFirstAutostartAck";
  // AGP_ORPHANED_CONTENT_SCRIPT_GUARD_V1 (live 2026-10-02: after the automatic
  // extension reload the old content script in the open tab kept its timers and
  // threw "Extension context invalidated"; it could also keep polling the
  // bridge). An orphaned script stops its timers, removes its overlay and never
  // talks to the bridge again; the reloaded tab runs the new script.
  let AGP_ORPHANED = false;
  let AGP_HANDSHAKE_TIMER = null;
  function extensionAlive() {
    try { return Boolean(chrome.runtime && chrome.runtime.id); } catch (_) { return false; }
  }
  function retireIfOrphaned() {
    if (AGP_ORPHANED) return true;
    if (extensionAlive()) return false;
    AGP_ORPHANED = true;
    STATE.running = false;
    for (const timer of [STATE.timer, AGP_TASK_FIRST_START_REQUEST_TIMER, AGP_HANDSHAKE_TIMER]) {
      try { if (timer) clearInterval(timer); } catch (_) {}
    }
    try {
      const root = document.getElementById("agp-cockpit-bridge");
      if (root) root.remove();
    } catch (_) {}
    return true;
  }

  function taskStartRequestKey(missionId, generation) {
    return `${String(missionId || "")}:${Number(generation || 0)}`;
  }

  async function persistedTaskStartRequestKey() {
    try {
      const saved = await chrome.storage.local.get([AGP_TASK_FIRST_AUTOSTART_ACK_STORAGE_KEY]);
      return String(saved[AGP_TASK_FIRST_AUTOSTART_ACK_STORAGE_KEY] || "");
    } catch (_err) {
      return "";
    }
  }

  async function persistTaskStartRequestKey(key) {
    await chrome.storage.local.set({[AGP_TASK_FIRST_AUTOSTART_ACK_STORAGE_KEY]:key});
  }

  const LIMITS = {
    maxTurns: 40,
    maxRuntimeMs: 2 * 60 * 60 * 1000,
    maxErrors: 3,
    pollMs: 1000,
    stablePollsRequired: 3,
    minAssistantChars: 8
  };

  // AGP_PANEL_MODULE_V1: the overlay lives in cockpit_panel.js; content.js keeps the actions.
  const PANEL = AGP_PANEL.create({
    state:STATE,
    limits:LIMITS,
    retired:() => retireIfOrphaned(),
    clientEvent:(event, details) => clientEvent(event, details),
    diagnosticsOpen:() => AGP_DIAGNOSTICS_OPEN,
    actions:{
      start:() => startAuto(),
      stop:async () => stop("Stopped by user"),
      next:() => resumeStep(),
      refresh:() => refreshStatus(),
      toggleTrace:() => setK07DebugTraceEnabled(!STATE.k07DebugTraceEnabled, "overlay"),
    },
  });

  function render() {
    PANEL.render();
  }

  async function digest(text) {
    const bytes = new TextEncoder().encode(text || "");
    const hash = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(hash))
      .map(x => x.toString(16).padStart(2, "0")).join("");
  }

  // AGP_K07_STRUCTURED_ASSISTANT_EXTRACTION_738
  function pureJsonObjectCandidate(text) {
    const value = String(text || "").trim();
    if (!value) return "";
    try {
      const parsed = JSON.parse(value);
      return (parsed && typeof parsed === "object" && !Array.isArray(parsed)) ? value : "";
    } catch (_) { return ""; }
  }

  function assistantMessageNodes() {
    return AGP_DOM.assistantTurns();   // AGP_DOM_ADAPTER_V1
  }

  // AGP_K07_ASSISTANT_BASELINE_SET_1404
  // A long-lived ChatGPT conversation can contain older assistant attachments
  // and replies. The last message id alone is not a sufficient boundary: the
  // selector must exclude the complete pre-turn assistant set.
  function assistantBaselineIds() {
    return new Set(
      Array.isArray(STATE.assistantBaselineMessageIds)
        ? STATE.assistantBaselineMessageIds.map(String).filter(Boolean)
        : []
    );
  }

  // AGP_K07_BASELINE_BEFORE_SEND_V1: the baseline for the next turn is
  // snapshotted before the continuation is sent and applied only after the
  // send is committed, so a fast next assistant message can never be
  // absorbed into the baseline, and a failed send leaves the old one intact.
  function snapshotAssistantBaseline() {
    const nodes = assistantMessageNodes();
    return {
      ids:nodes
        .map(node => String(node.getAttribute("data-message-id") || ""))
        .filter(Boolean),
      count:nodes.length,
      lastId:lastAssistantMessageId(),
      text:normalizeObservedMessageText(lastAssistantText()),
      names:nodes.flatMap(node => {
        const text = String(node.innerText || node.textContent || "");
        return Array.from(text.matchAll(/(?:^|[\s/])([^\s/]+\.py)(?:$|[\s?#])/gim))
          .map(match => match[1]);
      })
    };
  }

  function applyAssistantBaseline(baseline) {
    STATE.assistantBaselineMessageIds = baseline.ids;
    STATE.assistantBaselineCount = baseline.count;
    STATE.assistantBaselineMessageId = baseline.lastId;
    STATE.observedAssistantMessageId = "";
    STATE.assistantBaselineText = baseline.text;
    STATE.assistantBaselineAttachmentNames = baseline.names;
  }

  function captureAssistantBaseline() {
    applyAssistantBaseline(snapshotAssistantBaseline());
  }

  // AGP_K07_IDENTITY_AWARE_ASSISTANT_SELECTION_1212
  function selectedAssistantMessageNode() {
    const nodes = assistantMessageNodes();
    if (!nodes.length) return null;
    const observedId = String(STATE.observedAssistantMessageId || "");
    if (observedId && !observedId.startsWith("request-placeholder")) {
      const observed = nodes.find(node => String(node.getAttribute("data-message-id") || "") === observedId);
      if (observed) return observed;
    }
    const baselineIds = assistantBaselineIds();
    const nonBaseline = nodes.filter(node => {
      const id = String(node.getAttribute("data-message-id") || "");
      return id && !baselineIds.has(id) && !id.startsWith("request-placeholder");
    });
    if (nonBaseline.length) return nonBaseline[nonBaseline.length - 1];
    const nonPlaceholder = nodes.filter(
      node => !String(node.getAttribute("data-message-id") || "").startsWith("request-placeholder")
    );
    return nonPlaceholder[nonPlaceholder.length - 1] || null;
  }

  function lastAssistantMessageId() {
    const assistant = selectedAssistantMessageNode();
    return assistant ? String(assistant.getAttribute("data-message-id") || "") : "";
  }

  function lastAssistantText() {
    const assistant = selectedAssistantMessageNode();
    if (!assistant) return "";
    const codeCandidates = Array.from(assistant.querySelectorAll("pre code, code"))
      .map(node => pureJsonObjectCandidate(node.textContent)).filter(Boolean);
    const uniqueCodeCandidates = [...new Set(codeCandidates)];
    if (uniqueCodeCandidates.length === 1) return uniqueCodeCandidates[0];
    const preCandidates = Array.from(assistant.querySelectorAll("pre"))
      .map(node => pureJsonObjectCandidate(node.textContent)).filter(Boolean);
    const uniquePreCandidates = [...new Set(preCandidates)];
    if (uniquePreCandidates.length === 1) return uniquePreCandidates[0];
    const rendered = String(assistant.innerText || assistant.textContent || "").trim();
    const fencedCandidates = Array.from(rendered.matchAll(/```(?:json)?\s*([\s\S]*?)```/gi))
      .map(match => pureJsonObjectCandidate(match[1])).filter(Boolean);
    const uniqueFencedCandidates = [...new Set(fencedCandidates)];
    if (uniqueFencedCandidates.length === 1) return uniqueFencedCandidates[0];
    return rendered;
  }
  // AGP_K07_LIVE_DOM_SERIALIZATION_RECOVERY_758
  function repairRenderedJsonStringEscapes(text) {
    const raw = String(text || "").trim();
    if (!raw || raw[0] !== "{" || raw[raw.length - 1] !== "}") return "";
    let out = "", inString = false, escaped = false;
    for (let i = 0; i < raw.length; i += 1) {
      const ch = raw[i];
      if (!inString) { out += ch; if (ch === '"') inString = true; continue; }
      if (escaped) { out += ch; escaped = false; continue; }
      if (ch === "\\") { out += ch; escaped = true; continue; }
      if (ch !== '"') { out += ch; continue; }
      let j = i + 1;
      while (j < raw.length && /\s/.test(raw[j])) j += 1;
      const next = raw[j] || "";
      if (next === ":" || next === "," || next === "}" || next === "]") {
        out += ch; inString = false;
      } else {
        out += '\\"';
      }
    }
    return (!inString && !escaped) ? out : "";
  }


  // AGP_INGRESS_MODULE_V1: the file ingress lives in cockpit_ingress.js; content.js keeps the loop.
  const INGRESS = AGP_INGRESS.create({
    state:STATE,
    api:(...args) => api(...args),
    clientEvent:(...args) => clientEvent(...args),
    composer:(...args) => composer(...args),
    assistantBaselineIds:(...args) => assistantBaselineIds(...args),
    selectedAssistantMessageNode:(...args) => selectedAssistantMessageNode(...args),
    lastAssistantMessageId:(...args) => lastAssistantMessageId(...args),
    reserveRemoteStep:(...args) => reserveRemoteStep(...args),
    snapshotAssistantBaseline:(...args) => snapshotAssistantBaseline(...args),
    applyAssistantBaseline:(...args) => applyAssistantBaseline(...args),
  });
  const {
    expectedStepAttachmentCandidates, expectedStepFileVisible, expectedStepTerminalCandidates,
    assistantPythonAttachmentCandidates, submitAssistantTerminalReply, submitAssistantCommandFile,
  } = INGRESS;

  // AGP_K07_ASSISTANT_WAIT_OBSERVATION_V1: bounded DOM evidence while the
  // loop waits for a remote response, so a missed response is diagnosable
  // from the bridge log instead of by hypothesis.
  async function reportAssistantWaitObservation(reason) {
    const now = Date.now();
    if (now - Number(STATE.lastAssistantObservationAt || 0) < 20000) return;
    STATE.lastAssistantObservationAt = now;
    const count = selector => {
      try { return document.querySelectorAll(selector).length; } catch (_) { return -1; }
    };
    const labelOf = el => String(
      el.getAttribute("download") || el.getAttribute("aria-label") ||
      el.getAttribute("title") || el.textContent || ""
    ).replace(/\s+/g, " ").trim();
    const pythonLabels = Array.from(document.querySelectorAll(AGP_DOM.SELECTORS.fileCardCandidate))
      .map(labelOf).filter(label => /\.py(?:$|[?#\s])/i.test(label)).slice(-5).map(label => label.slice(0, 120));
    const stopLabels = Array.from(document.querySelectorAll("button"))
      .map(button => String(button.getAttribute("aria-label") || button.getAttribute("data-testid") || ""))
      .filter(label => /stop|stopp/i.test(label)).slice(0, 5);
    const authorHeadings = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6,[role='heading']"))
      .map(el => String(el.textContent || "").trim().toLowerCase())
      .filter(text => text.length <= 40 && /gesagt|said/.test(text));
    await clientEvent("K07_ASSISTANT_WAIT_OBSERVATION", {
      reason:String(reason || ""),
      expected_step:Number(STATE.nextLocalStep || 0),
      // AGP_SELECTOR_TABLE_V1: the counted page structures are named in chatgpt_selectors.js.
      ...Object.fromEntries(Object.entries(AGP_SELECTORS.waitObservation)
        .map(([key, selector]) => [key, count(selector)])),
      author_headings:authorHeadings.slice(-6),
      baseline_ids:assistantBaselineIds().size,
      python_labels:pythonLabels,
      expected_candidates:Number(STATE.nextLocalStep || 0) > 0
        ? expectedStepAttachmentCandidates(Number(STATE.nextLocalStep || 0)).length
        : -1,
      generation_active:chatgptGenerationActive(),
      stop_like_buttons:stopLabels
    });
  }

  function assistantAttachmentKey(candidates) {
    const attachment = candidates && candidates[0];
    if (!attachment) return "";
    const messageId = lastAssistantMessageId();
    const responseText = normalizeObservedMessageText(lastAssistantText());
    const missionId = STATE.mission ? String(STATE.mission.mission_id || "") : "";
    return [missionId, STATE.runGeneration, messageId, attachment.name, attachment.href, responseText].join("\n");
  }


  function composer() {
    const resolved = typeof agpResolveComposer === "function" ? agpResolveComposer() : null;
    if (resolved) return resolved;
    return AGP_DOM.composerFallback();   // AGP_DOM_ADAPTER_V1
  }

  async function waitForComposer({timeoutMs = 20000, intervalMs = 100} = {}) {

    const deadline = Date.now() + timeoutMs;

    while (Date.now() < deadline) {

      const el = composer();

      if (el && el.isConnected) return el;

      await new Promise(resolve => setTimeout(resolve, intervalMs));

    }

    throw new Error("ChatGPT composer not ready after 20s");

  }



  async function settings() {
    const cfg = await chrome.storage.local.get({
      token:"",
      baseUrl:"http://127.0.0.1:9876"
    });
    if (cfg.baseUrl === "http://127.0.0.1:8765") {
      cfg.baseUrl = "http://127.0.0.1:9876";
      await chrome.storage.local.set({baseUrl:cfg.baseUrl});
    }
    return cfg;
  }

  async function api(path, options={}) {
    if (retireIfOrphaned()) throw new Error("AGP extension was reloaded; this page script is retired");
    const cfg = await settings();
    if (!cfg.token) throw new Error("AGP bridge token missing");

    const headers = Object.assign(
      {"X-AGP-Token":cfg.token},
      options.headers || {}
    );

    const response = await fetch(
      cfg.baseUrl + path,
      Object.assign({}, options, {headers})
    );

    const data = await response.json();

    if (!response.ok) {
      STATE.connected = false;
      STATE.errorId = data.error_id || "";
      const error = new Error(data.error || `Cockpit bridge HTTP ${response.status}`);
      // AGP_K07_FAIL_FAST_REJECTION_V1: the bridge rejects a payload that
      // violates the contract with HTTP 400 "ValueError: ...". Repeating the
      // same step cannot change that verdict (live 2026-09-30: three
      // downloads of the same file before AUTO_ERROR).
      error.bridgeRejected = response.status === 400 && /^ValueError:/.test(String(data.error || ""));
      throw error;
    }

    STATE.connected = true;
    return data;
  }

  async function reserveRemoteStep(reason, step=Number(STATE.nextLocalStep || 0)) {
    const reservedStep = Number(step || 0);
    if (reservedStep <= 0) return null;
    const reserved = await api("/v1/file-loop/reserve-step", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({step:reservedStep, reason})
    });
    if (Number(reserved.next_step || 0) > 0) {
      STATE.nextLocalStep = Number(reserved.next_step);
    }
    return reserved;
  }

  async function sendHandshake(force=false) {
    if (retireIfOrphaned()) return;
    const now = Date.now();
    const url = location.href;

    if (
      !force &&
      STATE.lastHandshakeUrl === url &&
      now - STATE.lastHandshakeAt < 60000
    ) {
      return;
    }

    try {
      const response = await api(
        "/v1/client-event",
        {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            event:"EXTENSION_HANDSHAKE",
            details:{
              version:chrome.runtime.getManifest().version,
              build_id:globalThis.AGP_EXTENSION_BUILD_ID || "",
              page_url:url,
              handled_refresh_generation:Number(
                (
                  await chrome.storage.local.get([
                    "agpLastHandledRefreshGeneration"
                  ])
                ).agpLastHandledRefreshGeneration || 0
              )
            }
          })
        }
      );

      STATE.lastHandshakeUrl = url;
      STATE.lastHandshakeAt = now;

      const requestedGeneration = Number(
        response.refresh_generation || 0
      );

      // AGP_SINGLE_REFRESH_V1: the staged build travels along; an extension that
      // already runs it does not reload itself (live 2026-10-07: it orphaned this tab).
      const expectedBuild = String(response.extension_expected_build_id || "");
      const ownBuild = String(globalThis.AGP_EXTENSION_BUILD_ID || "");
      if (requestedGeneration > 0 && !(expectedBuild && expectedBuild === ownBuild)) {
        chrome.runtime.sendMessage({
          type:"AGP_REFRESH_INTEGRATION",
          generation:requestedGeneration,
          expected_build_id:expectedBuild
        }).catch(() => {});
      }

    } catch (_) {}
  }

  function k07DebugTrace(event, details={}) {
    if (!STATE.k07DebugTraceEnabled) return;
    void clientEvent("K07_DEBUG_TRACE", {
      trace_event:String(event),
      cycle:Number(STATE.turns || 0),
      run_generation:Number(STATE.runGeneration || 0),
      ...details
    });
  }


  if (chrome.runtime && chrome.runtime.onMessage &&
      typeof chrome.runtime.onMessage.addListener === "function") {
    chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (message && message.type === "AGP_K07_NATIVE_TRACE_1165") {
      void clientEvent("K07_NATIVE_TRACE", message.payload || {});
      return false;
    }
    if (message && message.type === "AGP_PING") {
      // AGP_ORPHAN_TAB_RECOVERY_V1: the reloaded extension asks whether this
      // content script is still connected; an orphaned one never answers.
      sendResponse({ok:true, build_id:String(globalThis.AGP_EXTENSION_BUILD_ID || "")});
      return false;
    }
    if (message && message.type === "AGP_K07_SEND_PROMPT") {
      sendPrompt(String(message.prompt || ""))
        .then(() => sendResponse({ok:true, stage:"PROMPT_SENT"}))
        .catch(error => sendResponse({
          ok:false,
          stage:"PROMPT_SEND_FAILED",
          error:String(error && error.message ? error.message : error)
        }));
      return true;
    }
    return false;
    });
  }

  async function clientEvent(event, details={}) {
    try {
      await api(
        "/v1/client-event",
        {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({event, details:{
            ...details,
            mission_id:STATE.mission ? STATE.mission.mission_id : "",
            extension_version:chrome.runtime.getManifest().version,
            extension_build_id:globalThis.AGP_EXTENSION_BUILD_ID || "",
            conversation_url:location.href,
            run_generation:Number(STATE.runGeneration || 0),
            client_turn:Number(STATE.turns || 0)
          }})
        }
      );
    } catch (_) {}
  }

    // AGP_SEND_ACK_FALSE_NEGATIVE_065L_R11
  function normalizeObservedMessageText(text) {
    return String(text || "")
      .normalize("NFKC")
      .replace(/[\u200b\u200c\u200d\ufeff]/g, "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function chatgptGenerationActive() {
    return AGP_DOM.generationActive();   // AGP_DOM_ADAPTER_V1
  }

  let PENDING_SEND_TRANSPORT = null;
  // AGP_SEND_MODULE_V1: the send transport lives in cockpit_send.js; content.js keeps the pending
  // transport (read by tick, stop and startAuto) and calls sendPrompt.
  const SEND = AGP_SEND.create({
    state:STATE,
    setPendingSendTransport:value => { PENDING_SEND_TRANSPORT = value; },
    normalizeObservedMessageText:(...args) => normalizeObservedMessageText(...args),
    composer:(...args) => composer(...args),
    chatgptGenerationActive:(...args) => chatgptGenerationActive(...args),
    clientEvent:(...args) => clientEvent(...args),
    lastAssistantText:(...args) => lastAssistantText(...args),
    sleep:(...args) => sleep(...args),
    waitForComposer:(...args) => waitForComposer(...args),
    reserveRemoteStep:(...args) => reserveRemoteStep(...args),
    failureDomShape:(...args) => failureDomShape(...args),
  });
  const {SEND_TRANSPORT, sendPrompt, observedComposerText} = SEND;
  let AGP_FORMAT_REPAIR_ATTEMPTS = 0;
  const AGP_MAX_FORMAT_REPAIR_ATTEMPTS = 2;

  function formatRepairPrompt(attempt) {
    return (
      "FORMAT REPAIR ONLY. JSON syntax invalid; likely an unescaped quote or other string-escaping error. " +
      "Re-serialize the SAME intended work order without changing its semantics as exactly one JSON object and nothing else. " +
      "Preserve semantics, not broken byte-for-byte string serialization. " +
      "The result must be parseable by JSON.parse. " +
      "Escape every double quote inside JSON string values using the standard JSON backslash escape; escape backslashes as required. " +
      "Do not change the chosen executable during format repair and do not introduce a shell wrapper. " +
      "No Markdown fences, no commentary, no leading or trailing prose. " +
      `Automatic format-repair attempt ${attempt}/${AGP_MAX_FORMAT_REPAIR_ATTEMPTS}.`
    );
  }

  // Used by the native transport retry and stale-draft recovery; it was never
  // defined (ReferenceError "sleep is not defined", live 1510 and 1518).
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // AGP_DOM_SHAPE_SNAPSHOT_V1: the shape of the composer form, the last assistant turn and
  // ChatGPT's own alert notices (e.g. „Herunterladen der Datei fehlgeschlagen“) at a failure.
  function failureDomShape() {
    try {
      if (typeof agpDomShape !== "function") return {nodes:0, error:"helper missing"};
      const el = typeof agpResolveComposer === "function" ? agpResolveComposer() : composer();
      const form = el && el.closest ? el.closest("form") : null;
      const turns = assistantMessageNodes();
      const shape = agpDomShape({composer_form:form, last_assistant:turns.length ? turns[turns.length - 1] : null});
      shape.alerts = AGP_DOM.alertNotices();   // AGP_DOM_ADAPTER_V1
      return shape;
    } catch (error) {
      return {nodes:0, error:String(error).slice(0, 120)};
    }
  }

  function resetCandidate() {
    STATE.candidateHash = "";
    STATE.candidateText = "";
    STATE.candidateStablePolls = 0;
    STATE.attachmentWaitStartedAt = 0;
    STATE.pendingAttachmentKey = "";
  }

  // AGP_STRUCTURED_RESPONSE_COMPLETION_064_R1
  function parsePureJsonObject(text) {
    try {
      const data = JSON.parse(text);
      if (!data || typeof data !== "object" || Array.isArray(data)) {
        return null;
      }
      return data;
    } catch (_) {
      return null;
    }
  }

  // AGP_K07_UNIQUE_WORK_ORDER_EXTRACTION_746
  function extractSingleWorkOrderJson(text) {
    const raw = String(text || "").trim();
    if (!raw) return null;

    let directText = raw;
    let direct = parsePureJsonObject(directText);
    if (!direct) {
      const repairedText = repairRenderedJsonStringEscapes(raw);
      const repairedValue = repairedText ? parsePureJsonObject(repairedText) : null;
      if (repairedValue) { directText = repairedText; direct = repairedValue; }
    }
    const required = ["kind", "cwd", "argv", "timeout_seconds", "label"];
    const isWorkOrder = value => {
      if (!value || typeof value !== "object" || Array.isArray(value)) return false;
      if (!required.every(key => Object.prototype.hasOwnProperty.call(value, key))) return false;
      if (typeof value.kind !== "string" || !value.kind.trim()) return false;
      if (typeof value.cwd !== "string" || !value.cwd.trim()) return false;
      if (!Array.isArray(value.argv) || !value.argv.length ||
          !value.argv.every(item => typeof item === "string")) return false;
      if (!Number.isFinite(value.timeout_seconds) || value.timeout_seconds <= 0) return false;
      if (typeof value.label !== "string" || !value.label.trim()) return false;
      return true;
    };

    if (direct && isWorkOrder(direct)) {
      return {text: directText, value: direct, source: directText === raw ? "pure-json" : "rendered-json-escape-repair"};
    }

    const candidates = [];
    let depth = 0;
    let start = -1;
    let inString = false;
    let escaped = false;

    for (let i = 0; i < raw.length; i += 1) {
      const ch = raw[i];
      if (inString) {
        if (escaped) {
          escaped = false;
        } else if (ch === "\\") {
          escaped = true;
        } else if (ch === '"') {
          inString = false;
        }
        continue;
      }
      if (ch === '"') {
        inString = true;
        continue;
      }
      if (ch === "{") {
        if (depth === 0) start = i;
        depth += 1;
        continue;
      }
      if (ch === "}") {
        if (depth === 0) continue;
        depth -= 1;
        if (depth === 0 && start >= 0) {
          const candidateText = raw.slice(start, i + 1).trim();
          try {
            k07DebugTrace("JSON_PARSE_ATTEMPT",{candidate_chars:String(candidateText||"").length});
            const value = JSON.parse(candidateText);
            k07DebugTrace("JSON_PARSE_SUCCESS");
            if (isWorkOrder(value)) {
              candidates.push({text:candidateText, value});
            }
          } catch (_) {}
          start = -1;
        }
      }
    }

    const unique = [...new Set(candidates.map(item => item.text))]
      .map(textValue => candidates.find(item => item.text === textValue));
    candidates.length = unique.length;
    if (candidates.length !== 1) return null;
    return {text: unique[0].text, value: unique[0].value, source: "embedded-json"};
  }

  async function stop(reason, event="AUTO_STOPPED", operatorStop=true) {
    STATE.runGeneration += 1;
    STATE.running = false;
    STATE.transportHoldUntil = 0;
    STATE.waitingForAssistant = false;
        STATE.assistantWaitStartedAt = 0;
    STATE.processingAssistant = false;
    PENDING_SEND_TRANSPORT = null;
    AGP_FORMAT_REPAIR_ATTEMPTS = 0;
    AGP_REMOTE_FILE_REGENERATE_ATTEMPTS = 0;
    resetCandidate();
    if (STATE.timer) clearInterval(STATE.timer);
    STATE.timer = null;
    STATE.note = reason || "";
    STATE.lastEvent = event;
    // Stop must reach the durable bridge authority as well as this content
    // script. Otherwise polling can recreate the run after the overlay stops.
    try {
      if (operatorStop) await api("/v1/file-loop/control", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        // The mission records the real reason, not a generic operator stop.
        body:JSON.stringify({action:"STOP", reason:String(reason || "").slice(0, 300)})
      });
    } catch (error) {
      await clientEvent("OPERATOR_STOP_REQUEST_FAILED", {
        reason:String(error && error.message ? error.message : error)
      });
    }
    try {
      await clientEvent(event, {
        reason:STATE.note,
        run_generation:STATE.runGeneration,
        failure_class:STATE.lastTransportFailureClass || ""
      });
    } catch (error) {
      // A failed diagnostic report must never turn a completed stop into an
      // unhandled promise rejection or leave the local state ambiguous.
      STATE.lastEvent = "STOP_EVENT_REPORT_FAILED";
      STATE.note = `${reason || ""} · ${String(error)}`.trim();
    }
    // AGP_STOP_REASON_V1: show the stopped mission state instead of a stale
    // READY/RUNNING line; keep the stop reason as the visible note.
    try {
      const current = await api("/v1/status");
      if (current && current.mission) STATE.mission = current.mission;
      if (current && current.state) STATE.state = current.state;
    } catch (_) {}
    render();
  }

  function scheduleTick() {
    if (STATE.timer) clearInterval(STATE.timer);
    STATE.timer = setInterval(() => {
      void tick().catch(error => {
        // setInterval does not observe rejected promises. Keep the browser
        // console clean and preserve a durable diagnostic when an unexpected
        // error escapes the tick-level recovery path.
        STATE.processingAssistant = false;
        STATE.errors += 1;
        STATE.lastEvent = "TICK_UNHANDLED_ERROR";
        STATE.note = String(error);
        try {
          render();
        } catch (_) {}
        void clientEvent("TICK_UNHANDLED_ERROR", {
          message:String(error),
          error_count:STATE.errors
        }).catch(() => {});
      });
    }, LIMITS.pollMs);
  }

  function missionBootstrapPrompt(mission) {
    const nextStep = Number(STATE.nextLocalStep || 0);
    return [
      "AGP COCKPIT MISSION — FIRST SINGLE STEP",
      "",
      "Overall mission:",
      mission.mission_text,
      "",
      "Return exactly ONE executable Python command file as a .py attachment.",
      "The Python file is the only non-terminal command artifact for the normal K07 file loop.",
      ...(nextStep > 0 ? [
        "The local bridge is the numbering authority for this run.",
        `The next local work-order number is ${nextStep}. Use exactly ${nextStep}_...py as the attachment filename and use ${nextStep} in the embedded STEP constant and all step-scoped output names. Never reuse an older number.`,
        // AGP_TASK_REPLY_POLICY_V1: the first turn of every mission is a fresh
        // work order. A remote DONE is never offered here; earlier results in
        // the same conversation do not complete a new mission.
        `This is a new mission: earlier results in this conversation do not complete it. Only if a genuine human decision is required before any local work, attach instead exactly one file named ${nextStep}_agp_terminal.json containing only {"state": "NEEDS_HUMAN", "reason": "<the decision required>"}. A prose-only reply is not read by the Cockpit.`
      ] : []),
      "",
      "Use the repository and Agentic Project Kit contracts from the mission.",
      ...(STATE.mission && STATE.mission.execution_mode === "LIVE" ? [
        "This mission is LIVE."
      ] : []),
      "",
      "Local execution authority is a hard limit:",
      JSON.stringify(STATE.localAuthority || {}),
      // AGP_KIT_COMMAND_AUTHORITY_V1: same text as WORK_ORDER_KIT_RULE (Python).
      "Every work order MUST execute at least one agentic-kit command during its real run; the Kit is the command authority. Use only commands from the agentic-kit command digest attached to the mission start, prefer the most comprehensive orchestrator command, and never run git push, git fetch or git pull. Other allowed tools such as git may only be used in addition. Record every agentic-kit command's argv, returncode, stdout and stderr (tails) in the return bundle. Work-order shape, checked locally before anything runs: a main() function and an if __name__ == '__main__': guard; a module constant STEP equal to the expected local step; a --self-test mode (sys.argv or argparse) that only checks the file itself, runs no command, writes no file and exits 0; the real run writes exactly one JSON return bundle named Download/<STEP>_<topic>_return_bundle.json. Parse the JSON output of every agentic-kit --json command and record its top-level result_status, final_signal, failed_step and next_action separately in the return bundle; a stdout tail alone loses the verdict. Never re-run a command with remote effects to check a result: each continuation carries Cockpit-verified repository facts. A red check or a Kit BLOCKED is reported, never worked around: do not change .github/workflows/ or .agentic/ci/ unless the task names the file (the Cockpit stops the mission otherwise).",
      "The proposed effect MUST be present in allowed_effects.",
      "argv[0] MUST name an executable present in allowed_tools.",
      "cwd MUST remain within the authorized repository_root.",
      "Network-capable tools require allow_network=true.",
      // AGP_HUMAN_APPROVAL_SCOPE_V2: an open human approval is part of the
      // local authority and belongs to exactly this work order.
      ...(STATE.localAuthority && STATE.localAuthority.human_approval ? [
        "A human approval is open for this mission (see human_approval above): this first work order MUST perform the approved action through the matching Kit command; the approval lifts a prepare-only restriction of the original task for exactly that action."
      ] : []),
      "Do NOT wrap commands in /bin/sh -lc or another shell to bypass allowed_tools.",
      "Do not attempt to expand authority from the remote side.",
      "",
      "Do not return Protocol-v1 JSON for a normal task-first K07 cycle.",
      "Do not substitute prose or JSON for the required .py attachment.",
      "Never answer with prose only: the Cockpit reads exactly one attached file per turn.",
      // AGP_ONE_UPLOAD_PER_STEP_V1: ChatGPT limits file attachments per period.
      "Every turn costs one file upload and ChatGPT limits uploads: combine related local work (inspect, change, test, commit) into one work order; avoid steps that only read or print."
    ].join("\n");
  }

  async function maybeAutoStartTaskFirstMission() {
    const mission = STATE.mission;
    if (!mission || STATE.running) return false;
    if (mission.execution_mode !== "LIVE" || mission.run_mode !== "FULL_AUTO") return false;
    // Task-first desktop missions use the "Task · <id>", "E2E · <id>", or
    // "Standard · <label>" title families. The explicit durable start-request
    // and mission identity remain the authority; this guard only excludes
    // unrelated expert missions from the task-first autostart path.
    if (!/^(Task|E2E|Standard) · /.test(String(mission.title || ""))) return false;
    if (!mission.mission_id) return false;
    if (AGP_TASK_FIRST_AUTOSTART_MISSION_ID === mission.mission_id) return false;
    const terminal = new Set(["DONE","COMPLETED","FAILED","ERROR","STOPPED","CANCELLED"]);
    if (terminal.has(String(mission.state || ""))) return false;

    AGP_TASK_FIRST_AUTOSTART_MISSION_ID = mission.mission_id;
    STATE.note = "Task übernommen · Automatik startet";
    STATE.lastEvent = "TASK_FIRST_AUTOSTART";
    render();
    try {
      await startAuto();
      return true;
    } catch (err) {
      AGP_TASK_FIRST_AUTOSTART_MISSION_ID = null;
      STATE.lastEvent = "TASK_FIRST_AUTOSTART_FAILED";
      STATE.note = String(err);
      render();
      return false;
    }
  }

  // AGP_K07_UNIFIED_OPERATOR_CONTROL_1005
  async function pollOperatorControl() {
    try {
      const ctl = await api("/v1/file-loop/control");
      const generation = Number(ctl.generation || 0);
      if (!generation || generation <= STATE.operatorControlGeneration) return;
      STATE.operatorControlGeneration = generation;
      const action = String(ctl.action || "").toUpperCase();
      if (action === "PAUSE") {
        STATE.paused = true;
        STATE.runGeneration += 1;
        STATE.processingAssistant = false;
        STATE.lastEvent = "OPERATOR_PAUSED";
        STATE.note = "Automatik pausiert";
        render();
        return;
      }
      if (action === "RESUME") {
        if (!STATE.paused) return;
        STATE.paused = false;
        STATE.runGeneration += 1;
        STATE.lastEvent = "OPERATOR_RESUMED";
        STATE.note = "Automatik fortgesetzt";
        render();
        return;
      }
      if (action === "STOP") {
        STATE.paused = false;
        stop("Vom Operator gestoppt", "OPERATOR_STOPPED");
      }
    } catch (_err) {}
  }

  // AGP_DIGEST_ONCE_PER_CHAT_V1: the 33 KB command digest is attached once per
  // conversation and manifest; it is attached again after a manifest change or
  // after DIGEST_REATTACH_AFTER missions (long chats may drop old attachments).
  // The Cockpit validates every work order locally, so a forgotten command
  // costs a correction, never an unchecked execution.
  const DIGEST_MEMORY_KEY = "agpDigestByConversation";
  const DIGEST_REATTACH_AFTER = 5;
  function conversationKey() {
    const match = String(location.pathname || "").match(/\/c\/([^/?#]+)/);
    return match ? match[1] : "";
  }
  async function digestMemory() {
    try {
      const data = await chrome.storage.local.get([DIGEST_MEMORY_KEY]);
      const memory = data && data[DIGEST_MEMORY_KEY];
      return memory && typeof memory === "object" ? memory : {};
    } catch (_) {
      return null;
    }
  }
  async function digestAlreadyInChat(sha) {
    const key = conversationKey();
    if (!key || !sha) return false;
    const memory = await digestMemory();
    const entry = memory && memory[key];
    return Boolean(entry && entry.sha === sha && Number(entry.missions || 0) < DIGEST_REATTACH_AFTER);
  }
  async function rememberDigest(sha, attached) {
    const key = conversationKey();
    if (!key || !sha) return;
    const memory = await digestMemory();
    if (memory === null) return;
    const entry = memory[key] || {};
    memory[key] = attached ? {sha, missions:1} : {sha, missions:Number(entry.missions || 0) + 1};
    const keys = Object.keys(memory);
    if (keys.length > 50) delete memory[keys[0]];
    try { await chrome.storage.local.set({[DIGEST_MEMORY_KEY]:memory}); } catch (_) {}
  }

  // AGP_EXTENSION_AUTO_REFRESH_V2: the idle start-request poll (every second)
  // names the staged extension build. An outdated extension asks for its
  // refresh at once instead of waiting for the next throttled handshake.
  function checkBuildDrift(expectedBuild) {
    const expected = String(expectedBuild || "");
    const own = String(globalThis.AGP_EXTENSION_BUILD_ID || "");
    if (!expected || !own || expected === own) return false;
    const now = Date.now();
    if (now - Number(STATE.lastDriftHandshakeAt || 0) < 10000) return false;
    STATE.lastDriftHandshakeAt = now;
    void sendHandshake(true);
    return true;
  }

  async function pollExplicitTaskStartRequest() {
    if (STATE.running || retireIfOrphaned()) return;
    try {
      const req = await api("/v1/task/start-request");
      checkBuildDrift(req.extension_expected_build_id);
      const generation = Number(req.generation || 0);
      const missionId = String(req.mission_id || "");
      // An invalidated request keeps its counter internally, but is not an
      // actionable browser start signal.
      if (!generation || !missionId) return;
      const requestKey = taskStartRequestKey(missionId, generation);
      if (!AGP_TASK_FIRST_START_REQUEST_PRIMED) {
        AGP_TASK_FIRST_START_REQUEST_PRIMED = true;
        // A pending explicit desktop start request is durable authority, not
        // historical telemetry. Do not discard it merely because this
        // content script was reloaded after the request was written.
        if (!generation) {
          AGP_TASK_FIRST_AUTOSTART_GENERATION = 0;
          return;
        }
      }
      const persistedKey = await persistedTaskStartRequestKey();
      if (requestKey && requestKey === persistedKey) {
        AGP_TASK_FIRST_AUTOSTART_REQUEST_KEY = requestKey;
        await clientEvent("TASK_START_REQUEST_SUPPRESSED", {
          generation,
          request_mission_id:missionId,
          reason:"already_accepted"
        });
        return;
      }
      const sameMission = missionId === AGP_TASK_FIRST_AUTOSTART_MISSION_ID;
      if (!generation || requestKey === AGP_TASK_FIRST_AUTOSTART_REQUEST_KEY ||
          (sameMission && generation <= AGP_TASK_FIRST_AUTOSTART_GENERATION)) {
        await clientEvent("TASK_START_REQUEST_SUPPRESSED", {
          generation,
          last_generation:AGP_TASK_FIRST_AUTOSTART_GENERATION,
          reason:"generation"
        });
        return;
      }
      const status = await refreshStatus();
      if (!status.mission || status.mission.mission_id !== missionId) {
        await clientEvent("TASK_START_REQUEST_SUPPRESSED", {
          generation,
          request_mission_id:missionId,
          status_mission_id:status.mission ? status.mission.mission_id : "",
          reason:"mission_identity"
        });
        return;
      }
      await clientEvent("TASK_START_REQUEST_ACCEPTED", {
        generation,
        request_mission_id:missionId
      });
      // An explicit desktop start request is authoritative for this generation.
      // Clear the legacy per-mission latch before entering the shared start path.
      AGP_TASK_FIRST_AUTOSTART_MISSION_ID = null;
      if (AGP_TASK_FIRST_AUTOSTART_IN_FLIGHT_KEY === requestKey) return;
      AGP_TASK_FIRST_AUTOSTART_IN_FLIGHT_KEY = requestKey;
      const started = await maybeAutoStartTaskFirstMission();
      AGP_TASK_FIRST_AUTOSTART_IN_FLIGHT_KEY = "";
      if (started) {
        AGP_TASK_FIRST_AUTOSTART_REQUEST_KEY = requestKey;
        AGP_TASK_FIRST_AUTOSTART_GENERATION = generation;
        await persistTaskStartRequestKey(requestKey);
      }
    } catch (_err) {}
  }

  async function refreshStatus() {
    const result = await api("/v1/status");
    STATE.state = result.state || "IDLE";
    STATE.mission = result.mission || null;
    STATE.localAuthority = result.local_authority || null;
    STATE.nextLocalStep = Number(result.next_local_step || 0);
    // K07: status refresh is observational only. A persisted READY/FULL_AUTO task
    // must not execute merely because the desktop app/bridge reconnects.
    STATE.lastRefresh = new Date();
    // The mission line already shows state and title; a second line with the
    // same text only repeated it (live 2026-10-01/02).
    STATE.note = "";
    STATE.lastEvent = "STATUS_OK";
    render();
    return result;
  }

  // AGP_PANEL_LIVE_STATUS_V1: while a mission runs, refresh the counters and the
  // "Aktualisiert" time every few seconds. Observational only: state, note,
  // next step and every decision stay with the existing paths.
  const LIVE_STATUS_INTERVAL_MS = 5000;
  async function refreshLiveMissionStatus() {
    if (!STATE.running || !STATE.mission) return;
    const now = Date.now();
    if (now - Number(STATE.lastLiveStatusAt || 0) < LIVE_STATUS_INTERVAL_MS) return;
    STATE.lastLiveStatusAt = now;
    try {
      const result = await api("/v1/status");
      const merged = agpMergeLiveMission(STATE.mission, result && result.mission);
      if (merged) STATE.mission = merged;
      STATE.lastRefresh = new Date();
      render();
    } catch (_) {}
  }

  async function submitAssistant(text) {
    STATE.lastEvent = "TURN_SUBMIT_STARTED";
    await clientEvent("TURN_SUBMIT_STARTED_CLIENT", {
      chars:text.length
    });
    render();

    // AGP_K07_PROTOCOL_V1_CLIENT_MIGRATION_761
    const mission = STATE.mission || {};
    const workOrder = parsePureJsonObject(text);
    if (!workOrder || typeof workOrder !== "object") throw new Error("completed assistant response is not a work-order JSON object");
    const sessionId = String(mission.session_id || mission.mission_id || "").trim();
    if (!sessionId) throw new Error("Protocol-v1 execution requires an active mission/session id");
    const roundId = crypto.randomUUID();
    const actionId = crypto.randomUUID();
    const action = {
      protocol_version:1, session_id:sessionId, round_id:roundId, action_id:actionId,
      mode:"DIRECT_EXECUTION",
      target:{kind:"local_repository",repository_root:String(workOrder.cwd || "")},
      work_order:{type:"terminal_payload",content:JSON.stringify(workOrder)}
    };
    const actionFrame = ["AGP_COCKPIT_ACTION_BEGIN",JSON.stringify(action),"AGP_COCKPIT_ACTION_END"].join("\n");
    const result = await api("/v1/protocol/execute",{method:"POST",headers:{"Content-Type":"text/plain"},body:actionFrame});
    if (!["EXECUTED","REPLAYED"].includes(String(result.decision || ""))) throw new Error(`Protocol-v1 execution did not produce a deliverable result: ${JSON.stringify(result)}`);
    if (typeof result.result_frame !== "string" || !result.result_frame.trim()) throw new Error("Protocol-v1 execution returned no result_frame");
    await clientEvent("RESULT_DELIVERED",{session_id:sessionId,action_id:actionId});
    STATE.lastEvent = "TURN_SUBMIT_OK";
    return {action:"continue",prompt:result.result_frame,state:"RUNNING",note:`Protocol-v1 ${result.decision}`};
  }

  async function processCompletedAssistant(text, runGeneration) {
    // AGP_K07_COMMAND_FILE_ACTIVE_BRANCH_992
    if (!STATE.running || STATE.runGeneration !== runGeneration) return;
    const commandFiles = assistantPythonAttachmentCandidates();
    if (commandFiles.length > 0) {
      if (commandFiles.length !== 1) {
        throw new Error(`expected exactly one assistant .py attachment; observed ${commandFiles.length}`);
      }
      const commandResult = await submitAssistantCommandFile(runGeneration);
      if (!STATE.running || STATE.runGeneration !== runGeneration) return;
      if (commandResult.terminal === false && String(commandResult.state) === "CONTINUE") {
        if (Number(commandResult.next_step || 0) > 0) {
          STATE.nextLocalStep = Number(commandResult.next_step);
        }
        captureAssistantBaseline();
        await sendPrompt(String(commandResult.prompt));
        if (!STATE.running || STATE.runGeneration !== runGeneration) return;
        STATE.turns += 1;
        STATE.note = String(commandResult.human_reason || "Auftrag abgelehnt; Korrektur angefordert");
        STATE.lastEvent = "K07_WORK_ORDER_REJECTED_FOR_CORRECTION";
        STATE.waitingForAssistant = true;
        STATE.assistantWaitStartedAt = Date.now();
        resetCandidate();
        render();
        return;
      }
      const replayed = commandResult.replayed === true;
      const redelivered = replayed && commandResult.delivery_pending === true;
      const terminal = commandResult.terminal === true;
      if (commandResult.held === true) {
        // Operator PAUSE during local execution: nothing was sent. Keep the
        // attachment unconsumed so the resumed loop replays and re-delivers it.
        STATE.lastEvent = "K07_RESULT_DELIVERY_HELD";
        STATE.note = "Ergebnis wegen PAUSE zurückgehalten; wird nach Fortsetzen zugestellt";
        STATE.waitingForAssistant = true;
        STATE.assistantWaitStartedAt = 0;
        resetCandidate();
        render();
        return false;
      }
      if (terminal) {
        STATE.turns += replayed ? 0 : 1;
        STATE.lastEvent = "K07_COMMAND_FILE_TERMINAL";
        STATE.note = String(
          commandResult.human_reason || commandResult.failure_reason ||
          "command-file loop reached a terminal state"
        );
        await stop(STATE.note, String(commandResult.state || "AUTO_STOPPED"), commandResult.state !== "DONE");
        await refreshStatus();
        return;
      }
      if (replayed && !redelivered) {
        // The server returned the preserved result without sending a new
        // continuation. Mark the visible response as consumed so a polling
        // tick cannot submit the same attachment once per second.
        captureAssistantBaseline();
        STATE.lastEvent = "K07_DUPLICATE_ATTACHMENT_SUPPRESSED";
        STATE.note = "Doppelter Python-Anhang unterdrueckt; warte auf neue Antwort";
        STATE.waitingForAssistant = true;
        STATE.assistantWaitStartedAt = Date.now();
        resetCandidate();
        render();
        return;
      }
      STATE.turns += redelivered ? 0 : 1;
      const failed = String(commandResult.result_status || "").toLowerCase() === "failed" ||
        String(commandResult.result_status || "").toLowerCase() === "fail" ||
        commandResult.artifact_kind === "execution_diagnostic";
      STATE.lastEvent = failed ? "K07_COMMAND_FILE_TURN_FAILED" : "K07_COMMAND_FILE_TURN_COMPLETE";
      STATE.note = failed
        ? String(commandResult.failure_reason || "local command execution failed; recovery requested")
        : "local command completed; continuation requested";
      STATE.waitingForAssistant = true;
      STATE.assistantWaitStartedAt = Date.now();
      // The continuation was sent by the background transport; the baseline
      // snapshotted before that send has already been applied.
      resetCandidate();
      render();
      return;
    }

    const result = await submitAssistant(text);

    if (!STATE.running || STATE.runGeneration !== runGeneration) {
      return;
    }

    // AGP_TURN_ACCOUNTING_064_R1
    if (result.action !== "continue" || !result.prompt) {
      // Count a terminal assistant response only after its result has been
      // accepted. A failed prompt insertion is not a completed turn.
      STATE.turns += 1;
      render();
      await stop(
        `${result.state}: ${result.note || ""}`,
        result.state || "AUTO_STOPPED"
      );
      await refreshStatus();
      return;
    }

    captureAssistantBaseline();
    k07DebugTrace("PROMPT_SEND_REQUESTED",{chars:String(result.prompt||"").length});
    await sendPrompt(result.prompt);
    k07DebugTrace("PROMPT_SENT");
    // The turn is committed only after native transport has acknowledged the
    // next prompt. INSERT_NOT_VERIFIED must not advance the counter.
    STATE.turns += 1;
    render();

    if (!STATE.running || STATE.runGeneration !== runGeneration) {
      return;
    }

    // K07: do not claim the next turn if the RESULT is still only a draft.
    if (normalizeObservedMessageText(observedComposerText()).includes(normalizeObservedMessageText(result.prompt).slice(0, 80))) {
      throw new Error("result prompt remained in composer after send acknowledgement");
    }
    STATE.note = result.state || "";
    STATE.lastEvent = "PROMPT_SENT";
    STATE.waitingForAssistant = true;
    STATE.assistantWaitStartedAt = Date.now();
    resetCandidate();
    await clientEvent("PROMPT_SENT", {
      state:result.state
    });
    render();
  }

  function newAssistantTextAfterBaseline() {
    const nodes = assistantMessageNodes();
    if (!nodes.length) return "";

    // Ignore ChatGPT's transient request placeholder and use the same
    // identity-aware selection as attachment and text extraction.
    const newest = selectedAssistantMessageNode();
    if (!newest) return "";
    const newestMessageId = String(newest.getAttribute("data-message-id") || "");
    if (newestMessageId.startsWith("request-placeholder")) return "";

    // K07: ChatGPT may virtualize/recycle conversation DOM nodes. A new
    // assistant turn can replace an older node without increasing the
    // total assistant-node count. Prefer stable message identity over
    // node-count growth. Count remains only as a fallback when ChatGPT
    // does not expose message IDs.
    if (newestMessageId && assistantBaselineIds().has(newestMessageId)) {
      return "";
    }

    // A long-lived conversation can materialize a historical assistant node
    // after the baseline was captured.  In the file loop that node is not a
    // response: its old numbered attachment must not start the 15-second
    // attachment grace timer for the current local step.
    const expectedStep = Number(STATE.nextLocalStep || 0);
    if (expectedStep > 0) {
      const stalePythonAttachment = Array.from(
        newest.querySelectorAll(AGP_SELECTORS.fileCardCandidate)
      ).some(node => {
        const label = String(
          node.getAttribute("download") ||
          node.getAttribute("aria-label") ||
          node.getAttribute("title") ||
          node.textContent ||
          ""
        ).trim();
        const match = label.match(/(?:^|[\s/])(\d+)_[^\s/]+\.py(?:$|[?#\s])/i);
        return Boolean(match) && Number(match[1]) !== expectedStep;
      });
      if (stalePythonAttachment) return "";
    }

    const newestText = lastAssistantText();
    k07DebugTrace("ASSISTANT_OBSERVED",{chars:String(newestText||"").length,message_id:String(newestMessageId||""),node_count:nodes.length});
    const normalizedNewestText = normalizeObservedMessageText(newestText);

    if (
      !STATE.assistantBaselineMessageId &&
      !newestMessageId &&
      nodes.length <= STATE.assistantBaselineCount &&
      normalizedNewestText === STATE.assistantBaselineText
    ) {
      return "";
    }

    // ChatGPT can recycle the same assistant DOM node without exposing a
    // data-message-id. A changed visible assistant payload is then the only
    // reliable generation edge; do not suppress it merely because node count
    // stayed constant.
    STATE.observedAssistantMessageId = newestMessageId;
    return newestText;
  }

  function classifyRemoteServiceLimit(text) {
    const normalized = normalizeObservedMessageText(text).toLowerCase();
    if (!normalized) return null;
    const markers = [
      "du hast dein nutzungslimit erreicht",
      "deine work-nutzung ist vorerst aufgebraucht",
      "you have reached your usage limit",
      "you've reached your usage limit",
      "you have reached the current usage limit",
      "you've reached the current usage limit",
      "your work usage is temporarily exhausted",
    ];
    if (!markers.some(marker => normalized.includes(marker))) return null;
    const reset = normalized.match(/(?:ab|after)\s+([0-2]?\d:[0-5]\d)/i);
    return {
      code:"CHATGPT_USAGE_LIMIT",
      reset_at:reset ? reset[1] : null,
      message:reset
        ? `ChatGPT-Nutzungslimit erreicht; erneut ab ${reset[1]}`
        : "ChatGPT-Nutzungslimit erreicht; Mission geordnet gestoppt",
    };
  }

  // AGP_K07_REMOTE_FILE_REGENERATE_V1 (live 2026-10-04, release 0.1.1, step 1712): ChatGPT
  // showed the file card of the answer but could not deliver the file ("Herunterladen der Datei
  // fehlgeschlagen", by hand as well). The extension retried the same broken card until
  // maxErrors and stopped the task. Now the first failed browser download of a remote file asks
  // the remote side once for the same answer as a new file under the next step; the broken step
  // is reserved so its card can never be taken later.
  let AGP_REMOTE_FILE_REGENERATE_ATTEMPTS = 0;
  const AGP_MAX_REMOTE_FILE_REGENERATE_ATTEMPTS = 1;

  function remoteFileDownloadFailed(err) {
    const text = String(err || "");
    return text.includes("browser download timed out") || text.includes("browser download interrupted");
  }

  function remoteFileRegeneratePrompt(filename, step) {
    return (
      `FILE TRANSFER REPAIR ONLY. The file ${filename} of your last answer could not be loaded in the chat ` +
      "(the download failed on the chat side); the local side did not receive it and ran nothing. " +
      `Create the same answer again as a new file for local step ${step}: the same decision and content, ` +
      `with the step number and every step-scoped name set to ${step} ` +
      `(a terminal reply is named ${step}_agp_terminal.json). ` +
      "Do not repeat earlier work, do not change the decision, attach exactly one file."
    );
  }

  async function requestRemoteFileRegeneration(err, runGeneration) {
    if (!remoteFileDownloadFailed(err)) return false;
    if (AGP_REMOTE_FILE_REGENERATE_ATTEMPTS >= AGP_MAX_REMOTE_FILE_REGENERATE_ATTEMPTS) return false;
    if (!STATE.running || STATE.runGeneration !== runGeneration) return false;
    // AGP_K07_TERMINAL_REGENERATE_V1 (live 2026-10-07, step 1862): the lost file was the
    // terminal reply 1862_agp_terminal.json; the command-file lookup found no .py card,
    // the repair was never asked for and the finished task stopped after three timeouts.
    let candidates = assistantPythonAttachmentCandidates();
    if (!candidates.length && typeof expectedStepTerminalCandidates === "function") {
      candidates = expectedStepTerminalCandidates();
    }
    if (candidates.length !== 1) return false;
    const failedName = String(candidates[0].name || "");
    const named = Number((failedName.match(/^(\d+)_/) || [])[1] || 0);
    const failedStep = named || Number(STATE.nextLocalStep || 0);
    AGP_REMOTE_FILE_REGENERATE_ATTEMPTS += 1;
    STATE.lastProcessedAssistantAttachmentKey = assistantAttachmentKey(candidates);
    await reserveRemoteStep("unloadable-remote-attachment", failedStep);
    const nextStep = Number(STATE.nextLocalStep || 0);
    if (nextStep <= failedStep) {
      throw new Error(`K07 step ${failedStep} could not be reserved for the file regeneration`);
    }
    await clientEvent("K07_REMOTE_FILE_REGENERATION_REQUESTED", {
      filename:failedName, failed_step:failedStep, next_step:nextStep,
      attempt:AGP_REMOTE_FILE_REGENERATE_ATTEMPTS, error:String(err).slice(0, 200)
    });
    STATE.lastAssistantHash = await digest(lastAssistantText());
    captureAssistantBaseline();
    resetCandidate();
    STATE.lastEvent = "K07_REMOTE_FILE_REGENERATION_REQUESTED";
    STATE.note = `${failedName} war im Chat nicht ladbar — neu angefordert als Schritt ${nextStep}`;
    render();
    await sendPrompt(remoteFileRegeneratePrompt(failedName, nextStep));
    if (STATE.running && STATE.runGeneration === runGeneration) {
      STATE.waitingForAssistant = true;
      STATE.assistantWaitStartedAt = Date.now();
    }
    return true;
  }

  async function tick() {
    if (retireIfOrphaned()) return;
    // The catch block is a sibling lexical scope of try. Keep the generation
    // fence outside try so polling failures can never turn into a ReferenceError.
    const runGeneration = STATE.runGeneration;
    try {
    // AGP_K07_ASSISTANT_WAIT_TIMEOUT_1360 + AGP_K07_ASSISTANT_ACTIVITY_WAIT_V1
    const waitExpiry = STATE.running && STATE.waitingForAssistant && STATE.assistantWaitStartedAt > 0
      ? assistantWaitExpiry(Date.now()) : null;
    if (waitExpiry) {
      STATE.waitingForAssistant = false;
      STATE.assistantWaitStartedAt = 0;
      const awaitedStep = Number(STATE.nextLocalStep || 0);
      const message = `K07_ASSISTANT_RESPONSE_TIMEOUT after ${waitExpiry.waitedSeconds}s ` +
        `(${waitExpiry.idle ? "180s without visible activity" : "maximum wait of 900s"}) — ` +
        "Mensch muss prüfen: keine Datei " +
        (awaitedStep > 0 ? `${awaitedStep}_*.py oder ${awaitedStep}_agp_terminal.json` : "der Remote-Antwort") +
        " erschienen; eine reine Textantwort wird nicht ausgewertet.";
      STATE.lastEvent = "K07_ASSISTANT_WAIT_TIMEOUT";
      STATE.note = message;
      await clientEvent("K07_ASSISTANT_WAIT_TIMEOUT", {
        idle_timeout_ms:ASSISTANT_IDLE_TIMEOUT_MS, max_wait_ms:ASSISTANT_MAX_WAIT_MS,
        waited_ms:waitExpiry.waitedMs, idle_ms:waitExpiry.idleMs, idle:waitExpiry.idle,
        dom_mutations:waitExpiry.mutations
      });
      await stop(message, "K07_ASSISTANT_WAIT_TIMEOUT");
      return;
    }
    await pollOperatorControl();
    if (STATE.paused) return;
    if (STATE.running && STATE.transportHoldUntil) {
      if (Date.now() < STATE.transportHoldUntil) return;
      STATE.transportHoldUntil = 0;
      STATE.lastEvent = "K07_ATTACHMENT_LIMIT_RETRY";
      STATE.note = "Anhangslimit-Wartezeit vorbei — das gespeicherte Ergebnis wird erneut gesendet.";
      await clientEvent("K07_ATTACHMENT_LIMIT_RETRY", {reason:STATE.note});
      render();
    }
    await pollExplicitTaskStartRequest();
    await refreshLiveMissionStatus();
    if (!STATE.running || !STATE.waitingForAssistant) return;
      // A historical attachment can briefly be the only visible Python card
      // while ChatGPT is still materializing the new assistant response. Do
      // not submit any card until the response boundary is observable.
      // AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1: a card carrying the
      // freshly assigned step number is itself the response boundary.
      const expectedAttachmentVisible = Number(STATE.nextLocalStep || 0) > 0 &&
        expectedStepFileVisible(Number(STATE.nextLocalStep || 0));
      const newResponseText = expectedAttachmentVisible ? "" : newAssistantTextAfterBaseline();
      if (!expectedAttachmentVisible && !newResponseText) {
        await reportAssistantWaitObservation("no_response_boundary");
        return;
      }
      // ChatGPT can render the file card before the assistant has finished
      // generating the attachment. Reading it at that point produces a
      // syntactically truncated Python file (the observed 1458-1462 failure
      // pattern). The response is not complete until generation is idle.
      if (chatgptGenerationActive()) {
        STATE.lastEvent = "ASSISTANT_STREAMING";
        STATE.note = "Python-Anhang wird noch vollständig erzeugt…";
        render();
        return;
      }
      // A visible .py file card is the authoritative terminal signal for the
      // task-first K07 response. It must not wait for prose stability: the
      // file card is exactly what the local file loop consumes.
      const directCommandFiles = assistantPythonAttachmentCandidates();
      const terminalFiles = expectedStepTerminalCandidates();
      if (terminalFiles.length > 0) {
        if (directCommandFiles.length > 0 || terminalFiles.length > 1) {
          throw new Error(
            `expected exactly one remote file for step ${Number(STATE.nextLocalStep || 0)}; observed ` +
            `${directCommandFiles.length} .py and ${terminalFiles.length} terminal`
          );
        }
        if (STATE.processingAssistant) return;
        const terminalKey = assistantAttachmentKey(terminalFiles);
        if (terminalKey && terminalKey === STATE.lastProcessedAssistantAttachmentKey) return;
        if (STATE.pendingAttachmentKey !== terminalKey) {
          STATE.pendingAttachmentKey = terminalKey;
          STATE.lastEvent = "K07_ASSISTANT_ATTACHMENT_SETTLING";
          STATE.note = `Abschlussdatei erkannt, prüfe Stabilität: ${terminalFiles[0].name}`;
          render();
          return;
        }
        STATE.pendingAttachmentKey = "";
        STATE.processingAssistant = true;
        STATE.waitingForAssistant = false;
        STATE.assistantWaitStartedAt = 0;
        let terminalResult;
        try {
          terminalResult = await submitAssistantTerminalReply(terminalFiles);
          STATE.lastProcessedAssistantAttachmentKey = terminalKey;
        } finally {
          STATE.processingAssistant = false;
        }
        if (STATE.runGeneration !== runGeneration) return;
        STATE.turns += terminalResult.replayed ? 0 : 1;
        if (terminalResult.terminal === false && String(terminalResult.state) === "CONTINUE") {
          // AGP_CI_GREEN_COMPLETION_V1: DONE rejected by the local CI check;
          // send the finding and wait for the next work order of the task.
          if (Number(terminalResult.next_step || 0) > 0) {
            STATE.nextLocalStep = Number(terminalResult.next_step);
          }
          captureAssistantBaseline();
          await sendPrompt(String(terminalResult.prompt));
          if (!STATE.running || STATE.runGeneration !== runGeneration) return;
          STATE.turns += 1;
          STATE.note = String(terminalResult.human_reason || "Abschluss abgelehnt; Auftrag wird fortgesetzt");
          STATE.lastEvent = "K07_DONE_REJECTED_CONTINUED";
          STATE.waitingForAssistant = true;
          STATE.assistantWaitStartedAt = Date.now();
          resetCandidate();
          render();
          await clientEvent("K07_DONE_REJECTED_CONTINUED", {
            step:Number(terminalResult.step || 0),
            next_step:Number(terminalResult.next_step || 0),
            authority:String(terminalResult.authority || "")
          });
          return;
        }
        const terminalState = String(terminalResult.state);
        const terminalNote = terminalState === "DONE"
          ? `Fertig (Remote): ${terminalResult.human_reason}`
          : `Mensch muss eingreifen: ${terminalResult.human_reason}`;
        await stop(terminalNote, terminalState, terminalState !== "DONE");
        await refreshStatus();
        return;
      }
      if (directCommandFiles.length === 1) {
        if (STATE.processingAssistant) return;
        const attachmentKey = assistantAttachmentKey(directCommandFiles);
        if (
          attachmentKey &&
          attachmentKey === STATE.lastProcessedAssistantAttachmentKey
        ) {
          if (STATE.lastEvent !== "K07_DUPLICATE_ATTACHMENT_SUPPRESSED") {
            STATE.lastEvent = "K07_DUPLICATE_ATTACHMENT_SUPPRESSED";
            STATE.note = "Doppelter Python-Anhang unterdrueckt; warte auf neue Antwort";
            render();
            await clientEvent("K07_DUPLICATE_ATTACHMENT_SUPPRESSED", {
              filename:directCommandFiles[0].name
            });
          }
          return;
        }
        // AGP_K07_ATTACHMENT_STABILITY_V1: generation-idle selectors are
        // ChatGPT-DOM dependent and were not observed to fire live. Require
        // the same attachment identity (message id, name, href and visible
        // response text) on two consecutive idle polls before consuming it.
        if (STATE.pendingAttachmentKey !== attachmentKey) {
          STATE.pendingAttachmentKey = attachmentKey;
          STATE.lastEvent = "K07_ASSISTANT_ATTACHMENT_SETTLING";
          STATE.note = `Python-Anhang erkannt, prüfe Stabilität: ${directCommandFiles[0].name}`;
          render();
          return;
        }
        STATE.pendingAttachmentKey = "";
        STATE.processingAssistant = true;
        STATE.waitingForAssistant = false;
        STATE.assistantWaitStartedAt = 0;
        STATE.lastEvent = "K07_ASSISTANT_ATTACHMENT_OBSERVED";
        STATE.note = `Python-Anhang erkannt: ${directCommandFiles[0].name}`;
        await clientEvent("K07_ASSISTANT_ATTACHMENT_OBSERVED", {
          filename:directCommandFiles[0].name,
          href:directCommandFiles[0].href || null
        });
        // AGP_PANEL_LIVE_STATUS_V1: the panel shows how long this work order runs.
        STATE.processingStartedAt = Date.now();
        STATE.processingFile = directCommandFiles[0].name;
        render();
        try {
          const consumed = await processCompletedAssistant(lastAssistantText(), runGeneration);
          if (consumed !== false) {
            STATE.lastProcessedAssistantAttachmentKey = attachmentKey;
            AGP_REMOTE_FILE_REGENERATE_ATTEMPTS = 0;
          }
        } finally {
          STATE.processingAssistant = false;
          STATE.processingStartedAt = 0;
          STATE.processingFile = "";
        }
        return;
      }
      if (directCommandFiles.length > 1) {
        throw new Error(`expected exactly one assistant .py attachment; observed ${directCommandFiles.length}`);
      }
      const text = newAssistantTextAfterBaseline();
      if (!text) return;

      // A ChatGPT account/service limit is page-state evidence, not an
      // executable assistant response. It must never enter the K07 attachment
      // timeout or weaken the one-Python-file boundary for real work orders.
      const serviceLimit = classifyRemoteServiceLimit(text);
      if (serviceLimit) {
        STATE.attachmentWaitStartedAt = 0;
        await clientEvent("REMOTE_SERVICE_LIMIT_DETECTED", {
          code:serviceLimit.code,
          reset_at:serviceLimit.reset_at,
        });
        await stop(serviceLimit.message, "REMOTE_SERVICE_LIMIT");
        await refreshStatus();
        return;
      }

      const hash = await digest(text);
      if (text.length < LIMITS.minAssistantChars) {
        STATE.lastEvent = "ASSISTANT_STREAMING";
        STATE.note = `Antwort wächst… ${text.length} Zeichen`;
        resetCandidate();
        render();
        return;
      }

      if (hash !== STATE.candidateHash) {
        STATE.candidateHash = hash;
        STATE.candidateText = text;
        STATE.candidateStablePolls = 1;
        STATE.lastEvent = "ASSISTANT_CANDIDATE_CHANGED";
        STATE.note =
          `Antwortkandidat: ${text.length} Zeichen · Stabilität 1/${LIMITS.stablePollsRequired}`;
        await clientEvent("ASSISTANT_CANDIDATE_CHANGED", {
          chars:text.length,
          stable_polls:1
        });
        render();
        return;
      }

      STATE.candidateStablePolls += 1;
      STATE.lastEvent = "ASSISTANT_CANDIDATE_STABLE";
      STATE.note =
        `Antwortkandidat stabil ${STATE.candidateStablePolls}/${LIMITS.stablePollsRequired} · ${text.length} Zeichen`;

      await clientEvent("ASSISTANT_CANDIDATE_STABLE", {
        chars:text.length,
        stable_polls:STATE.candidateStablePolls
      });
      render();

      if (STATE.candidateStablePolls < LIMITS.stablePollsRequired) {
        return;
      }

      const completed = STATE.candidateText;
      // Historical pure-JSON completion seam retained as an explicit compatibility
      // probe; bounded extraction below is the authoritative K07 decision boundary.
      // K07 decomplexified path: one Python attachment is a complete
      // non-terminal remote response. Use the existing command-file ingress
      // before legacy Protocol-v1 JSON compatibility parsing.
      const k07CommandFiles = assistantPythonAttachmentCandidates();
      if (k07CommandFiles.length === 1) {
        const attachmentKey = assistantAttachmentKey(k07CommandFiles);
        if (
          attachmentKey &&
          attachmentKey === STATE.lastProcessedAssistantAttachmentKey
        ) {
          if (STATE.lastEvent !== "K07_DUPLICATE_ATTACHMENT_SUPPRESSED") {
            STATE.lastEvent = "K07_DUPLICATE_ATTACHMENT_SUPPRESSED";
            STATE.note = "Doppelter Python-Anhang unterdrueckt; warte auf neue Antwort";
            render();
            await clientEvent("K07_DUPLICATE_ATTACHMENT_SUPPRESSED", {
              filename:k07CommandFiles[0].name
            });
          }
          return;
        }
        STATE.attachmentWaitStartedAt = 0;
        STATE.processingAssistant = true;
        STATE.lastAssistantHash = STATE.candidateHash;
        STATE.waitingForAssistant = false;
        STATE.assistantWaitStartedAt = 0;
        STATE.lastEvent = "ASSISTANT_RESPONSE_COMPLETE";
        try {
          const consumed = await processCompletedAssistant(completed, runGeneration);
          if (consumed !== false) {
            STATE.lastProcessedAssistantAttachmentKey = attachmentKey;
            AGP_REMOTE_FILE_REGENERATE_ATTEMPTS = 0;
          }
        } finally {
          STATE.processingAssistant = false;
        }
        return;
      }
      if (k07CommandFiles.length > 1) {
        throw new Error(`expected exactly one assistant .py attachment; observed ${k07CommandFiles.length}`);
      }

      if (STATE.mission && STATE.mission.execution_mode === "LIVE" && STATE.mission.run_mode === "FULL_AUTO") {
        // ChatGPT can finish rendering the assistant text before its file
        // button is attached to the message DOM. Keep the stable candidate
        // and allow a bounded attachment-rendering window before failing.
        if (!STATE.attachmentWaitStartedAt) {
          STATE.attachmentWaitStartedAt = Date.now();
        }
        const attachmentWaitMs = Date.now() - STATE.attachmentWaitStartedAt;
        if (attachmentWaitMs < 15000) {
          STATE.lastEvent = "COMMAND_FILE_ATTACHMENT_PENDING";
          STATE.note = `Python-Anhang wird noch eingeblendet… ${Math.ceil((15000 - attachmentWaitMs) / 1000)}s`;
          await clientEvent("COMMAND_FILE_ATTACHMENT_PENDING", {
            wait_ms: attachmentWaitMs,
            timeout_ms: 15000
          });
          render();
          return;
        }
        const expectedStep = Number(STATE.nextLocalStep || 0);
        throw new Error(
          expectedStep > 0
            ? `K07_FILE_TRANSFER_ATTACHMENT_REQUIRED: expected exactly one assistant .py attachment for local step ${expectedStep}; observed 0`
            : "K07_FILE_TRANSFER_ATTACHMENT_REQUIRED: expected exactly one assistant .py attachment; observed 0"
        );
      }

      // Legacy compatibility only: non-task-first probes may still use structured text.
      const pureStructured = parsePureJsonObject(completed);
      const extracted = extractSingleWorkOrderJson(completed);
      const structured = extracted ? extracted.value : pureStructured;
      const completedForProcessing = extracted ? extracted.text : completed;

      if (!structured) {
        const graceLimit = LIMITS.stablePollsRequired + 5;
        STATE.lastEvent = "ASSISTANT_STRUCTURED_RESPONSE_PENDING";
        STATE.note =
          `Antwort stabil, aber noch kein vollständiges JSON · ${STATE.candidateStablePolls}/${graceLimit}`;
        await clientEvent("ASSISTANT_STRUCTURED_RESPONSE_PENDING", {
          chars:completed.length,
          stable_polls:STATE.candidateStablePolls,
          grace_limit:graceLimit
        });
        render();

        if (STATE.candidateStablePolls < graceLimit) {
          return;
        }

                if (AGP_FORMAT_REPAIR_ATTEMPTS < AGP_MAX_FORMAT_REPAIR_ATTEMPTS) {
          AGP_FORMAT_REPAIR_ATTEMPTS += 1;
          const repairAttempt = AGP_FORMAT_REPAIR_ATTEMPTS;
          STATE.lastEvent = "ASSISTANT_FORMAT_REPAIR";
          STATE.note = `Antwortformat wird automatisch repariert · ${repairAttempt}/${AGP_MAX_FORMAT_REPAIR_ATTEMPTS}`;
          await clientEvent("ASSISTANT_FORMAT_REPAIR", {attempt:repairAttempt, max_attempts:AGP_MAX_FORMAT_REPAIR_ATTEMPTS, chars:text.length});
          STATE.lastAssistantHash = await digest(text);
          captureAssistantBaseline();
          /* K07_POST_REPAIR_COMPLETION_RESET */
          STATE.assistantCandidateText = "";
          STATE.assistantCandidateStablePolls = 0;
          STATE.assistantStructuredGracePolls = 0;
          k07DebugTrace("FORMAT_REPAIR_STARTED",{candidate_chars:String(completed||"").length});

          STATE.assistantBaselineMessageId = lastAssistantMessageId();
    STATE.observedAssistantMessageId = "";
    STATE.assistantBaselineText = normalizeObservedMessageText(lastAssistantText());
          resetCandidate();
          render();
          const repairGeneration = STATE.runGeneration;
          await sendPrompt(formatRepairPrompt(repairAttempt));
          if (!STATE.running || STATE.runGeneration !== repairGeneration) {
            return;
          }
          STATE.waitingForAssistant = true;
    STATE.assistantWaitStartedAt = Date.now();
          return;
        }
          k07DebugTrace("FORMAT_REPAIR_EXHAUSTED",{candidate_chars:String(completed||"").length});
        throw new Error("assistant response stayed stable but is not a complete pure JSON object after automatic format repair");
      }

      AGP_FORMAT_REPAIR_ATTEMPTS = 0; // valid structured response
      if (STATE.processingAssistant) {
        return;
      }
      STATE.processingAssistant = true;
      STATE.lastAssistantHash = STATE.candidateHash;
      STATE.waitingForAssistant = false;
        STATE.assistantWaitStartedAt = 0;
      STATE.lastEvent = "ASSISTANT_RESPONSE_COMPLETE";
      STATE.note = `Vollständige strukturierte Antwort erkannt · ${completed.length} Zeichen`;

      await clientEvent("ASSISTANT_RESPONSE_COMPLETE", {
        chars:completed.length,
        stable_polls:STATE.candidateStablePolls
      });

      // AGP_LATE_ACCEPTANCE_BOUNDARY_097
      // A genuinely new completed assistant response is decisive late evidence
      // that an indeterminate send was accepted by ChatGPT.
      if (
        PENDING_SEND_TRANSPORT &&
        PENDING_SEND_TRANSPORT.state === SEND_TRANSPORT.INDETERMINATE &&
        normalizeObservedMessageText(completed) !==
          normalizeObservedMessageText(
            PENDING_SEND_TRANSPORT.beforeAssistantText || ""
          )
      ) {
        PENDING_SEND_TRANSPORT.acknowledgement = {
          confirmed:true,
          via:"late_assistant_response"
        };
        PENDING_SEND_TRANSPORT.transition(SEND_TRANSPORT.ACCEPTED_LATE, {
          via:"assistant_response_complete",
          chars:completed.length
        });
        await clientEvent("SEND_LATE_ACCEPTED", {
          chars:completed.length,
          prompt_chars:PENDING_SEND_TRANSPORT.prompt.length
        });
        PENDING_SEND_TRANSPORT = null;
      }

      render();

      resetCandidate();
      await processCompletedAssistant(completedForProcessing, runGeneration);
      if (STATE.runGeneration === runGeneration) {
        STATE.processingAssistant = false;
      }

    } catch (err) {
      STATE.processingAssistant = false;
      if (await holdForAttachmentLimit(err, runGeneration)) return;
      STATE.errors += 1;
      STATE.note = String(err);
      STATE.lastEvent = "TICK_ERROR";
      if (err && err.bridgeRejected === true) {
        await clientEvent("K07_BRIDGE_REJECTED", {message:String(err)});
        await stop(`Vom Cockpit abgelehnt: ${err.message}`, "AUTO_ERROR");
        return;
      }
      if (String(err).includes("K07") || String(err).includes("command-file")) {
        await clientEvent("K07_FILE_INGRESS_FAILED", {
          message:String(err),
          error_count:STATE.errors
        });
      }
      await clientEvent("TICK_ERROR", {
        message:String(err),
        dom_shape:typeof failureDomShape === "function" ? failureDomShape() : null   // AGP_DOM_SHAPE_SNAPSHOT_V1
      });

      try {
        if (await requestRemoteFileRegeneration(err, runGeneration)) {   // AGP_K07_REMOTE_FILE_REGENERATE_V1
          render();
          return;
        }
      } catch (regenerateError) {
        await clientEvent("K07_REMOTE_FILE_REGENERATION_FAILED", {message:String(regenerateError)});
      }

      if (STATE.errors >= LIMITS.maxErrors) {
        await stop(String(err), "AUTO_ERROR");
      } else if (STATE.runGeneration === runGeneration && STATE.running) {
        STATE.waitingForAssistant = true;
    STATE.assistantWaitStartedAt = Date.now();
        resetCandidate();
        render();
      }
    }
  }

  // AGP_K07_ASSISTANT_ACTIVITY_WAIT_V1 (live 2026-10-04, step 1689): the wait for
  // the remote answer was a fixed 180 s from the send. ChatGPT thought 58 s and ran
  // four analyses; its terminal file appeared after the deadline and a finished
  // task ended STOPPED. The stop-button probe saw no generation (German label
  // "Stoppen" without data-testid="stop-button"). Now the 180 s count from the
  // last visible activity — DOM changes in the conversation (outside this
  // overlay) or a stop-like composer button — with a hard maximum of 900 s.
  const ASSISTANT_IDLE_TIMEOUT_MS = 180000;
  const ASSISTANT_MAX_WAIT_MS = 900000;
  let ASSISTANT_ACTIVITY_OBSERVER = null;
  let ASSISTANT_ACTIVITY_TARGET = null;
  let ASSISTANT_DOM_MUTATIONS = 0;

  function ensureAssistantActivityObserver() {
    if (typeof document === "undefined" || typeof MutationObserver === "undefined") return;
    const target = document.querySelector("main") || document.body;
    if (!target || (target === ASSISTANT_ACTIVITY_TARGET && target.isConnected)) return;
    if (ASSISTANT_ACTIVITY_OBSERVER) ASSISTANT_ACTIVITY_OBSERVER.disconnect();
    ASSISTANT_ACTIVITY_TARGET = target;
    ASSISTANT_ACTIVITY_OBSERVER = new MutationObserver(records => {
      const overlay = document.getElementById("agp-cockpit-bridge");
      for (const record of records) {
        if (!overlay || !overlay.contains(record.target)) ASSISTANT_DOM_MUTATIONS += 1;
      }
    });
    ASSISTANT_ACTIVITY_OBSERVER.observe(target, {childList:true, subtree:true, characterData:true});
  }

  function stopLikeComposerButtonVisible() {
    if (typeof document === "undefined") return false;
    return AGP_DOM.stopLikeButtonVisible();   // AGP_DOM_ADAPTER_V1
  }

  function assistantWaitExpiry(now) {
    ensureAssistantActivityObserver();
    const started = Number(STATE.assistantWaitStartedAt || 0);
    const mutations = ASSISTANT_DOM_MUTATIONS;
    if (mutations !== Number(STATE.assistantSeenMutations || 0) ||
        chatgptGenerationActive() || stopLikeComposerButtonVisible()) {
      STATE.assistantSeenMutations = mutations;
      STATE.assistantLastActivityAt = now;
    }
    const lastActivity = Math.max(started, Number(STATE.assistantLastActivityAt || 0));
    const waitedMs = now - started;
    const idleMs = now - lastActivity;
    if (idleMs <= ASSISTANT_IDLE_TIMEOUT_MS && waitedMs <= ASSISTANT_MAX_WAIT_MS) return null;
    return {idle:idleMs > ASSISTANT_IDLE_TIMEOUT_MS, waitedMs, idleMs, mutations,
            waitedSeconds:Math.round(waitedMs / 1000)};
  }

  // AGP_ATTACHMENT_LIMIT_HOLD_V1 (live 2026-10-06, Kit slice GF-050 B, step 63):
  // ChatGPT refused the result upload ("Du hast das Limit für Dateianhänge
  // erreicht · Erneut versuchen 6. Okt., 19:49"); three retries within seconds
  // ended the task STOPPED and it had to be restarted from scratch. The result
  // stays local with delivery PENDING; the loop now waits until the named time
  // and re-delivers it (the visible command file is replayed, never re-run).
  const ATTACHMENT_LIMIT_PATTERN = /Limit für Dateianh|upload limit|limit for file|file attachment limit|attachment limit/i;
  const ATTACHMENT_LIMIT_FALLBACK_MS = 15 * 60 * 1000;
  const ATTACHMENT_LIMIT_MAX_MS = 24 * 60 * 60 * 1000;

  function attachmentLimitRetryAt(message, now=Date.now()) {
    const text = String(message || "");
    if (!ATTACHMENT_LIMIT_PATTERN.test(text)) return 0;
    const match = /(?:Erneut versuchen|Try again|retry)[^0-9]*(?:[^"\]]*?\s)?(\d{1,2}):(\d{2})\s*([AaPp][Mm])?/.exec(text);
    if (!match) return now + ATTACHMENT_LIMIT_FALLBACK_MS;
    let hours = Number(match[1]) % 24;
    const minutes = Number(match[2]);
    const meridiem = String(match[3] || "").toUpperCase();
    if (meridiem === "PM" && hours < 12) hours += 12;
    if (meridiem === "AM" && hours === 12) hours = 0;
    const target = new Date(now);
    target.setHours(hours, minutes, 0, 0);
    let at = target.getTime() + 60 * 1000;          // one minute after the named time
    if (at <= now) {
      // Long past means the named time lies after midnight; otherwise it has
      // just passed and the upload is tried again in a minute.
      at = now - at > 12 * 60 * 60 * 1000 ? at + 24 * 60 * 60 * 1000 : now + 60 * 1000;
    }
    return Math.min(at, now + ATTACHMENT_LIMIT_MAX_MS);
  }

  async function holdForAttachmentLimit(err, runGeneration) {
    const until = attachmentLimitRetryAt(String(err && err.message ? err.message : err));
    if (!until || !STATE.running || STATE.runGeneration !== runGeneration) return false;
    STATE.transportHoldUntil = until;
    STATE.waitingForAssistant = true;
    STATE.assistantWaitStartedAt = 0;      // no answer is awaited while holding
    STATE.pendingAttachmentKey = "";
    const clock = new Date(until).toLocaleTimeString("de-DE", {hour:"2-digit", minute:"2-digit"});
    STATE.lastEvent = "K07_ATTACHMENT_LIMIT_HOLD";
    STATE.note = `ChatGPT-Anhangslimit erreicht — das Ergebnis bleibt lokal gespeichert; erneuter Versand automatisch um ${clock}.`;
    await clientEvent("K07_ATTACHMENT_LIMIT_HOLD", {reason:STATE.note, retry_at:new Date(until).toISOString()});
    render();
    return true;
  }

  // AGP_LEGACY_PATHS_REMOVED_V1 (content.js module 4, 2026-10-08): the operator paths whose buttons
  // left the overlay on 2026-09-15 (#115) are gone — DRY mission, LIVE probes 061/065, Phase 5 bind/
  // draft/send, Phase 7 one round, Phase 8 run/pause/resume/stop — with the content scripts only they
  // loaded. Tests that slice tick() end at this marker.

  async function resumeStep() {
    const result = await api(
      "/v1/resume",
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:"{}"
      }
    );

    STATE.mission = result.mission;
    STATE.state = result.mission.state;
    STATE.note = "Nächster SINGLE_STEP freigegeben";
    STATE.lastEvent = "SINGLE_STEP_RESUMED";
    STATE.errorId = "";
    render();

    const pending = result.mission.last_prompt || "";
    if (!pending) {
      throw new Error("no persisted next-step prompt");
    }

    STATE.lastAssistantHash = await digest(lastAssistantText());
    captureAssistantBaseline();
    resetCandidate();
    await sendPrompt(pending);

    STATE.running = true;
    STATE.waitingForAssistant = true;
    STATE.assistantWaitStartedAt = Date.now();
    STATE.lastEvent = "NEXT_STEP_PROMPT_SENT";
    await clientEvent("NEXT_STEP_PROMPT_SENT", {
      chars:pending.length
    });
    render();

    scheduleTick();
  }

  async function startAuto() {
    if (STATE.paused) {
      await clientEvent("AUTO_START_IGNORED_PAUSED", {});
      return;
    }
    if (STATE.running) {
      await clientEvent("AUTO_START_IGNORED_ALREADY_RUNNING", {});
      return;
    }

    STATE.lastEvent = "AUTO_START_REQUESTED";
    STATE.errorId = "";
    render();
    await clientEvent("AUTO_START_REQUESTED", {
      page_url:location.href
    });

    const status = await refreshStatus();
    await clientEvent("AUTO_STATUS_REFRESHED", {
      state:status.state || "",
      mission_state:status.mission ? status.mission.state : "",
      mission_id:status.mission ? status.mission.mission_id : ""
    });
    if (!status.mission) {
      throw new Error("no active mission");
    }

    const mission = status.mission;

    // AGP_BUILD_IDENTITY_GATE_V1: live 2026-09-30 an extension of one build
    // ran against a bridge of another; the bridge rejected the new terminal
    // file only after the remote turn. Refuse to start instead.
    const bridgeBuild = String(status.bridge_build_id || "");
    const extensionBuild = String(globalThis.AGP_EXTENSION_BUILD_ID || "");
    if (bridgeBuild && extensionBuild && bridgeBuild !== extensionBuild) {
      const reason = `Build passt nicht: Cockpit-App ${bridgeBuild}, Extension ${extensionBuild}. ` +
        "App neu bauen oder Extension neu laden; es wurde nichts gesendet.";
      await clientEvent("BUILD_MISMATCH_START_REFUSED", {
        bridge_build_id:bridgeBuild,
        extension_build_id:extensionBuild
      });
      await stop(reason, "BUILD_MISMATCH");
      throw new Error(reason);
    }

    if (mission.state !== "READY") {
      throw new Error(
        `mission must be READY for initial start, got ${mission.state}`
      );
    }

    STATE.runGeneration += 1;
    const runGeneration = STATE.runGeneration;
    STATE.running = true;
    STATE.processingAssistant = false;
    STATE.turns = 0;
    STATE.errors = 0;
    STATE.startedAt = Date.now();
    STATE.lastPrompt = "";
    STATE.lastTransportFailureClass = "";
    PENDING_SEND_TRANSPORT = null;
    AGP_FORMAT_REPAIR_ATTEMPTS = 0;
    AGP_REMOTE_FILE_REGENERATE_ATTEMPTS = 0;
    STATE.waitingForAssistant = false;
        STATE.assistantWaitStartedAt = 0;
    STATE.lastAssistantHash = await digest(lastAssistantText());
    if (!STATE.running || STATE.runGeneration !== runGeneration) {
      return;
    }

    // Do not start a task while ChatGPT is still finishing a previous answer.
    // Otherwise that answer can cross the new baseline and be mistaken for
    // the first response of this mission.
    const generationDeadline = Date.now() + 180000;
    while (chatgptGenerationActive() && Date.now() < generationDeadline) {
      STATE.note = "Warte auf Abschluss der vorherigen ChatGPT-Antwort";
      STATE.lastEvent = "WAITING_FOR_PREVIOUS_RESPONSE";
      render();
      await sleep(250);
    }
    if (chatgptGenerationActive()) {
      throw new Error("K07_PREVIOUS_ASSISTANT_RESPONSE_STILL_ACTIVE");
    }
    captureAssistantBaseline();
    resetCandidate();

    // AGP_MISSION_TOUCHPOINT_SELFTEST_V1: every composer touchpoint must resolve
    // before anything is inserted, attached or sent; the page may still be
    // rendering, so retry briefly. The snapshot is logged on every start.
    let touchpoints = null;
    const touchpointDeadline = Date.now() + 8000;
    while (true) {
      touchpoints = typeof agpMissionTouchpointCheck === "function"
        ? agpMissionTouchpointCheck(typeof agpResolveComposer === "function" ? agpResolveComposer : undefined)
        : {ok:false, reason:"selftest_unavailable", snapshot:{}};
      if (touchpoints.ok || Date.now() >= touchpointDeadline) break;
      STATE.note = "Selbsttest: warte auf ChatGPT-Eingabefeld";
      render();
      await sleep(250);
    }
    if (!STATE.running || STATE.runGeneration !== runGeneration) {
      return;
    }
    await clientEvent("MISSION_TOUCHPOINT_SELFTEST", {
      ok:touchpoints.ok, failure:touchpoints.reason, snapshot:touchpoints.snapshot, fingerprint:touchpoints.fingerprint || "",
      ui_signature:touchpoints.ui_signature || [], fingerprint_version:touchpoints.fingerprint_version || 0});
    if (!touchpoints.ok) {
      const message = typeof agpMissionTouchpointMessage === "function"
        ? agpMissionTouchpointMessage(touchpoints.reason)
        : "AGP_TOUCHPOINT_SELFTEST_UNAVAILABLE: Selbsttest vor dem Start nicht geladen; Erweiterung neu laden. Es wurde nichts gesendet.";
      // Recorded by the bridge (browser_transport_event) without blocking the
      // transport: nothing was inserted, attached or sent.
      await stop(message, "MISSION_TOUCHPOINT_SELFTEST_FAILED");
      // Like a failed bootstrap send: the explicit start request stays retryable.
      throw new Error(message);
    }

    // AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1: the expected step must be
    // unused in this conversation before it is issued, otherwise an older
    // card with that number (e.g. from a timed-out mission) would be taken
    // as this mission's response. Reserve every visible one and advance.
    for (let guard = 0; guard < 20; guard += 1) {
      const visibleStep = Number(STATE.nextLocalStep || 0);
      if (visibleStep <= 0 || !expectedStepFileVisible(visibleStep)) break;
      await reserveRemoteStep("visible-unmaterialized-remote-attachment", visibleStep);
      if (Number(STATE.nextLocalStep || 0) <= visibleStep) {
        throw new Error(`K07 expected step ${visibleStep} is already visible and could not be reserved`);
      }
    }

    const bootstrap = missionBootstrapPrompt(mission);

    STATE.lastEvent = "MISSION_BOOTSTRAP_PREPARED";
    await clientEvent("MISSION_BOOTSTRAP_PREPARED", {
      mission_chars:(mission.mission_text || "").length,
      bootstrap_chars:bootstrap.length
    });
    render();

    try {
      // AGP_KIT_COMMAND_CATALOG_V1: the remote side cannot read the local
      // command manifest; its digest travels with the mission start.
      const digestPath = String(status.kit_command_digest_path || "");
      const manifestSha = String(status.kit_manifest_sha || "");
      let bootstrapText = bootstrap;
      // AGP_DIGEST_REMEMBERED_AFTER_SEND_V1 (live 2026-10-02): the digest
      // counts as "in this chat" only after the message carrying it was
      // sent; a failed send must not turn the next start into a reuse.
      let digestAttached = null;
      // AGP_COMPOSER_CLEAN_START_V1: start from an empty composer.
      const cleaned = await chrome.runtime.sendMessage({type:"AGP_K07_CLEAN_COMPOSER"});
      if (!cleaned || cleaned.ok !== true) {
        throw new Error(String(cleaned && cleaned.reason || "ChatGPT-Eingabefeld nicht leer"));
      }
      if (cleaned.stage === "COMPOSER_CLEANED" || (cleaned.unrecognised || []).length) {
        await clientEvent("COMPOSER_LEFTOVERS_REMOVED", {
          cleared_text:Boolean(cleaned.cleared_text), removed_files:cleaned.removed_files || [],
          unrecognised:cleaned.unrecognised || []});
      }
      if (digestPath && await digestAlreadyInChat(manifestSha)) {
        // AGP_DIGEST_ONCE_PER_CHAT_V1: same manifest, same chat, recent enough.
        bootstrapText = bootstrap + "\n\nThe agentic-kit command digest for manifest " + manifestSha +
          " was attached earlier in this conversation and is unchanged; it remains the command authority for this mission.";
        digestAttached = false;
        await clientEvent("KIT_COMMAND_DIGEST_REUSED", {manifest_sha:manifestSha});
      } else if (digestPath) {
        const attached = await chrome.runtime.sendMessage({type:"AGP_K07_ATTACH_FILES", files:[digestPath]});
        if (!attached || attached.ok !== true) {
          throw new Error("Kit command digest could not be attached: " + String(attached && attached.error || "unknown"));
        }
        digestAttached = true;
        await clientEvent("KIT_COMMAND_DIGEST_ATTACHED", {
          manifest_sha:manifestSha,
          evidence:String(attached.evidence || "")
        });
      }
      await sendPrompt(bootstrapText);
      if (digestAttached !== null) await rememberDigest(manifestSha, digestAttached);
    } catch (err) {
      if (STATE.runGeneration === runGeneration) {
        await stop(String(err), "MISSION_BOOTSTRAP_SEND_FAILED");
      }
      // Keep the durable explicit start request retryable. A stopped run is
      // not a successfully accepted request.
      throw err;
    }

    if (!STATE.running || STATE.runGeneration !== runGeneration) {
      return;
    }
    STATE.waitingForAssistant = true;
    STATE.assistantWaitStartedAt = Date.now();
    STATE.lastEvent = "MISSION_BOOTSTRAP_SENT";
    STATE.note = "Warte auf vollständige neue ChatGPT-Antwort";
    await clientEvent("MISSION_BOOTSTRAP_SENT", {
      chars:bootstrap.length
    });
    render();

    scheduleTick();
  }

  // AGP_START_AUTO_CLICK_PATH_077

  render();

  sendHandshake();
  AGP_HANDSHAKE_TIMER = setInterval(sendHandshake, 15000);

  refreshStatus().catch(err => {
    STATE.note = String(err);
    STATE.lastEvent = "INITIAL_STATUS_ERROR";
    render();
  });

  // K07: passive READY state still observes explicit desktop start requests.
  // The first observed generation is only baselined by the poll function.
  if (!AGP_TASK_FIRST_START_REQUEST_TIMER) {
    AGP_TASK_FIRST_START_REQUEST_TIMER = setInterval(() => {
      void pollExplicitTaskStartRequest();
    }, LIMITS.pollMs);
  }

})();
