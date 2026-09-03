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
    candidateStablePolls: 0
  };

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

  function lastAssistantText() {
    const nodes = Array.from(
      document.querySelectorAll('[data-message-author-role="assistant"]')
    );
    if (!nodes.length) return "";
    return (nodes[nodes.length - 1].innerText || "").trim();
  }

  function composer() {
    return (
      document.querySelector('#prompt-textarea') ||
      document.querySelector('textarea') ||
      document.querySelector('[contenteditable="true"]')
    );
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
    return chrome.storage.local.get({
      token:"",
      baseUrl:"http://127.0.0.1:8765"
    });
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
          body:JSON.stringify({event, details})
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
    return Array.from(
      document.querySelectorAll('[data-message-author-role="user"]')
    )
      .filter(el => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0;
      })
      .map(el => (el.innerText || el.textContent || "").trim())
      .filter(Boolean);
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
      if (generationNow && !beforeGenerationActive) {
        return {confirmed:true, via:"generation_started"};
      }

      const assistantNow = normalizeObservedMessageText(lastAssistantText());
      if (assistantNow && assistantNow !== assistantBefore) {
        return {confirmed:true, via:"assistant_activity"};
      }
    }

    return {
      confirmed:false,
      via:"timeout",
      provisional:provisionalComposerEvidence
    };
  }

    // AGP_BROWSER_SENDER_TRANSPORT_STATE_MACHINE_092
  const SEND_TRANSPORT = Object.freeze({
    IDLE:"IDLE",
    DRAFT_WRITTEN:"DRAFT_WRITTEN",
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

async function sendPrompt(prompt) {
    const transport = createSendTransport(prompt);
    if (prompt === STATE.lastPrompt) {
      throw new Error("identical prompt loop detected");
    }

    const beforeMessages = visibleUserMessages();
    const beforeAssistantText = lastAssistantText();
    transport.beforeAssistantText = beforeAssistantText;
    const composerEl = composer();
    if (!composerEl) throw new Error("ChatGPT composer not found");
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
        attempts:transport.retryCount + 1
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

  async function refreshStatus() {
    const result = await api("/v1/status");
    STATE.state = result.state || "IDLE";
    STATE.mission = result.mission || null;
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

    const result = await api(
      "/v1/turn",
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          conversation_url:location.href,
          assistant_text:text,
          turn_id:crypto.randomUUID()
        })
      }
    );

    STATE.lastEvent = "TURN_SUBMIT_OK";
    STATE.state = result.state || STATE.state;
    return result;
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

    await sendPrompt(result.prompt);
    STATE.note = result.state || "";
    STATE.lastEvent = "PROMPT_SENT";
    STATE.waitingForAssistant = true;
    resetCandidate();
    await clientEvent("PROMPT_SENT", {
      state:result.state
    });
    render();
  }

  async function tick() {
    if (!STATE.running || !STATE.waitingForAssistant) return;

    try {
      const text = lastAssistantText();
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
      const structured = parsePureJsonObject(completed);

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

        throw new Error(
          "assistant response stayed stable but is not a complete pure JSON object"
        );
      }

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
      await processCompletedAssistant(completed);

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
        STATE.running ? "▶ Auto läuft" : "▶ Start Auto",
        "start",
        startAuto
      )
    );
    actions.appendChild(
      btn("■ Stop", "stop", async () => stop("Stopped by user"))
    );
    actions.appendChild(
      btn("+ New DRY Mission", "mission", newDryMission)
    );
    actions.appendChild(
      btn("● LIVE Probe", "liveprobe", newLiveProbeMission)
    );
    actions.appendChild(
      btn("③ LIVE 3-Turn", "liveprobe", newMultiTurnLiveProbeMission)
    );
    actions.appendChild(
      btn("⏭ Next Step", "next", resumeStep)
    );
    actions.appendChild(
      btn("↻ Status", "status", refreshStatus)
    );

    root.appendChild(actions);

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

    root.appendChild(debug);
  }

  render();

  sendHandshake();
  setInterval(sendHandshake, 15000);

  refreshStatus().catch(err => {
    STATE.note = String(err);
    STATE.lastEvent = "INITIAL_STATUS_ERROR";
    render();
  });
})();
