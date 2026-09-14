(() => {
  const STATE = {
    running: false,
    lastAssistantHash: "",
    lastPrompt: "",
    turns: 0,
    startedAt: 0,
    errors: 0,
    timer: null,
    note: "",
    mission: null,
    state: "IDLE",
    connected: false,
    lastRefresh: null,
    lastEvent: "INIT",
    errorId: "",
    waitingForAssistant: false,
    lastHandshakeUrl: "",
    lastHandshakeAt: 0,
    candidateHash: "",
    candidateText: "",
    candidateStablePolls: 0,
    assistantBaselineCount: 0
  };

  let AGP_DIAGNOSTICS_OPEN = false;
  let AGP_TASK_FIRST_AUTOSTART_MISSION_ID = null;
  let AGP_TASK_FIRST_AUTOSTART_GENERATION = 0;
  let AGP_TASK_FIRST_START_REQUEST_TIMER = null;
  let AGP_TASK_FIRST_START_REQUEST_PRIMED = false;

  const LIMITS = {
    maxTurns: 40,
    maxRuntimeMs: 2 * 60 * 60 * 1000,
    maxErrors: 3,
    pollMs: 1000,
    stablePollsRequired: 3,
    minAssistantChars: 8
  };

  const STYLE = `
    #agp-cockpit-bridge {
      position:fixed;right:18px;bottom:88px;z-index:2147483647;
      width:620px;max-width:calc(100vw - 36px);
      background:linear-gradient(180deg,#18202a,#111820);
      color:#eef4f8;border:1px solid #3b82a9;border-radius:12px;
      box-shadow:0 10px 28px rgba(0,0,0,.34);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      overflow:hidden;
    }
    #agp-cockpit-bridge * {box-sizing:border-box}
    #agp-cockpit-bridge .agp-head {
      display:flex;align-items:center;gap:8px;padding:10px 12px;
      border-bottom:1px solid rgba(255,255,255,.10);font-weight:700
    }
    /* AGP_OVERLAY_DRAG_MINIMIZE_063S2 */
    #agp-cockpit-bridge .agp-head {
      cursor:move;user-select:none
    }
    #agp-cockpit-bridge .agp-minimize {
      background:#263543;padding:2px 8px;min-height:24px;font-size:13px;
      line-height:1;border-radius:6px
    }
    #agp-cockpit-bridge.agp-minimized .agp-actions,
    #agp-cockpit-bridge.agp-minimized .agp-body,
    #agp-cockpit-bridge.agp-minimized .agp-debug {
      display:none
    }
    #agp-cockpit-bridge.agp-minimized .agp-head {
      border-bottom:0
    }
    #agp-cockpit-bridge .agp-grow {flex:1}
    #agp-cockpit-bridge .agp-dot {
      width:9px;height:9px;border-radius:50%;display:inline-block;background:#7c8791
    }
    #agp-cockpit-bridge .agp-dot.on {
      background:#35c759;box-shadow:0 0 8px rgba(53,199,89,.55)
    }
    /* AGP_BROWSER_BUSY_INDICATOR_064_R2 */
    #agp-cockpit-bridge .agp-busy {
      display:inline-flex;align-items:center;gap:6px;
      color:#8fdcff;font-size:11px;font-weight:700;white-space:nowrap
    }
    #agp-cockpit-bridge .agp-spinner {
      width:12px;height:12px;border-radius:50%;
      border:2px solid rgba(143,220,255,.30);
      border-top-color:#8fdcff;
      animation:agp-cockpit-spin .8s linear infinite
    }
    @keyframes agp-cockpit-spin {
      to { transform:rotate(360deg) }
    }

    #agp-cockpit-bridge .agp-pill {
      border:1px solid rgba(255,255,255,.22);border-radius:7px;
      padding:3px 8px;font-size:11px;font-weight:700;background:#222d38;color:#dbe7ee
    }
    #agp-cockpit-bridge .agp-pill.mode {
      border-color:#2d7fc0;color:#73c4ff;background:#12314b
    }
    #agp-cockpit-bridge .agp-pill.run {
      border-color:#8046bd;color:#d6a4ff;background:#35194d
    }
    #agp-cockpit-bridge .agp-actions {
      display:grid;grid-template-columns:repeat(6,1fr);gap:8px;
      padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.10)
    }
    #agp-cockpit-bridge button {
      appearance:none;border:1px solid rgba(255,255,255,.18);border-radius:7px;
      padding:8px 7px;color:white;font-weight:700;cursor:pointer;min-height:38px
    }
    #agp-cockpit-bridge button:hover {filter:brightness(1.12)}
    #agp-cockpit-bridge .start {background:#238636}
    #agp-cockpit-bridge .stop {background:#b85d09}
    #agp-cockpit-bridge .mission {background:#145f91}
    #agp-cockpit-bridge .liveprobe {background:#8a2432}
    #agp-cockpit-bridge .next {background:#6531a8}
    #agp-cockpit-bridge .status {background:#236980}
    #agp-cockpit-bridge .agp-body {
      display:grid;grid-template-columns:145px 1fr 155px;min-height:90px
    }
    #agp-cockpit-bridge .agp-cell {
      padding:10px 12px;border-right:1px solid rgba(255,255,255,.08)
    }
    #agp-cockpit-bridge .agp-cell:last-child {border-right:0}
    #agp-cockpit-bridge .agp-label {color:#9fb0bc;font-size:11px;margin-bottom:4px}
    #agp-cockpit-bridge .agp-big {font-size:18px;font-weight:800}
    #agp-cockpit-bridge .agp-note {
      font-size:12px;line-height:1.35;color:#dbe7ee;overflow-wrap:anywhere
    }
    #agp-cockpit-bridge .agp-progress {
      margin-top:6px;height:5px;border-radius:999px;background:#303a43;overflow:hidden
    }
    #agp-cockpit-bridge .agp-progress > div {
      height:100%;background:#35c759;width:0%;transition:width .2s ease
    }
    #agp-cockpit-bridge .agp-debug {
      padding:6px 12px;border-top:1px solid rgba(255,255,255,.08);
      color:#9fc8dc;font-size:11px
    }
    #agp-cockpit-bridge .agp-error {color:#ff9a9a;font-weight:700}
  `;

  function ensureStyle() {
    if (document.getElementById("agp-cockpit-style")) return;
    const style = document.createElement("style");
    style.id = "agp-cockpit-style";
    style.textContent = STYLE;
    document.documentElement.appendChild(style);
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
    return Array.from(document.querySelectorAll('[data-message-author-role="assistant"]'));
  }

  function lastAssistantText() {
    const nodes = assistantMessageNodes();
    if (!nodes.length) return "";
    const assistant = nodes[nodes.length - 1];
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

  function composer() {
    return (
      document.querySelector('#prompt-textarea') ||
      document.querySelector('textarea') ||
      document.querySelector('[contenteditable="true"]')
    );
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


  function isUsableSendControl(el) {
    if (!el || !el.isConnected || el.disabled) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function sendButton(anchor=null) {
    const selectors = [
      'button[data-testid="send-button"]',
      'button[aria-label*="Send"]',
      'button[aria-label*="Senden"]',
      'button[type="submit"]'
    ];

    const form = anchor && anchor.closest ? anchor.closest("form") : null;
    if (form) {
      for (const selector of selectors) {
        const candidate = form.querySelector(selector);
        if (isUsableSendControl(candidate)) return candidate;
      }
    }

    for (const selector of selectors) {
      const candidates = Array.from(document.querySelectorAll(selector));
      const candidate = candidates.find(isUsableSendControl);
      if (candidate) return candidate;
    }

    return null;
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
      throw new Error(data.error || `Cockpit bridge HTTP ${response.status}`);
    }

    STATE.connected = true;
    return data;
  }

  async function sendHandshake(force=false) {
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

      if (requestedGeneration > 0) {
        chrome.runtime.sendMessage({
          type:"AGP_REFRESH_INTEGRATION",
          generation:requestedGeneration
        }).catch(() => {});
      }

    } catch (_) {}
  }

  async function clientEvent(event, details={}) {
    try {
      await api(
        "/v1/client-event",
        {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({event, details:{...details, mission_id:STATE.mission ? STATE.mission.mission_id : ""}})
        }
      );
    } catch (_) {}
  }

  function setComposerText(el, text) {
    if (!el) throw new Error("ChatGPT composer not found");

    if (el instanceof HTMLTextAreaElement) {
      const setter = Object.getOwnPropertyDescriptor(
        HTMLTextAreaElement.prototype,
        "value"
      ).set;
      setter.call(el, text);
      el.dispatchEvent(new Event("input", {bubbles:true}));
      return;
    }

    el.focus();
    el.textContent = text;
    el.dispatchEvent(
      new InputEvent("input", {
        bubbles:true,
        inputType:"insertText",
        data:text
      })
    );
  }

  function visibleUserMessages() {
    return agpNativeMessageSnapshot().messages.map(message => message.text).filter(Boolean);
  }

    // AGP_SEND_ACK_FALSE_NEGATIVE_065L_R11
  function normalizeObservedMessageText(text) {
    return String(text || "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }


  // AGP_FOLLOWUP_SEND_TARGET_DECISIVE_ACK_066_D4
  // AGP_MULTI_SIGNAL_SEND_ACCEPTANCE_066_D3
  function observedComposerText() {
    const el = composer();
    if (!el) return "";
    if (el instanceof HTMLTextAreaElement) {
      return normalizeObservedMessageText(el.value || "");
    }
    return normalizeObservedMessageText(
      el.innerText || el.textContent || el.getAttribute("data-lexical-text") || ""
    );
  }

  function chatgptGenerationActive() {
    const selectors = [
      'button[data-testid="stop-button"]',
      'button[aria-label*="Stop generating"]',
      'button[aria-label*="Stop response"]',
      'button[aria-label*="Generierung stoppen"]',
      'button[aria-label*="Antwort stoppen"]',
      '[data-is-streaming="true"]',
      '[data-testid="stop-generating-button"]'
    ];
    return selectors.some(selector => {
      const el = document.querySelector(selector);
      return Boolean(el && !el.disabled);
    });
  }

  async function waitForSentUserMessage(
    prompt,
    beforeMessages,
    beforeAssistantText="",
    beforeComposerText="",
    beforeGenerationActive=false
  ) {
    const beforeCount = beforeMessages.length;
    const expected = normalizeObservedMessageText(prompt);
    const assistantBefore = normalizeObservedMessageText(beforeAssistantText);
    const composerBefore = normalizeObservedMessageText(beforeComposerText);
    let provisionalComposerEvidence = "";
    let generationStartedObserved = false;

    for (let i = 0; i < 60; i += 1) {
      await new Promise(resolve => setTimeout(resolve, 250));

      const after = visibleUserMessages();
      if (after.length > beforeCount) {
        const newest = normalizeObservedMessageText(after[after.length - 1]);
        if (newest === expected) {
          return {confirmed:true, via:"user_message"};
        }
      }

      // Composer mutation alone is not decisive. React/editor re-renders can clear
      // or replace the draft even when no user message was actually submitted.
      const composerNow = observedComposerText();
      if (composerBefore && composerNow !== composerBefore) {
        provisionalComposerEvidence = !composerNow
          ? "composer_cleared"
          : "composer_changed";
      }

      const generationNow = chatgptGenerationActive();
      if (
        generationNow &&
        !beforeGenerationActive &&
        !generationStartedObserved
      ) {
        generationStartedObserved = true;
        await clientEvent("SEND_GENERATION_STARTED_OBSERVED", {
          authoritative_acceptance:false
        });
      }

      const assistantNow = normalizeObservedMessageText(lastAssistantText());
      if (assistantNow && assistantNow !== assistantBefore) {
        await clientEvent("SEND_ASSISTANT_ACTIVITY_OBSERVED", {
          authoritative_acceptance:false
        });
      }
    }

    return {
      confirmed:false,
      via:"timeout",
      provisional:provisionalComposerEvidence,
      generation_started_observed:generationStartedObserved
    };
  }

    // AGP_BROWSER_SENDER_TRANSPORT_STATE_MACHINE_092
  const SEND_TRANSPORT = Object.freeze({
    IDLE:"IDLE",
    DRAFT_WRITTEN:"DRAFT_WRITTEN",
    NATIVE_INPUT_REQUESTED:"NATIVE_INPUT_REQUESTED",
    NATIVE_SUBMIT_DISPATCHED:"NATIVE_SUBMIT_DISPATCHED",
    SUBMIT_ATTEMPTED:"SUBMIT_ATTEMPTED",
    WAITING_FOR_ACCEPTANCE:"WAITING_FOR_ACCEPTANCE",
    ACCEPTED:"ACCEPTED",
    ACCEPTED_LATE:"ACCEPTED_LATE",
    SAFE_RETRY_ELIGIBLE:"SAFE_RETRY_ELIGIBLE",
    RETRY_ATTEMPTED:"RETRY_ATTEMPTED",
    INDETERMINATE:"INDETERMINATE",
    FAILED_CONFIRMATION:"FAILED_CONFIRMATION"
  });

  let PENDING_SEND_TRANSPORT = null;
  const AGP_ALLOW_DEGRADED_DOM_FALLBACK = false;

  function createSendTransport(prompt) {
    return {
      state:SEND_TRANSPORT.IDLE,
      prompt,
      beforeAssistantText:"",
      retryCount:0,
      acknowledgement:null,
      transition(next, details={}) {
        this.state = next;
        STATE.lastEvent = `SEND_TRANSPORT_${next}`;
        clientEvent("SEND_TRANSPORT_STATE", {
          state:next,
          retry_count:this.retryCount,
          ...details
        }).catch(() => {});
      }
    };
  }
  let AGP_FORMAT_REPAIR_ATTEMPTS = 0;
  const AGP_MAX_FORMAT_REPAIR_ATTEMPTS = 2;

  function formatRepairPrompt(attempt) {
    return (
      "FORMAT REPAIR ONLY. JSON syntax invalid; likely an unescaped quote or other string-escaping error. " +
      "Re-serialize the SAME intended work order without changing its semantics as exactly one JSON object and nothing else. " +
      "Preserve semantics, not broken byte-for-byte string serialization. " +
      "The result must be parseable by JSON.parse. " +
      "Escape every double quote inside JSON string values using the standard JSON backslash escape; escape backslashes as required. " +
      "For shell work orders such as /bin/sh -lc, inner double quotes in argv strings must use the standard JSON backslash escape. " +
      "No Markdown fences, no commentary, no leading or trailing prose. " +
      `Automatic format-repair attempt ${attempt}/${AGP_MAX_FORMAT_REPAIR_ATTEMPTS}.`
    );
  }


async function sendPromptNative(prompt) {
    const transport = createSendTransport(prompt);
    if (prompt === STATE.lastPrompt) {
      throw new Error("identical prompt loop detected");
    }

    const nativeTransport = window.AGPBrowserNativeTransport;
    if (
      !nativeTransport ||
      typeof nativeTransport.available !== "function" ||
      typeof nativeTransport.submit !== "function" ||
      !nativeTransport.available()
    ) {
      throw new Error("browser-native transport unavailable");
    }

    const beforeMessages = visibleUserMessages();
    const beforeAssistantText = lastAssistantText();
    transport.beforeAssistantText = beforeAssistantText;

    await waitForComposer();

    const stagedComposerText = normalizeObservedMessageText(
      observedComposerText()
    );
    const expectedPromptText = normalizeObservedMessageText(prompt);

    if (stagedComposerText) {
      if (stagedComposerText !== expectedPromptText) {
        throw new Error(
          "browser-native transport found non-empty foreign composer content; refusing to overwrite"
        );
      }

      const staleOwnedComposer = composer();
      if (!staleOwnedComposer) {
        throw new Error(
          "browser-native transport stale-owned composer disappeared during recovery"
        );
      }

      setComposerText(staleOwnedComposer, "");

      const cleanupDeadline = Date.now() + 2000;
      while (
        normalizeObservedMessageText(observedComposerText()) &&
        Date.now() < cleanupDeadline
      ) {
        await sleep(50);
      }

      if (normalizeObservedMessageText(observedComposerText())) {
        throw new Error(
          "browser-native transport could not clear exact stale Cockpit-owned draft"
        );
      }

      await clientEvent("NATIVE_STALE_OWNED_COMPOSER_RECOVERED", {
        chars:prompt.length,
        ownership:"exact_current_prompt"
      });
    }

    const beforeGenerationActive = chatgptGenerationActive();
    STATE.lastPrompt = prompt;
    PENDING_SEND_TRANSPORT = transport;

    transport.transition(SEND_TRANSPORT.NATIVE_INPUT_REQUESTED, {
      chars:prompt.length
    });
    await clientEvent("NATIVE_TRANSPORT_REQUESTED", {
      chars:prompt.length
    });

    const nativeAck = await nativeTransport.submit(prompt);

    transport.transition(SEND_TRANSPORT.NATIVE_SUBMIT_DISPATCHED, {
      request_id:String(nativeAck.request_id || ""),
      tab_id:Number(nativeAck.tab_id || 0),
      native_stage:String(nativeAck.stage || "")
    });
    await clientEvent("NATIVE_TRANSPORT_SUBMIT_DISPATCHED", {
      request_id:String(nativeAck.request_id || ""),
      tab_id:Number(nativeAck.tab_id || 0),
      native_stage:String(nativeAck.stage || "")
    });

    if (String(nativeAck.stage || "") === "USER_TURN_INDETERMINATE") {
      transport.acknowledgement = {
        confirmed:false,
        via:"native_indeterminate"
      };
      transport.transition(SEND_TRANSPORT.INDETERMINATE, {
        request_id:String(nativeAck.request_id || ""),
        native_stage:"USER_TURN_INDETERMINATE",
        via:"native_transport",
        attempts:Array.isArray(nativeAck.submit_attempts)
          ? nativeAck.submit_attempts.length
          : 0
      });
      await clientEvent("SEND_INDETERMINATE", {});
      STATE.lastEvent = "SEND_INDETERMINATE";
      STATE.note = "Prompt gesendet; native Bestätigung noch unbestimmt";
      return;
    }

    if (String(nativeAck.stage || "") !== "USER_TURN_COMMITTED") {
      throw new Error(
        `native transport returned non-committed stage: ${String(nativeAck.stage || "")}`
      );
    }

    const acknowledgement = {
      confirmed:true,
      via:"user_message",
      native_stage:"USER_TURN_COMMITTED"
    };

    transport.acknowledgement = acknowledgement;
    transport.transition(SEND_TRANSPORT.ACCEPTED, {
      via:"user_message",
      request_id:String(nativeAck.request_id || ""),
      native_stage:"USER_TURN_COMMITTED"
    });
    PENDING_SEND_TRANSPORT = null;
    STATE.lastEvent = "PROMPT_SENT";
    STATE.note = "Prompt bestätigt via persistentem User-Turn";
    await clientEvent("NATIVE_USER_TURN_COMMITTED", {
      request_id:String(nativeAck.request_id || ""),
      via:"user_message",
      native_stage:"USER_TURN_COMMITTED"
    });
    await clientEvent("NATIVE_SEND_ACCEPTED", {
      request_id:String(nativeAck.request_id || ""),
      via:"user_message"
    });
  }

  async function sendPrompt(prompt) {
    try {
      return await sendPromptNative(prompt);
    } catch (error) {
      await clientEvent("NATIVE_TRANSPORT_FAILED", {
        message:String(error && error.message ? error.message : error)
      });

      if (!AGP_ALLOW_DEGRADED_DOM_FALLBACK) {
        throw error;
      }

      await clientEvent("DOM_TRANSPORT_DEGRADED_FALLBACK", {
        explicit_degraded_mode:true
      });
      return await sendPromptDomDegraded(prompt);
    }
  }

  async function sendPromptDomDegraded(prompt) {
    const transport = createSendTransport(prompt);
    if (prompt === STATE.lastPrompt) {
      throw new Error("identical prompt loop detected");
    }

    const beforeMessages = visibleUserMessages();
    const beforeAssistantText = lastAssistantText();
    transport.beforeAssistantText = beforeAssistantText;
    const composerEl = await waitForComposer();
    STATE.lastPrompt = prompt;
    setComposerText(composerEl, prompt);
    transport.transition(SEND_TRANSPORT.DRAFT_WRITTEN, {chars:prompt.length});
    const beforeComposerText = observedComposerText();
    const beforeGenerationActive = chatgptGenerationActive();

    let sentAttempt = false;
    for (let attempt = 0; attempt < 20; attempt += 1) {
      const button = sendButton(composerEl);
      if (button && !button.disabled) {
        button.click();
        sentAttempt = true;
        break;
      }
      await new Promise(resolve => setTimeout(resolve, 150));
    }

    if (!sentAttempt) {
      const el = composer();
      const form = el && el.closest ? el.closest("form") : null;
      if (form && typeof form.requestSubmit === "function") {
        form.requestSubmit();
        sentAttempt = true;
      }
    }

    if (!sentAttempt) {
      const el = composer();
      if (!el) throw new Error("ChatGPT composer not found");
      el.focus();
      const down = new KeyboardEvent("keydown", {
          key:"Enter",
          code:"Enter",
          keyCode:13,
          which:13,
          bubbles:true,
          cancelable:true
        });
      const up = new KeyboardEvent("keyup", {
          key:"Enter",
          code:"Enter",
          keyCode:13,
          which:13,
          bubbles:true,
          cancelable:true
        });
      el.dispatchEvent(down);
      el.dispatchEvent(up);
      sentAttempt = true;
    }

    if (!sentAttempt) {
      throw new Error("send path unavailable");
    }

    PENDING_SEND_TRANSPORT = transport;
    transport.transition(SEND_TRANSPORT.SUBMIT_ATTEMPTED, {attempt:1});
    transport.transition(SEND_TRANSPORT.WAITING_FOR_ACCEPTANCE, {attempt:1});
    let acknowledgement = await waitForSentUserMessage(
      prompt,
      beforeMessages,
      beforeAssistantText,
      beforeComposerText,
      beforeGenerationActive
    );

    // AGP_LATE_ACCEPTANCE_BOUNDARY_097
    // Timeout is epistemic uncertainty, not proof that ChatGPT rejected the send.
    // Retry remains bounded and requires positive evidence that the exact prompt
    // is still present and no generation has begun.
    if (!acknowledgement.confirmed) {
      const pendingComposer = observedComposerText();
      const expectedPrompt = normalizeObservedMessageText(prompt);
      const safeToRetry = (
        pendingComposer === expectedPrompt &&
        !chatgptGenerationActive()
      );

      if (safeToRetry) {
        transport.transition(SEND_TRANSPORT.SAFE_RETRY_ELIGIBLE, {
          via:acknowledgement.via || "unknown"
        });
        await clientEvent("SEND_RETRY_SAFE_PENDING_COMPOSER", {
          chars:prompt.length,
          first_via:acknowledgement.via || "",
          provisional:acknowledgement.provisional || ""
        });

        const retryComposer = composer();
        const retryButton = sendButton(retryComposer);
        if (retryButton && !retryButton.disabled) {
          retryButton.click();

          transport.retryCount += 1;
          transport.transition(SEND_TRANSPORT.RETRY_ATTEMPTED, {attempt:2});
          transport.transition(SEND_TRANSPORT.WAITING_FOR_ACCEPTANCE, {attempt:2});
          acknowledgement = await waitForSentUserMessage(
            prompt,
            beforeMessages,
            beforeAssistantText,
            expectedPrompt,
            false
          );

          await clientEvent(
            acknowledgement.confirmed
              ? "SEND_RETRY_CONFIRMED"
              : "SEND_RETRY_UNCONFIRMED",
            {
              via:acknowledgement.via || "",
              provisional:acknowledgement.provisional || ""
            }
          );
        }
      }
    }

    if (!acknowledgement.confirmed) {
      const expectedPrompt = normalizeObservedMessageText(prompt);
      const positiveUnsentEvidence = (
        observedComposerText() === expectedPrompt &&
        !chatgptGenerationActive()
      );

      if (positiveUnsentEvidence && transport.retryCount > 0) {
        transport.transition(SEND_TRANSPORT.FAILED_CONFIRMATION, {
          via:acknowledgement.via || "timeout",
          positive_unsent_evidence:true
        });
        PENDING_SEND_TRANSPORT = null;
        STATE.lastEvent = "SEND_UNCONFIRMED";
        throw new Error(
          "SEND_UNCONFIRMED: positive evidence shows the prompt is still unsent"
        );
      }

      transport.acknowledgement = acknowledgement;
      transport.transition(SEND_TRANSPORT.INDETERMINATE, {
        via:acknowledgement.via || "timeout",
        attempts:transport.retryCount + 1,
        generation_started_observed:Boolean(
          acknowledgement.generation_started_observed
        )
      });
      STATE.lastEvent = "SEND_INDETERMINATE";
      STATE.note = "Prompt gesendet; Bestätigung noch unbestimmt";
      return;
    }

    transport.acknowledgement = acknowledgement;
    transport.transition(SEND_TRANSPORT.ACCEPTED, {
      via:acknowledgement.via || "unknown",
      attempts:transport.retryCount + 1
    });
    PENDING_SEND_TRANSPORT = null;
    STATE.lastEvent = "PROMPT_SENT";
    STATE.note = `Prompt bestätigt via ${acknowledgement.via}`;
  }

  function resetCandidate() {
    STATE.candidateHash = "";
    STATE.candidateText = "";
    STATE.candidateStablePolls = 0;
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
            const value = JSON.parse(candidateText);
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

  function stop(reason, event="AUTO_STOPPED") {
    STATE.running = false;
    STATE.waitingForAssistant = false;
    resetCandidate();
    if (STATE.timer) clearInterval(STATE.timer);
    STATE.timer = null;
    STATE.note = reason || "";
    STATE.lastEvent = event;
    clientEvent(event, {reason:STATE.note});
    render();
  }

  function missionBootstrapPrompt(mission) {
    return [
      "AGP COCKPIT MISSION — FIRST SINGLE STEP",
      "",
      "Overall mission:",
      mission.mission_text,
      "",
      "Return exactly ONE bounded work order as a single JSON object.",
      "Required keys: kind, cwd, argv, timeout_seconds, label.",
      (
        mission.execution_mode === "LIVE"
          ? "This mission is LIVE. The validated command may really execute."
          : "For this DRY_RUN do not assume the command will actually execute."
      ),
      "Do not return prose before or after the JSON.",
      "If no safe bounded step is possible, return only:",
      '{"mission_state":"NEEDS_HUMAN","summary":"<exact reason>"}'
    ].join("\n");
  }

  async function maybeAutoStartTaskFirstMission() {
    const mission = STATE.mission;
    if (!mission || STATE.running) return;
    if (mission.execution_mode !== "LIVE" || mission.run_mode !== "FULL_AUTO") return;
    if (!String(mission.title || "").startsWith("Task · ")) return;
    if (!mission.mission_id) return;
    if (AGP_TASK_FIRST_AUTOSTART_MISSION_ID === mission.mission_id) return;
    const terminal = new Set(["DONE","COMPLETED","FAILED","ERROR","STOPPED","CANCELLED"]);
    if (terminal.has(String(mission.state || ""))) return;

    AGP_TASK_FIRST_AUTOSTART_MISSION_ID = mission.mission_id;
    STATE.note = "Task übernommen · Automatik startet";
    STATE.lastEvent = "TASK_FIRST_AUTOSTART";
    render();
    try {
      await startAuto();
    } catch (err) {
      AGP_TASK_FIRST_AUTOSTART_MISSION_ID = null;
      STATE.lastEvent = "TASK_FIRST_AUTOSTART_FAILED";
      STATE.note = String(err);
      render();
    }
  }

  async function pollExplicitTaskStartRequest() {
    if (STATE.running) return;
    try {
      const req = await api("/v1/task/start-request");
      const generation = Number(req.generation || 0);
      const missionId = String(req.mission_id || "");
      if (!AGP_TASK_FIRST_START_REQUEST_PRIMED) {
        AGP_TASK_FIRST_AUTOSTART_GENERATION = generation;
        AGP_TASK_FIRST_START_REQUEST_PRIMED = true;
        return;
      }
      if (!generation || generation <= AGP_TASK_FIRST_AUTOSTART_GENERATION) return;
      const status = await refreshStatus();
      if (!status.mission || status.mission.mission_id !== missionId) return;
      AGP_TASK_FIRST_AUTOSTART_GENERATION = generation;
      // An explicit desktop start request is authoritative for this generation.
      // Clear the legacy per-mission latch before entering the shared start path.
      AGP_TASK_FIRST_AUTOSTART_MISSION_ID = null;
      await maybeAutoStartTaskFirstMission();
    } catch (_err) {}
  }

  async function refreshStatus() {
    const result = await api("/v1/status");
    STATE.state = result.state || "IDLE";
    STATE.mission = result.mission || null;
    // K07: status refresh is observational only. A persisted READY/FULL_AUTO task
    // must not execute merely because the desktop app/bridge reconnects.
    STATE.lastRefresh = new Date();
    STATE.note = STATE.mission
      ? `${STATE.mission.state} · ${STATE.mission.title || "Mission"}`
      : "Keine aktive Mission";
    STATE.lastEvent = "STATUS_OK";
    render();
    return result;
  }

  async function submitAssistant(text) {
    // AGP_LIVE_PROBE_TERMINAL_SIGNAL_074
    // A terminal mission signal is not a work order. Let the server/runtime
    // validate and finalize DONE / NEEDS_HUMAN before applying probe-specific
    // argv assertions that are only meaningful for executable work orders.
    const terminalSignal = parsePureJsonObject(text);
    const terminalState = (
      terminalSignal &&
      typeof terminalSignal.mission_state === "string"
    ) ? terminalSignal.mission_state : "";

    if (!["DONE", "NEEDS_HUMAN"].includes(terminalState)) {
      assertExactLiveProbeWorkOrder(text);
      assertBoundedMultiTurnLiveProbeWorkOrder(text);
    }

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

  async function processCompletedAssistant(text) {
    const result = await submitAssistant(text);

    // AGP_TURN_ACCOUNTING_064_R1
    STATE.turns += 1;
    render();

    if (result.action !== "continue" || !result.prompt) {
      stop(
        `${result.state}: ${result.note || ""}`,
        result.state || "AUTO_STOPPED"
      );
      await refreshStatus();
      return;
    }

    STATE.assistantBaselineCount = assistantMessageNodes().length;
    await sendPrompt(result.prompt);
    // K07: do not claim the next turn if the RESULT is still only a draft.
    if (normalizeObservedMessageText(observedComposerText()).includes(normalizeObservedMessageText(result.prompt).slice(0, 80))) {
      throw new Error("result prompt remained in composer after send acknowledgement");
    }
    STATE.note = result.state || "";
    STATE.lastEvent = "PROMPT_SENT";
    STATE.waitingForAssistant = true;
    resetCandidate();
    await clientEvent("PROMPT_SENT", {
      state:result.state
    });
    render();
  }

  function newAssistantTextAfterBaseline() {
    const nodes = assistantMessageNodes();
    if (nodes.length <= STATE.assistantBaselineCount) return "";
    return lastAssistantText();
  }

  async function tick() {
    await pollExplicitTaskStartRequest();
    if (!STATE.running || !STATE.waitingForAssistant) return;

    try {
      const text = newAssistantTextAfterBaseline();
      if (!text) return;

      const hash = await digest(text);

      if (hash === STATE.lastAssistantHash) {
        resetCandidate();
        return;
      }

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
          resetCandidate();
          render();
          await sendPrompt(formatRepairPrompt(repairAttempt));
          return;
        }
        throw new Error("assistant response stayed stable but is not a complete pure JSON object after automatic format repair");
      }

      AGP_FORMAT_REPAIR_ATTEMPTS = 0; // valid structured response
      STATE.lastAssistantHash = STATE.candidateHash;
      STATE.waitingForAssistant = false;
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
      await processCompletedAssistant(completedForProcessing);

    } catch (err) {
      STATE.errors += 1;
      STATE.note = String(err);
      STATE.lastEvent = "TICK_ERROR";
      await clientEvent("TICK_ERROR", {
        message:String(err)
      });

      if (STATE.errors >= LIMITS.maxErrors) {
        stop(String(err), "AUTO_ERROR");
      } else {
        STATE.waitingForAssistant = true;
        resetCandidate();
        render();
      }
    }
  }

  const LIVE_PROBE = {
    title:"061 LIVE READ-ONLY PROBE",
    missionText:
      "Execute exactly one read-only repository status check. " +
      // AGP_K07_JSON_SERIALIZATION_CONTRACT_751
      "The response must be parseable by JSON.parse as one complete JSON object. " +
      "Escape every double quote inside JSON string values using the standard JSON backslash escape; escape backslashes as required. " +
      "Do not return JSON-like text that is syntactically invalid JSON. " +
      "For shell work orders such as /bin/sh -lc, inner double quotes in argv strings must use the standard JSON backslash escape. " +
      "Return exactly one JSON work order with kind=generic, " +
      "cwd=/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit, " +
      "argv=[\"/usr/bin/git\",\"status\",\"--short\"], " +
      "timeout_seconds no greater than 30, and a short label. " +
      "Do not propose any other command. Do not modify files.",
    cwd:"/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit",
    argv:["/usr/bin/git","status","--short"]
  };


  // AGP_MULTITURN_LIVE_PROBE_065
  const MULTITURN_LIVE_PROBE = {
    title:"065 LIVE 3-TURN READ-ONLY PROBE",
    missionText:
      "Execute exactly three bounded read-only repository observations, one work order per turn, in this order: " +
      "(1) /usr/bin/git status --short, " +
      "(2) /usr/bin/git branch --show-current, " +
      "(3) /usr/bin/git log -1 --oneline. " +
      "cwd is always /Users/hof/Dropbox/Privat/GitHub/agp-Cockpit. " +
      "Return exactly one pure JSON work order per assistant response. " +
      "Do not modify files and do not propose any other command.",
    cwd:"/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit",
    steps:[
      ["/usr/bin/git","status","--short"],
      ["/usr/bin/git","branch","--show-current"],
      ["/usr/bin/git","log","-1","--oneline"]
    ]
  };

  function isMultiTurnLiveProbeMission() {
    return Boolean(
      STATE.mission &&
      STATE.mission.execution_mode === "LIVE" &&
      STATE.mission.title === MULTITURN_LIVE_PROBE.title
    );
  }

  function assertBoundedMultiTurnLiveProbeWorkOrder(text) {
    if (!isMultiTurnLiveProbeMission()) return;
    let data;
    try {
      data = JSON.parse(text);
    } catch (_) {
      throw new Error(
        "065 multi-turn LIVE probe rejected before local submit: assistant response is not pure JSON"
      );
    }

    const stepIndex = Math.max(0, Math.min(
      MULTITURN_LIVE_PROBE.steps.length - 1,
      Number(STATE.turns || 0)
    ));
    const expected = MULTITURN_LIVE_PROBE.steps[stepIndex];
    const exactArgv = (
      Array.isArray(data.argv) &&
      data.argv.length === expected.length &&
      data.argv.every((value, index) => value === expected[index])
    );
    const timeout = Number(data.timeout_seconds);

    if (
      data.kind !== "generic" ||
      data.cwd !== MULTITURN_LIVE_PROBE.cwd ||
      !exactArgv ||
      !Number.isFinite(timeout) ||
      timeout <= 0 ||
      timeout > 30
    ) {
      throw new Error(
        "065 multi-turn LIVE probe rejected before local submit: work order differs from bounded read-only sequence"
      );
    }
  }

  function isLiveProbeMission() {
    return Boolean(
      STATE.mission &&
      STATE.mission.execution_mode === "LIVE" &&
      STATE.mission.title === LIVE_PROBE.title
    );
  }

  function assertExactLiveProbeWorkOrder(text) {
    if (!isLiveProbeMission()) {
      return;
    }

    let data;
    try {
      data = JSON.parse(text);
    } catch (_) {
      throw new Error(
        "LIVE probe rejected before local submit: assistant response is not pure JSON"
      );
    }

    const exactArgv = (
      Array.isArray(data.argv) &&
      data.argv.length === LIVE_PROBE.argv.length &&
      data.argv.every(
        (value, index) => value === LIVE_PROBE.argv[index]
      )
    );

    const timeout = Number(data.timeout_seconds);

    if (
      data.kind !== "generic" ||
      data.cwd !== LIVE_PROBE.cwd ||
      !exactArgv ||
      !Number.isFinite(timeout) ||
      timeout <= 0 ||
      timeout > 30
    ) {
      throw new Error(
        "LIVE probe rejected before local submit: work order differs from exact read-only git status contract"
      );
    }
  }

  async function newLiveProbeMission() {
    const result = await api(
      "/v1/mission",
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          title:LIVE_PROBE.title,
          mission_text:LIVE_PROBE.missionText,
          execution_mode:"LIVE",
          run_mode:"SINGLE_STEP"
        })
      }
    );

    STATE.mission = result.mission;
    STATE.state = result.mission.state;
    STATE.note = "Neue LIVE/SINGLE_STEP Read-only-Probe angelegt";
    STATE.lastEvent = "LIVE_PROBE_MISSION_CREATED";
    STATE.errorId = "";
    STATE.turns = 0;
    resetCandidate();

    await clientEvent(
      "LIVE_PROBE_MISSION_CREATED",
      {
        cwd:LIVE_PROBE.cwd,
        argv:LIVE_PROBE.argv
      }
    );

    render();
  }


  async function newMultiTurnLiveProbeMission() {
    const result = await api(
      "/v1/mission",
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          title:MULTITURN_LIVE_PROBE.title,
          mission_text:MULTITURN_LIVE_PROBE.missionText,
          execution_mode:"LIVE",
          run_mode:"FULL_AUTO"
        })
      }
    );
    STATE.mission = result.mission;
    STATE.state = result.mission.state;
    STATE.turns = 0;
    STATE.errors = 0;
    STATE.note = "Neue 065 LIVE/SINGLE_STEP 3-Turn Read-only-Probe angelegt";
    STATE.lastEvent = "MULTITURN_LIVE_PROBE_MISSION_CREATED";
    STATE.errorId = "";
    render();
    await clientEvent("MULTITURN_LIVE_PROBE_MISSION_CREATED", {steps:3});
  }


  // AGP_PHASE7_SINGLE_ROUND_UI_254
  async function phase7RunOneRound() {
    const ctl = globalThis.AGPCockpitPhase7SingleRound;
    if (!ctl || typeof ctl.runOneRound !== "function") throw new Error("Phase-7 controller is not loaded");
    STATE.note = "Phase 7: ein DIRECT_EXECUTION-Round läuft …";
    render();
    try {
      const result = await ctl.runOneRound();
      STATE.note = `Phase 7: ${result.state} · ${result.action_id}`;
      render();
      return result;
    } catch (error) {
      STATE.note = `Phase 7 BLOCK: ${error instanceof Error ? error.message : String(error)}`;
      render();
      throw error;
    }
  }

// AGP_PHASE5_CONVERSATION_UI_203
  let PHASE5_LAST_DRAFT = null;
  let PHASE5_BASELINE_FINGERPRINT = "";

  function phase5Contract() {
    const contract = globalThis.AGPCockpitConversationContract;
    if (!contract || contract.marker !== "AGP_PHASE5_CONVERSATION_CONTRACT_204") {
      throw new Error("Phase-5 conversation contract is not loaded");
    }
    return contract;
  }

  async function phase5Bind() {
    const contract = phase5Contract();
    const binding = await contract.bindConfiguredConversation();
    STATE.note = `Phase 5 gebunden: ${binding.conversationUrl}`;
    STATE.lastEvent = "PHASE5_BOUND";
    render();
  }

  async function phase5StageDraft() {
    const contract = phase5Contract();
    const binding = await contract.bindConfiguredConversation();
    let baseline = "";
    try {
      baseline = (await contract.currentAssistantSnapshot()).fingerprint;
    } catch (err) {
      if (!String(err).includes("PHASE5_ASSISTANT_NOT_FOUND")) throw err;
    }

    const text = window.prompt(
      "Phase 5: Text nur in den ChatGPT-Composer einsetzen (noch NICHT senden):"
    );
    if (text === null) {
      STATE.note = "Phase-5-Draft abgebrochen";
      STATE.lastEvent = "PHASE5_DRAFT_CANCELLED";
      render();
      return;
    }

    PHASE5_LAST_DRAFT = await contract.stageDraft(text);
    PHASE5_BASELINE_FINGERPRINT = baseline;
    STATE.note =
      `Phase-5-Draft eingesetzt (${PHASE5_LAST_DRAFT.chars} Zeichen), nicht gesendet · ${binding.conversationUrl}`;
    STATE.lastEvent = "PHASE5_DRAFT_STAGED_NOT_SENT";
    render();
  }

  async function phase5ConfirmAndSend() {
    const contract = phase5Contract();
    if (!PHASE5_LAST_DRAFT) {
      throw new Error("Kein Phase-5-Draft zum Senden vorgemerkt");
    }

    const confirmed = window.confirm(
      "Phase 5: Den aktuell sichtbaren Draft jetzt an die konfigurierte ChatGPT-Konversation senden?"
    );
    if (!confirmed) {
      contract.invalidateApproval();
      STATE.note = "Phase-5-Senden nicht bestätigt; Draft bleibt stehen";
      STATE.lastEvent = "PHASE5_SEND_NOT_CONFIRMED";
      render();
      return;
    }

    const approval = await contract.approveCurrentDraft();
    await contract.sendApprovedDraft(approval);
    STATE.note = "Phase-5-Draft explizit bestätigt und gesendet; warte auf nächste abgeschlossene Antwort";
    STATE.lastEvent = "PHASE5_SEND_CONFIRMED";
    render();

    const next = await contract.waitForCompletedAssistant({
      afterFingerprint: PHASE5_BASELINE_FINGERPRINT,
      timeoutMs: 120000,
      pollMs: 500,
      stablePolls: 3
    });

    PHASE5_LAST_DRAFT = null;
    PHASE5_BASELINE_FINGERPRINT = next.fingerprint;
    STATE.note =
      `Nächste abgeschlossene Phase-5-Antwort erkannt (${next.text.length} Zeichen)`;
    STATE.lastEvent = "PHASE5_NEXT_RESPONSE_COMPLETE";
    render();
  }


  async function newDryMission() {
    const text = window.prompt(
      "Mission für AGP Cockpit (DRY_RUN + SINGLE_STEP):"
    );
    if (!text) return;

    const result = await api(
      "/v1/mission",
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          title:document.title || "Chrome mission",
          mission_text:text,
          execution_mode:"DRY_RUN",
          run_mode:"SINGLE_STEP"
        })
      }
    );

    STATE.mission = result.mission;
    STATE.state = result.mission.state;
    STATE.note = "Neue DRY_RUN/SINGLE_STEP Mission angelegt";
    STATE.lastEvent = "MISSION_CREATED";
    STATE.errorId = "";
    STATE.turns = 0;
    resetCandidate();
    render();
  }

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
    STATE.assistantBaselineCount = assistantMessageNodes().length;
    resetCandidate();
    await sendPrompt(pending);

    STATE.running = true;
    STATE.waitingForAssistant = true;
    STATE.lastEvent = "NEXT_STEP_PROMPT_SENT";
    await clientEvent("NEXT_STEP_PROMPT_SENT", {
      chars:pending.length
    });
    render();

    if (STATE.timer) clearInterval(STATE.timer);
    STATE.timer = setInterval(tick, LIMITS.pollMs);
  }

  async function startAuto() {
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

    if (mission.state !== "READY") {
      throw new Error(
        `mission must be READY for initial start, got ${mission.state}`
      );
    }

    STATE.running = true;
    STATE.turns = 0;
    STATE.errors = 0;
    STATE.startedAt = Date.now();
    STATE.lastPrompt = "";
    STATE.lastAssistantHash = await digest(lastAssistantText());
    STATE.assistantBaselineCount = assistantMessageNodes().length;
    resetCandidate();

    const bootstrap = missionBootstrapPrompt(mission);

    STATE.lastEvent = "MISSION_BOOTSTRAP_PREPARED";
    await clientEvent("MISSION_BOOTSTRAP_PREPARED", {
      mission_chars:(mission.mission_text || "").length,
      bootstrap_chars:bootstrap.length
    });
    render();

    try {
      await sendPrompt(bootstrap);
    } catch (err) {
      stop(String(err), "MISSION_BOOTSTRAP_SEND_FAILED");
      return;
    }

    STATE.waitingForAssistant = true;
    STATE.lastEvent = "MISSION_BOOTSTRAP_SENT";
    STATE.note = "Warte auf vollständige neue ChatGPT-Antwort";
    await clientEvent("MISSION_BOOTSTRAP_SENT", {
      chars:bootstrap.length
    });
    render();

    if (STATE.timer) clearInterval(STATE.timer);
    STATE.timer = setInterval(tick, LIMITS.pollMs);
  }

  // AGP_START_AUTO_CLICK_PATH_077
  function btn(label, cls, handler) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = cls;
    b.textContent = label;
    b.addEventListener("mousedown", event => event.stopPropagation());
    b.addEventListener("click", async event => {
      event.preventDefault();
      event.stopPropagation();

      STATE.lastEvent = "UI_BUTTON_CLICKED";
      STATE.note = `Button: ${label}`;
      render();
      await clientEvent("UI_BUTTON_CLICKED", {
        label,
        class_name:cls
      });

      try {
        await handler();
      } catch (err) {
        STATE.note = String(err);
        STATE.lastEvent = "UI_ACTION_ERROR";
        await clientEvent("UI_ACTION_ERROR", {
          label,
          class_name:cls,
          message:String(err)
        });
        render();
      }
    });
    return b;
  }

  function pill(text, cls="") {
    const p = document.createElement("span");
    p.className = `agp-pill ${cls}`.trim();
    p.textContent = text;
    return p;
  }

  // AGP_OVERLAY_DRAG_MINIMIZE_063S2
  const AGP_OVERLAY_UI_KEY = "agpOverlayUi063S2";
  let AGP_OVERLAY_UI = {left:null, top:null, minimized:false};
  let AGP_OVERLAY_UI_LOADED = false;
  let AGP_DRAG = null;

  async function loadOverlayUiState() {
    if (AGP_OVERLAY_UI_LOADED) return;
    AGP_OVERLAY_UI_LOADED = true;
    try {
      const stored = await chrome.storage.local.get([AGP_OVERLAY_UI_KEY]);
      const value = stored && stored[AGP_OVERLAY_UI_KEY];
      if (value && typeof value === "object") {
        AGP_OVERLAY_UI = {
          left:Number.isFinite(value.left) ? value.left : null,
          top:Number.isFinite(value.top) ? value.top : null,
          minimized:Boolean(value.minimized)
        };
      }
    } catch (_) {}
  }

  function saveOverlayUiState() {
    try {
      chrome.storage.local.set({[AGP_OVERLAY_UI_KEY]:AGP_OVERLAY_UI});
    } catch (_) {}
  }

  function clampOverlayPosition(root, left, top) {
    const rect = root.getBoundingClientRect();
    const maxLeft = Math.max(0, window.innerWidth - rect.width);
    const maxTop = Math.max(0, window.innerHeight - rect.height);
    return {
      left:Math.min(Math.max(0, left), maxLeft),
      top:Math.min(Math.max(0, top), maxTop)
    };
  }

  function applyOverlayUiState(root) {
    root.classList.toggle("agp-minimized", Boolean(AGP_OVERLAY_UI.minimized));
    if (Number.isFinite(AGP_OVERLAY_UI.left) && Number.isFinite(AGP_OVERLAY_UI.top)) {
      const pos = clampOverlayPosition(root, AGP_OVERLAY_UI.left, AGP_OVERLAY_UI.top);
      root.style.left = `${pos.left}px`;
      root.style.top = `${pos.top}px`;
      root.style.right = "auto";
      root.style.bottom = "auto";
    }
  }

  function beginOverlayDrag(event, root) {
    if (event.button !== 0) return;
    if (event.target && event.target.closest && event.target.closest("button")) return;
    const rect = root.getBoundingClientRect();
    AGP_DRAG = {
      root,
      dx:event.clientX - rect.left,
      dy:event.clientY - rect.top
    };
    event.preventDefault();
  }

  function moveOverlayDrag(event) {
    if (!AGP_DRAG) return;
    const pos = clampOverlayPosition(
      AGP_DRAG.root,
      event.clientX - AGP_DRAG.dx,
      event.clientY - AGP_DRAG.dy
    );
    AGP_DRAG.root.style.left = `${pos.left}px`;
    AGP_DRAG.root.style.top = `${pos.top}px`;
    AGP_DRAG.root.style.right = "auto";
    AGP_DRAG.root.style.bottom = "auto";
    AGP_OVERLAY_UI.left = pos.left;
    AGP_OVERLAY_UI.top = pos.top;
  }

  function endOverlayDrag() {
    if (!AGP_DRAG) return;
    AGP_DRAG = null;
    saveOverlayUiState();
  }

  window.addEventListener("mousemove", moveOverlayDrag);
  window.addEventListener("mouseup", endOverlayDrag);
  window.addEventListener("resize", () => {
    const root = document.getElementById("agp-cockpit-bridge");
    if (!root) return;
    if (!Number.isFinite(AGP_OVERLAY_UI.left) || !Number.isFinite(AGP_OVERLAY_UI.top)) return;
    const pos = clampOverlayPosition(root, AGP_OVERLAY_UI.left, AGP_OVERLAY_UI.top);
    AGP_OVERLAY_UI.left = pos.left;
    AGP_OVERLAY_UI.top = pos.top;
    applyOverlayUiState(root);
    saveOverlayUiState();
  });

  function render() {
    ensureStyle();
    loadOverlayUiState().then(() => {
      const current = document.getElementById("agp-cockpit-bridge");
      if (current) applyOverlayUiState(current);
    });

    let root = document.getElementById("agp-cockpit-bridge");
    if (!root) {
      root = document.createElement("div");
      root.id = "agp-cockpit-bridge";
      document.body.appendChild(root);
    }

    root.innerHTML = "";

    const head = document.createElement("div");
    head.className = "agp-head";
    head.title = "Ziehen zum Verschieben";
    head.addEventListener("mousedown", event => beginOverlayDrag(event, root));

    const title = document.createElement("span");
    title.textContent = "AGP Cockpit Bridge";
    head.appendChild(title);

    const dot = document.createElement("span");
    dot.className = `agp-dot ${STATE.connected ? "on" : ""}`;
    head.appendChild(dot);

    const conn = document.createElement("span");
    conn.style.fontSize = "11px";
    conn.style.color = STATE.connected ? "#62d879" : "#9fb0bc";
    conn.textContent = STATE.connected ? "CONNECTED" : "LOCAL";
    head.appendChild(conn);

    if (STATE.running) {
      const busy = document.createElement("span");
      busy.className = "agp-busy";
      busy.setAttribute("role", "status");
      busy.setAttribute("aria-live", "polite");

      const spinner = document.createElement("span");
      spinner.className = "agp-spinner";
      spinner.setAttribute("aria-hidden", "true");
      busy.appendChild(spinner);

      const busyText = document.createElement("span");
      busyText.textContent = STATE.waitingForAssistant
        ? "ChatGPT arbeitet…"
        : "Cockpit arbeitet…";
      busy.appendChild(busyText);

      head.appendChild(busy);
    }

    const grow = document.createElement("span");
    grow.className = "agp-grow";
    head.appendChild(grow);

    head.appendChild(pill(STATE.state || "IDLE"));

    if (STATE.mission) {
      head.appendChild(pill(STATE.mission.execution_mode || "", "mode"));
      head.appendChild(pill(STATE.mission.run_mode || "", "run"));
    }

    const minimize = document.createElement("button");
    minimize.className = "agp-minimize";
    minimize.type = "button";
    minimize.title = AGP_OVERLAY_UI.minimized ? "Cockpit einblenden" : "Cockpit minimieren";
    minimize.textContent = AGP_OVERLAY_UI.minimized ? "▣" : "—";
    minimize.addEventListener("mousedown", event => event.stopPropagation());
    minimize.addEventListener("click", event => {
      event.preventDefault();
      event.stopPropagation();
      AGP_OVERLAY_UI.minimized = !AGP_OVERLAY_UI.minimized;
      saveOverlayUiState();
      render();
    });
    head.appendChild(minimize);

    applyOverlayUiState(root);
    root.appendChild(head);

    const actions = document.createElement("div");
    actions.className = "agp-actions";

    actions.appendChild(
      btn(
        STATE.running ? "▶ Aufgabe läuft" : "▶ Aufgabe starten",
        "start",
        startAuto
      )
    );
    actions.appendChild(btn("■ Stoppen", "stop", async () => stop("Stopped by user")));
    actions.appendChild(btn("⏭ Nächster Schritt", "next", resumeStep));
    actions.appendChild(btn("↻ Aktualisieren", "status", refreshStatus));

    const diagnosticsToggle = btn(
      AGP_DIAGNOSTICS_OPEN ? "▾ Diagnose" : "▸ Diagnose",
      "status",
      () => {
        AGP_DIAGNOSTICS_OPEN = !AGP_DIAGNOSTICS_OPEN;
        render();
      }
    );
    diagnosticsToggle.setAttribute("aria-expanded", String(Boolean(AGP_DIAGNOSTICS_OPEN)));
    diagnosticsToggle.setAttribute("aria-controls", "agp-cockpit-diagnostics");
    actions.appendChild(diagnosticsToggle);
    root.appendChild(actions);

    if (AGP_DIAGNOSTICS_OPEN) {
      const diagnostics = document.createElement("div");
      diagnostics.id = "agp-cockpit-diagnostics";
      diagnostics.className = "agp-actions agp-diagnostics";
      diagnostics.setAttribute("role", "region");
      diagnostics.setAttribute("aria-label", "Entwicklerdiagnose");
      diagnostics.appendChild(btn("Neue DRY-Mission", "mission", newDryMission));
      diagnostics.appendChild(btn("LIVE-Probe", "liveprobe", newLiveProbeMission));
      diagnostics.appendChild(btn("LIVE 3-Turn", "liveprobe", newMultiTurnLiveProbeMission));
      diagnostics.appendChild(btn("Phase 5: Bind", "status", phase5Bind));
      diagnostics.appendChild(btn("Phase 5: Draft", "mission", phase5StageDraft));
      diagnostics.appendChild(btn("Phase 5: Send", "stop", phase5ConfirmAndSend));
      diagnostics.appendChild(btn("Phase 7: One Round", "start", phase7RunOneRound));
      diagnostics.appendChild(btn("Phase 8: Run", "start", phase8RunMultiRound));
      diagnostics.appendChild(btn("Phase 8: Pause", "status", phase8Pause));
      diagnostics.appendChild(btn("Phase 8: Resume", "mission", phase8Resume));
      diagnostics.appendChild(btn("Phase 8: Stop", "stop", phase8Stop));
      root.appendChild(diagnostics);
    }

    const body = document.createElement("div");
    body.className = "agp-body";

    const turns = document.createElement("div");
    turns.className = "agp-cell";

    const tLabel = document.createElement("div");
    tLabel.className = "agp-label";
    tLabel.textContent = "Turns";
    turns.appendChild(tLabel);

    const tBig = document.createElement("div");
    tBig.className = "agp-big";
    tBig.textContent = `${STATE.turns} / ${LIMITS.maxTurns}`;
    turns.appendChild(tBig);

    const progress = document.createElement("div");
    progress.className = "agp-progress";
    const fill = document.createElement("div");
    fill.style.width =
      `${Math.min(100, STATE.turns / LIMITS.maxTurns * 100)}%`;
    progress.appendChild(fill);
    turns.appendChild(progress);
    body.appendChild(turns);

    const mission = document.createElement("div");
    mission.className = "agp-cell";

    const mLabel = document.createElement("div");
    mLabel.className = "agp-label";
    mLabel.textContent = "Mission";
    mission.appendChild(mLabel);

    const mText = document.createElement("div");
    mText.className = "agp-note";
    mText.textContent = STATE.mission
      ? `${STATE.mission.state} — ${STATE.mission.title || "Mission"} · Steps ${STATE.mission.step_count || 0}`
      : "IDLE — Keine aktive Mission";
    mission.appendChild(mText);

    if (STATE.note) {
      const note = document.createElement("div");
      note.className = "agp-note";
      note.style.marginTop = "4px";
      note.textContent = STATE.note;
      mission.appendChild(note);
    }

    body.appendChild(mission);

    const refreshed = document.createElement("div");
    refreshed.className = "agp-cell";

    const rLabel = document.createElement("div");
    rLabel.className = "agp-label";
    rLabel.textContent = "Aktualisiert";
    refreshed.appendChild(rLabel);

    const rText = document.createElement("div");
    rText.className = "agp-big";
    rText.style.fontSize = "14px";
    rText.textContent = STATE.lastRefresh
      ? STATE.lastRefresh.toLocaleTimeString()
      : "—";
    refreshed.appendChild(rText);

    body.appendChild(refreshed);
    root.appendChild(body);

    const debug = document.createElement("div");
    debug.className = "agp-debug";
    debug.textContent = `Last event: ${STATE.lastEvent}`;

    if (STATE.errorId) {
      const error = document.createElement("span");
      error.className = "agp-error";
      error.textContent = ` · ${STATE.errorId}`;
      debug.appendChild(error);
    }

    if (AGP_DIAGNOSTICS_OPEN) {
      root.appendChild(debug);
    }
  }

  render();

  sendHandshake();
  setInterval(sendHandshake, 15000);

  refreshStatus().catch(err => {
    STATE.note = String(err);
    STATE.lastEvent = "INITIAL_STATUS_ERROR";
    render();
  });

  // AGP_PHASE8_OPERATOR_UI_286
  async function phase8RunMultiRound() {
    const P8 = window.AGPCockpitPhase8MultiRound;
    if (!P8) throw new Error("Phase8 controller unavailable");
    const raw = window.prompt("Phase 8: maximale Rundenzahl", "5");
    if (raw === null) return;
    STATE.turns = 0;
    STATE.note = "Phase 8: RUNNING (0 rounds)";
    STATE.lastEvent = "PHASE8_RUNNING";
    render();
    // AGP_PHASE8_UI_LIVE_ROUND_PROGRESS_328
  const out = await P8.run({
    maxRounds:Number(raw),
    onRoundCompleted: ({rounds}) => {
      STATE.turns = Number(rounds || 0);
      STATE.note = `Phase 8: RUNNING (${STATE.turns} rounds)`;
      STATE.lastEvent = "PHASE8_ROUND_COMPLETED";
      render();
    }
  });
    // K04: Protocol-v1 DONE is transport termination only. It becomes a
    // durable completion proposal; verification remains evidence-bound in
    // DurableTaskController and is never performed by the browser.
    let durableTaskState = "";
    if (out.state === "DONE") {
      const sessionId = String(
        (out.control && out.control.session_id) ||
        (out.last && out.last.session_id) ||
        ""
      ).trim();
      if (!sessionId) throw new Error("K04_DONE_SESSION_REQUIRED");
      const proposal = await api(
        "/v1/task/complete-proposal",
        {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({"session_id":sessionId})
        }
      );
      if (
        proposal.authority !== "DurableTaskController" ||
        !proposal.accepted ||
        !proposal.task ||
        proposal.task.state !== "COMPLETE_PROPOSED"
      ) throw new Error("K04_COMPLETION_PROPOSAL_REJECTED");
      durableTaskState = proposal.task.state;
    }
    // AGP_PHASE8_UI_STATE_REPAIR_316
    STATE.turns = Number(out.rounds || 0);
    STATE.note = durableTaskState
      ? `Phase 8: ${out.state} / ${durableTaskState} (${out.rounds} rounds)`
      : `Phase 8: ${out.state} (${out.rounds} rounds)`;
    STATE.lastEvent = `PHASE8_${out.state}`;
    render();
  }
  function phase8Pause(){
    window.AGPCockpitPhase8MultiRound.pause();
    STATE.note = "Phase 8: PAUSED";
    STATE.lastEvent = "PHASE8_PAUSED";
    render();
  }
  function phase8Resume(){
    window.AGPCockpitPhase8MultiRound.resume();
    STATE.note = "Phase 8: RUNNING";
    STATE.lastEvent = "PHASE8_RUNNING";
    render();
  }
  function phase8Stop(){
    window.AGPCockpitPhase8MultiRound.stop();
    STATE.note = "Phase 8: STOP REQUESTED";
    STATE.lastEvent = "PHASE8_STOP_REQUESTED";
    render();
  }

  // K07: passive READY state still observes explicit desktop start requests.
  // The first observed generation is only baselined by the poll function.
  if (!AGP_TASK_FIRST_START_REQUEST_TIMER) {
    AGP_TASK_FIRST_START_REQUEST_TIMER = setInterval(() => {
      void pollExplicitTaskStartRequest();
    }, LIMITS.pollMs);
  }

})();
