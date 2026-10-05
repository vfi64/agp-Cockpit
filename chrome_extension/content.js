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


  function pythonAttachmentRow(anchor) {
    const href = String(anchor.href || anchor.getAttribute("href") || "").trim();
    const label = String(
      anchor.getAttribute("download") ||
      anchor.getAttribute("aria-label") ||
      anchor.getAttribute("title") ||
      anchor.textContent ||
      ""
    ).trim();
    const match = label.match(/(?:^|[\s/])([^\s/]+\.(?:py|json)(?:[?#][^\s]*)?)/i);
    const name = match ? match[1] : label.split("/").pop().trim();
    let row = anchor;
    let downloadNode = null;
    for (let depth = 0; depth < 8 && row; depth += 1, row = row.parentElement) {
      downloadNode = row.querySelector('button[aria-label="Datei herunterladen"], button[aria-label="Download"]');
      if (downloadNode) break;
    }
    return {href, name, isButton: anchor.tagName === "BUTTON", node: anchor, downloadNode};
  }

  // AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1
  // The local bridge assigns a fresh work-order number for every remote turn
  // and reserves every number that may already be visible remotely. A file
  // card named <expectedStep>_*.py is therefore the identity of the awaited
  // response, exactly like the send nonce identifies the committed user turn.
  // Discovery must not depend on assistant-turn wrappers: on 2026-09-30 the
  // live DOM exposed the 1475 file card while no assistant node was found for
  // 180 s. Composer, user-turn and dialog copies are excluded; the first card
  // in document order wins among identical names.
  function expectedStepAttachmentCandidates(expectedStep, kind="command") {
    // AGP_K07_TERMINAL_REPLY_FILE_V1: a terminal answer is the file card
    // <expectedStep>_agp_terminal.json, with the same identity rules.
    const pattern = kind === "terminal"
      ? new RegExp(`^${Number(expectedStep)}_agp_terminal\\.json(?:[?#]|$)`)
      : new RegExp(`^${Number(expectedStep)}_[^\\s/]+\\.py(?:[?#]|$)`, "i");
    const unique = new Map();
    for (const anchor of document.querySelectorAll('a[href], button, [role="button"]')) {
      if (anchor.closest('form, [data-message-author-role="user"], [role="dialog"], [aria-modal="true"]')) continue;
      // AGP_COMPOSER_RESOLVER_V1: ChatGPT can keep a previous conversation in
      // a hidden/inert container after "new chat" (live 2026-09-30: step 1480
      // of the old chat was reported visible on https://chatgpt.com/).
      if (anchor.closest('[inert], [aria-hidden="true"]')) continue;
      const anchorRect = anchor.getBoundingClientRect();
      if (!(anchorRect.width > 0 && anchorRect.height > 0)) continue;
      const item = pythonAttachmentRow(anchor);
      if (!pattern.test(String(item.name || ""))) continue;
      if (!(item.href || item.isButton)) continue;
      const key = `${item.href}\n${item.name}`;
      if (!unique.has(key)) unique.set(key, item);
    }
    return Array.from(unique.values());
  }

  function expectedStepFileVisible(step) {
    return expectedStepAttachmentCandidates(step).length > 0 ||
      expectedStepAttachmentCandidates(step, "terminal").length > 0;
  }

  function expectedStepTerminalCandidates() {
    const step = Number(STATE.nextLocalStep || 0);
    return step > 0 ? expectedStepAttachmentCandidates(step, "terminal") : [];
  }

  // AGP_K07_COMMAND_FILE_INGRESS_989
  function assistantPythonAttachmentCandidates() {
    const expectedStepIdentity = Number(STATE.nextLocalStep || 0);
    if (expectedStepIdentity > 0) {
      return expectedStepAttachmentCandidates(expectedStepIdentity);
    }
    const nodes = assistantMessageNodes();
    if (!nodes.length) return [];
    const baselineNames = new Set(STATE.assistantBaselineAttachmentNames || []);
    // Use the same identity-aware selection as assistant text extraction. The
    // ChatGPT DOM can contain virtualized or stale assistant nodes alongside
    // the currently observed response.
    const baselineIds = assistantBaselineIds();
    const assistant = [...nodes].reverse().find(node => {
      const id = String(node.getAttribute("data-message-id") || "");
      if (id && baselineIds.has(id)) return false;
      return node.querySelector('a[href$=".py"], button[aria-label$=".py"], button, [role="button"]');
    }) || selectedAssistantMessageNode();
    if (!assistant) return [];
    // ChatGPT currently renders the attachment card as a plain button with
    // visible filename text. Keep links and labelled controls supported, but
    // also inspect ordinary buttons so the real file-card DOM is covered.
    const rows = Array.from(assistant.querySelectorAll(
      "a[href], button[aria-label$=\".py\"], button, [role=\"button\"]"
    ))
      .map(anchor => {
        const href = String(anchor.href || anchor.getAttribute("href") || "").trim();
        const label = String(
          anchor.getAttribute("download") ||
          anchor.getAttribute("aria-label") ||
          anchor.getAttribute("title") ||
          anchor.textContent ||
          ""
        ).trim();
        const match = label.match(/(?:^|[\s/])([^\s/]+\.py(?:[?#][^\s]*)?)/i);
        const name = match ? match[1] : label.split("/").pop().trim();
        let row = anchor;
        let downloadNode = null;
        for (let depth = 0; depth < 8 && row; depth += 1, row = row.parentElement) {
          downloadNode = row.querySelector('button[aria-label="Datei herunterladen"], button[aria-label="Download"]');
          if (downloadNode) break;
        }
        return {href, name, isButton: anchor.tagName === "BUTTON", node: anchor, downloadNode};
      })
      .filter(item => (
        /\.py(?:$|[?#\s])/i.test(item.name || "") ||
        /\.py(?:$|[?#])/i.test(item.href || "")
      ))
      .filter(item =>
        (item.href || item.isButton)
      );
    const unique = new Map();
    for (const row of rows) unique.set(`${row.href}\n${row.name}`, row);
    const candidates = Array.from(unique.values());
    const expectedStep = Number(STATE.nextLocalStep || 0);
    if (expectedStep > 0) {
      return candidates.filter(item => {
        const match = String(item.name || "").match(/^(\d+)_/);
        return match && Number(match[1]) === expectedStep;
      });
    }
    // A stable message id does not prove that the attachment is new: an
    // in-flight assistant response can materialize after the baseline was
    // captured, and ChatGPT may recycle or expose that old response again.
    // The filename is therefore a second, mandatory turn boundary. A remote
    // retry must receive a new filename instead of being executed locally as
    // a fresh step.
    if (baselineNames.size) {
      return candidates.filter(item => !baselineNames.has(item.name));
    }
    return candidates;
  }

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
    const pythonLabels = Array.from(document.querySelectorAll('a[href], button, [role="button"]'))
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
      role_assistant:count('[data-message-author-role="assistant"]'),
      role_user:count('[data-message-author-role="user"]'),
      role_any:count("[data-message-author-role]"),
      message_ids:count("[data-message-id]"),
      turn_articles:count('article[data-testid^="conversation-turn"]'),
      testid_turns:count('[data-testid*="conversation-turn"]'),
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

  function readableAttachmentPreview(filename) {
    const expectedName = String(filename || "").trim().toLowerCase();
    const candidates = Array.from(document.querySelectorAll(
      '[role="dialog"] .cm-content[role="textbox"], ' +
      '[role="dialog"] .cm-content, .cm-content[role="textbox"], ' +
      '[role="textbox"][aria-label]'
    ));
    return candidates.find(candidate => {
      const content = String(candidate.innerText || candidate.textContent || "").trim();
      if (!content) return false;
      if (candidate.closest('[role="dialog"], [aria-modal="true"]')) return true;
      const label = String(candidate.getAttribute("aria-label") || "").trim().toLowerCase();
      return Boolean(expectedName) && (label === expectedName || label.endsWith(`/${expectedName}`));
    }) || null;
  }

  function attachmentPreviewContainer(preview) {
    let current = preview;
    for (let depth = 0; current && depth < 12; depth += 1, current = current.parentElement) {
      const buttons = Array.from(current.querySelectorAll("button"));
      const labels = buttons.map(button => String(
        button.getAttribute("aria-label") || button.textContent || button.title || ""
      ).trim().toLowerCase());
      const hasClose = labels.some(label => label === "close" || label === "schließen");
      const hasDownload = labels.some(label => label === "download" || label === "herunterladen");
      if (hasClose && hasDownload) return current;
    }
    return preview ? preview.closest('[role="dialog"], [aria-modal="true"]') : null;
  }

  function attachmentPreviewDownloadButton(preview) {
    const dialog = attachmentPreviewContainer(preview);
    const root = dialog || preview;
    if (!root) return null;
    return Array.from(root.querySelectorAll("button")).find(button => {
      const label = String(
        button.getAttribute("aria-label") || button.textContent || button.title || ""
      ).trim().toLowerCase();
      return label === "download" || label === "herunterladen" ||
        label === "datei herunterladen";
    }) || null;
  }

  async function materializeDownloadedAttachment(attachment, downloadNode) {
    if (!downloadNode || !downloadNode.isConnected) {
      throw new Error("K07 assistant attachment has no authoritative download control");
    }
    const armed = await chrome.runtime.sendMessage({
      type:"AGP_K07_ARM_COMMAND_FILE_DOWNLOAD",
      filename:attachment.name
    });
    if (!armed || armed.ok !== true) {
      throw new Error(armed && armed.error ? String(armed.error) : "K07 browser download could not be armed");
    }
    downloadNode.click();
    const downloaded = await chrome.runtime.sendMessage({
      type:"AGP_K07_WAIT_COMMAND_FILE_DOWNLOAD",
      filename:attachment.name
    });
    if (!downloaded || downloaded.ok !== true || !downloaded.download_path) {
      throw new Error(downloaded && downloaded.error ? String(downloaded.error) : "K07 browser download did not complete");
    }
    const fetched = await api("/v1/file-loop/download", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({filename:attachment.name, download_path:downloaded.download_path})
    });
    if (!fetched || fetched.ok !== true || fetched.stage !== "COMMAND_FILE_FETCHED" || typeof fetched.content !== "string" || !fetched.content.trim()) {
      throw new Error("K07 downloaded command file could not be materialized");
    }
    // AGP_K07_DOWNLOAD_PROVENANCE_V1: the bytes the bridge read must be the
    // bytes Chrome reported for this exact download item.
    const browserBytes = Number(downloaded.download_bytes || 0);
    if (browserBytes > 0 && Number(fetched.bytes || 0) !== browserBytes) {
      throw new Error(`K07 download size mismatch: browser ${browserBytes} bytes, bridge ${Number(fetched.bytes || 0)} bytes`);
    }
    await clientEvent("K07_ATTACHMENT_DOWNLOAD_USED", {
      filename:attachment.name,
      download_path:downloaded.download_path,
      download_id:downloaded.download_id || null,
      download_bytes:Number(downloaded.download_bytes || 0),
      chars:fetched.content.length
    });
    return {
      ok:true,
      stage:"COMMAND_FILE_FETCHED",
      filename:attachment.name,
      href:`chatgpt://assistant-download/${encodeURIComponent(attachment.name)}`,
      content:fetched.content,
      content_type:String(fetched.content_type || "text/x-python"),
      chars:fetched.content.length,
      download_sha256:String(fetched.sha256 || ""),
      download_id:Number.isInteger(downloaded.download_id) ? downloaded.download_id : null
    };
  }

  // AGP_DOWNLOAD_HYGIENE_V1: after the bridge has persisted an accepted file in
  // the repository, the browser copy in ~/Downloads is removed. Rejected work
  // orders keep their browser copy (the bridge records only the reason).
  async function forgetBrowserDownload(fetched) {
    if (!fetched || !Number.isInteger(fetched.download_id)) return;
    try {
      const removed = await chrome.runtime.sendMessage({
        type:"AGP_K07_FORGET_DOWNLOAD",
        download_id:fetched.download_id,
        filename:fetched.filename
      });
      await clientEvent("K07_BROWSER_DOWNLOAD_REMOVED", {
        filename:fetched.filename,
        download_id:fetched.download_id,
        stage:String(removed && removed.stage || ""),
        ok:Boolean(removed && removed.ok)
      });
    } catch (_) {}
  }

  async function readAssistantButtonAttachment(attachment) {
    const button = attachment && attachment.node;
    if (!button || !button.isConnected) {
      throw new Error("K07 assistant attachment button is no longer connected");
    }
    if (attachment.downloadNode && attachment.downloadNode.isConnected) {
      const downloaded = await materializeDownloadedAttachment(attachment, attachment.downloadNode);
      const target = composer();
      if (target && target.isConnected) {
        const activeBefore = document.activeElement;
        if (activeBefore && activeBefore !== target && typeof activeBefore.blur === "function") {
          activeBefore.blur();
        }
        if (typeof window !== "undefined" && typeof window.focus === "function") window.focus();
        if (typeof target.focus === "function") target.focus();
      }
      return downloaded;
    }
    button.click();
    const deadline = Date.now() + 45000;
    let preview = null;
    while (Date.now() < deadline) {
      preview = readableAttachmentPreview(attachment.name);
      const previewText = preview
        ? String(preview.innerText || preview.textContent || "")
        : "";
      if (preview && previewText.trim()) break;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    if (!preview) {
      const unavailableDialog = document.querySelector('[role="dialog"], [aria-modal="true"]');
      const closeUnavailable = unavailableDialog && Array.from(unavailableDialog.querySelectorAll('button')).find(candidate => {
        const label = String(candidate.getAttribute("aria-label") || candidate.textContent || "").trim().toLowerCase();
        return label === "schließen" || label === "close";
      });
      if (closeUnavailable) closeUnavailable.click();
      else if (unavailableDialog) {
        document.dispatchEvent(new KeyboardEvent("keydown", {key:"Escape", code:"Escape", bubbles:true, cancelable:true}));
      }
      throw new Error("K07 assistant attachment preview did not become readable");
    }
    const dialog = attachmentPreviewContainer(preview);
    const previewDownload = attachmentPreviewDownloadButton(preview);
    let downloadedContent = null;
    let downloadError = null;
    if (previewDownload) {
      try {
        downloadedContent = await materializeDownloadedAttachment(attachment, previewDownload);
      } catch (error) {
        downloadError = error;
      }
    } else {
      downloadError = new Error("K07 assistant attachment preview is not an authoritative payload; browser download is required");
    }
    const normalizedLabel = value => String(value || "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
    const closeCandidates = dialog
      ? Array.from(dialog.querySelectorAll(
        '[data-testid="close-button"], ' +
        'button[aria-label="Vollbildmodus beenden"], ' +
        'button[aria-label="Exit full screen"], ' +
        'button[aria-label="Schließen"], button[aria-label="Close"], button'
      ))
      : [];
    const active = document.activeElement;
    if (active && active.tagName === "BUTTON" && dialog && dialog.contains(active)) {
      closeCandidates.unshift(active);
    }
    const close = closeCandidates.find(button => {
      const label = normalizedLabel(
        button.getAttribute("aria-label") || button.textContent || button.title
      );
      return label === "ok" || label === "close" || label === "schließen" ||
        label === "exit full screen" || label === "vollbildmodus beenden" ||
        button.getAttribute("data-testid") === "close-button";
    });
    let closeMethod = "none";
    if (close) {
      close.click();
      closeMethod = normalizedLabel(close.textContent) === "ok" ? "dialog_ok" : "dialog_control";
    } else {
      document.dispatchEvent(new KeyboardEvent("keydown", {
        key:"Escape", code:"Escape", bubbles:true, cancelable:true
      }));
      closeMethod = "escape";
    }
    const closeDeadline = Date.now() + 3000;
    while (Date.now() < closeDeadline) {
      const stillOpen = dialog && dialog.isConnected && (() => {
        const rect = dialog.getBoundingClientRect();
        const style = getComputedStyle(dialog);
        return rect.width > 0 && rect.height > 0 &&
          style.display !== "none" && style.visibility !== "hidden";
      })();
      if (!stillOpen) break;
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    const stillOpen = dialog && dialog.isConnected && (() => {
      const rect = dialog.getBoundingClientRect();
      const style = getComputedStyle(dialog);
      return rect.width > 0 && rect.height > 0 &&
        style.display !== "none" && style.visibility !== "hidden";
    })();
    if (stillOpen) {
      throw new Error("K07 assistant attachment preview did not close");
    }

    // Closing the preview can leave focus on its now-detached OK button.
    // Restore and verify composer ownership before the background transport
    // attaches the result files and sends the recovery prompt.
    const focusDeadline = Date.now() + 1500;
    let focusEvidence = null;
    while (Date.now() < focusDeadline) {
      const target = composer();
      if (target && target.isConnected) {
        const activeBefore = document.activeElement;
        if (activeBefore && activeBefore !== target && typeof activeBefore.blur === "function") {
          activeBefore.blur();
        }
        if (typeof window.focus === "function") window.focus();
        if (typeof target.focus === "function") target.focus();
        focusEvidence = {
          focused: document.activeElement === target,
          active_tag: document.activeElement ? document.activeElement.tagName : "",
          active_id: document.activeElement ? document.activeElement.id : "",
          composer_tag: target.tagName,
          composer_id: target.id || ""
        };
        if (focusEvidence.focused) break;
      }
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    if (!focusEvidence || !focusEvidence.focused) {
      throw new Error("K07 composer focus could not be restored after attachment preview");
    }
    await clientEvent("K07_ATTACHMENT_PREVIEW_CLOSED", {
      filename:attachment.name,
      method:closeMethod,
      composer_focus:focusEvidence
    });
    if (downloadError) throw downloadError;
    return downloadedContent;
  }

  async function fetchSingleAssistantPythonAttachment(candidates = assistantPythonAttachmentCandidates()) {
    if (candidates.length !== 1) {
      throw new Error(
        `expected exactly one assistant remote-file attachment; observed ${candidates.length}`
      );
    }
    const attachment = candidates[0];
    if (!attachment.href && attachment.isButton) {
      return readAssistantButtonAttachment(attachment);
    }
    const response = await chrome.runtime.sendMessage({
      type:"AGP_K07_COMMAND_FILE_FETCH",
      href:attachment.href,
      filename:attachment.name
    });
    if (!response || response.ok !== true || response.stage !== "COMMAND_FILE_FETCHED") {
      throw new Error(
        response && response.error
          ? String(response.error)
          : "assistant .py attachment could not be materialized"
      );
    }
    return response;
  }

  // AGP_K07_TERMINAL_REPLY_FILE_V1: materialize the terminal file through the
  // same download/provenance path and let the bridge decide the final state.
  async function submitAssistantTerminalReply(candidates) {
    const fetched = await fetchSingleAssistantPythonAttachment(candidates);
    const result = await api("/v1/file-loop/terminal", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({
        filename:fetched.filename,
        content:fetched.content,
        download_sha256:fetched.download_sha256 || undefined
      })
    });
    // AGP_CI_GREEN_COMPLETION_V1: the Cockpit may reject a remote DONE (CI not
    // green) and continue the task with a prompt instead of ending it.
    const continued = result && result.terminal === false && String(result.state || "") === "CONTINUE" &&
      typeof result.prompt === "string" && result.prompt.length > 0;
    if (!result || (!continued && (result.terminal !== true ||
        !["DONE", "NEEDS_HUMAN"].includes(String(result.state || ""))))) {
      throw new Error("K07 terminal-reply bridge response incomplete");
    }
    await clientEvent("K07_TERMINAL_REPLY_OBSERVED", {
      filename:fetched.filename,
      state:String(result.state),
      remote_state:String(result.remote_state || ""),
      authority:String(result.authority || ""),
      replayed:Boolean(result.replayed)
    });
    void forgetBrowserDownload(fetched);
    return result;
  }

  async function submitAssistantCommandFile(runGeneration = STATE.runGeneration) {
    await clientEvent("K07_FILE_INGRESS_REQUESTED", {
      stage:"FETCH_ATTACHMENT",
      message_id:lastAssistantMessageId()
    });
    const fetched = await fetchSingleAssistantPythonAttachment();
    await clientEvent("K07_FILE_INGRESS_ATTACHMENT_FETCHED", {
      filename:fetched.filename,
      chars:Number(fetched.chars || String(fetched.content || "").length)
    });
    const result = await api(
      "/v1/file-loop/command",
      {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          filename:fetched.filename,
          content:fetched.content,
          href:fetched.href,
          download_sha256:fetched.download_sha256 || undefined,
          message_id:lastAssistantMessageId()
        })
      }
    );
    const terminal = Boolean(result && result.terminal === true);
    // AGP_CORRECTABLE_REJECTION_V1: the work order broke the command authority,
    // was not executed and the remote side gets a correction prompt.
    const rejectedForCorrection = Boolean(result && result.terminal === false &&
      String(result.state || "") === "CONTINUE" && typeof result.prompt === "string" && result.prompt);
    if (rejectedForCorrection) {
      await clientEvent("K07_WORK_ORDER_REJECTED_FOR_CORRECTION", {
        filename:fetched.filename,
        next_step:Number(result.next_step || 0)
      });
      return result;
    }
    if (
      !result ||
      (result.state !== "COMMAND_FILE" && !terminal) ||
      (!terminal && (typeof result.result_file !== "string" || !result.result_file)) ||
      (!terminal && result.held !== true &&
        (result.replayed !== true || result.delivery_pending === true) &&
        (typeof result.prompt !== "string" || !result.prompt))
    ) {
      throw new Error("K07 command-file bridge response incomplete");
    }
    await clientEvent("K07_FILE_INGRESS_ACCEPTED", {
      filename:fetched.filename,
      state:String(result.state || ""),
      step:Number(result.step || 0),
      terminal,
      replayed:Boolean(result.replayed)
    });
    void forgetBrowserDownload(fetched);
    // AGP_K07_ADVANCE_STEP_AFTER_DELIVERY_V1: the expected step is the
    // identity of the awaited remote response. It advances only when the
    // result reached the remote side (or delivery is not required). Advancing
    // earlier hid the current card after a failed delivery (live 2026-09-30:
    // expected 1477 while 1476 still needed re-delivery).
    const advanceExpectedStep = () => {
      if (Number(result.next_step || 0) > 0) {
        STATE.nextLocalStep = Number(result.next_step);
      }
    };
    // AGP_K07_DELIVERY_STATE_V1: a replay whose earlier delivery was never
    // confirmed is re-delivered; a confirmed one is suppressed. A result held
    // by operator PAUSE is not sent now; it is re-delivered after resume.
    if (result.held === true) {
      return result;
    }
    if (terminal) {
      advanceExpectedStep();
      return result;
    }
    if (result.replayed === true && result.delivery_pending !== true) {
      advanceExpectedStep();
      return result;
    }
    if (!STATE.running || STATE.runGeneration !== runGeneration) {
      await clientEvent("K07_CONTINUATION_SUPPRESSED_BY_GENERATION", {
        step:Number(result.step || 0),
        result_sha256:result.result_sha256 || null
      });
      return Object.assign({}, result, {delivery_skipped:true});
    }
    const upcomingStep = Number(result.next_step || 0);
    if (upcomingStep > 0 && expectedStepFileVisible(upcomingStep)) {
      // The continuation would ask for a number that is already visible;
      // its stale card would be consumed as the next response. Fail closed.
      const currentExpectedStep = STATE.nextLocalStep;
      await reserveRemoteStep("visible-unmaterialized-remote-attachment", upcomingStep);
      STATE.nextLocalStep = currentExpectedStep;
      throw new Error(`K07 next step ${upcomingStep} is already visible in the conversation; continuation not sent`);
    }
    const nextBaseline = snapshotAssistantBaseline();
    // AGP_K07_RESULT_CONTINUATION_CALL_991
    const continuation = await chrome.runtime.sendMessage({
      type:"AGP_K07_RESULT_CONTINUATION",
      result_file:result.result_file,
      output_file:result.output_file || null,
      prompt:result.prompt,
      cycle_id:result.cycle_id || null,
      result_sha256:result.result_sha256 || null
    });
    if (!continuation || continuation.ok !== true || continuation.stage !== "RESULT_ATTACHED_AND_CONTINUATION_SENT") {
      throw new Error(continuation && continuation.error ? String(continuation.error) : "result continuation transport failed");
    }
    applyAssistantBaseline(nextBaseline);
    advanceExpectedStep();
    if (result.completion_pending !== true) {
      try {
        await api("/v1/file-loop/delivery-ack", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({cycle_id:result.cycle_id, result_sha256:result.result_sha256})
        });
      } catch (ackError) {
        // The continuation is committed; a later remote command implies
        // delivery. Never resend because only the acknowledgement failed.
        await clientEvent("K07_DELIVERY_ACK_FAILED", {
          result_sha256:result.result_sha256 || null,
          error:String(ackError && ackError.message ? ackError.message : ackError)
        });
      }
    }
    if (result.completion_pending === true) {
      const completed = await api("/v1/file-loop/result-delivered", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({cycle_id:result.cycle_id, result_sha256:result.result_sha256})
      });
      if (completed.state !== "DONE" || completed.terminal !== true) {
        throw new Error("handoff completion acknowledgement rejected");
      }
      return Object.assign({}, result, completed);
    }
    return result;
  }

  function composer() {
    const resolved = typeof agpResolveComposer === "function" ? agpResolveComposer() : null;
    if (resolved) return resolved;
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

      if (requestedGeneration > 0) {
        chrome.runtime.sendMessage({
          type:"AGP_REFRESH_INTEGRATION",
          generation:requestedGeneration
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
    return agpNativeMessageSnapshot(typeof agpResolveComposer === "function" ? agpResolveComposer : undefined).messages.map(message => message.text).filter(Boolean);
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

  function normalizeRenderedUserTurnText(text) {
    return typeof agpNormalizeUserTurnText === "function"
      ? agpNormalizeUserTurnText(text)
      : normalizeObservedMessageText(text);
  }

  function renderedUserTurnMatches(observed, expected) {
    if (typeof agpRenderedUserTurnMatches === "function") {
      return agpRenderedUserTurnMatches(observed, expected);
    }
    const observedText = normalizeRenderedUserTurnText(observed);
    const expectedText = normalizeRenderedUserTurnText(expected);
    if (!observedText || !expectedText) return false;
    if (observedText === expectedText) return true;
    const minimumPrefix = 240;
    const collapsedText = observedText.replace(/\s*(?:…|\.{3})$/, "").trim();
    if (collapsedText.length >= minimumPrefix && expectedText.startsWith(collapsedText)) {
      return true;
    }
    return observedText.length >= minimumPrefix &&
      observedText.slice(0, minimumPrefix) === expectedText.slice(0, minimumPrefix);
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

  function isKnownCockpitDraft(text) {
    const value = normalizeObservedMessageText(text);
    return /^AGP-SEND-[0-9a-f]{16}(?:\s|$)/.test(value) ||
      value.includes("AGP COCKPIT MISSION — FIRST SINGLE STEP") ||
      value.includes("Attached is the result file for the command you gave me.") ||
      value.includes("The attached local execution evidence reports a FAILED command-file step.");
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
    const expected = normalizeRenderedUserTurnText(prompt);
    const assistantBefore = normalizeObservedMessageText(beforeAssistantText);
    const composerBefore = normalizeObservedMessageText(beforeComposerText);
    let provisionalComposerEvidence = "";
    let generationStartedObserved = false;

    // The nonce was generated for this send, so its pre-send occurrence count
    // outside the composer is zero by construction. Reconciliation may start
    // after the native commit already rendered, so it must not re-baseline.
    const commitMarker = commitMarkerOf(prompt);
    const markerBaseline = 0;
    let markerStreak = 0;

    for (let i = 0; i < 60; i += 1) {
      await new Promise(resolve => setTimeout(resolve, 250));

      markerStreak = commitMarker && commitMarkerOutsideComposer(commitMarker) > markerBaseline
        ? markerStreak + 1
        : 0;
      if (markerStreak >= 2) {
        return {confirmed:true, via:"commit_marker"};
      }

      const after = visibleUserMessages();
      if (after.length > beforeCount) {
        const newest = after[after.length - 1];
        if (renderedUserTurnMatches(newest, expected)) {
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
      "Do not change the chosen executable during format repair and do not introduce a shell wrapper. " +
      "No Markdown fences, no commentary, no leading or trailing prose. " +
      `Automatic format-repair attempt ${attempt}/${AGP_MAX_FORMAT_REPAIR_ATTEMPTS}.`
    );
  }


  // AGP_K07_SEND_COMMIT_NONCE_V1
  // Every native send carries a fresh, unguessable first line. A persistent
  // occurrence of that nonce outside the composer after the send boundary is
  // decisive commit evidence that does not depend on ChatGPT's user-turn
  // wrappers, message ids, rendered Markdown projection, virtualization
  // window, or conversation URL.
  const AGP_COMMIT_MARKER_PATTERN = /^AGP-SEND-[0-9a-f]{16}$/;

  function agpCommitMarker() {
    const bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    return "AGP-SEND-" + Array.from(bytes, byte => byte.toString(16).padStart(2, "0")).join("");
  }

  function commitMarkerOf(prompt) {
    const firstLine = String(prompt || "").split("\n", 1)[0].trim();
    return AGP_COMMIT_MARKER_PATTERN.test(firstLine) ? firstLine : "";
  }

  function commitMarkerOutsideComposer(marker) {
    if (!marker) return 0;
    const count = value => String(value || "").split(marker).length - 1;
    const el = composer();
    const inBody = el && !(el instanceof HTMLTextAreaElement)
      ? count(el.innerText || el.textContent || "")
      : 0;
    const bodyText = document.body ? (document.body.innerText || document.body.textContent || "") : "";
    return Math.max(0, count(bodyText) - inBody);
  }

  // AGP_NATIVE_RETRY_OWNED_DRAFT_V1
  // Live 2026-10-05: attempt 1 inserted the prompt but the editor model was not
  // verified; attempt 2 then refused because the composer was not empty, so the
  // bounded retry could never succeed and the real cause was masked. Before a
  // retry, clear exactly this send's own draft (fresh AGP-SEND nonce or the
  // exact prompt). Any other content stays protected: fail closed.
  async function clearOwnedDraftBeforeRetry(prompt, commitMarker, attempt) {
    const staged = normalizeObservedMessageText(observedComposerText());
    if (!staged) return;
    const expected = normalizeObservedMessageText(prompt);
    const marker = String(commitMarker || "");
    const owned = staged === expected ||
      (AGP_COMMIT_MARKER_PATTERN.test(marker) &&
        (staged === marker || staged.startsWith(marker + " ")));
    if (!owned) {
      throw new Error(
        "browser-native retry found foreign composer content; refusing to overwrite"
      );
    }
    const el = composer();
    if (!el) throw new Error("browser-native retry composer disappeared");
    setComposerText(el, "");
    const deadline = Date.now() + 2000;
    while (normalizeObservedMessageText(observedComposerText()) && Date.now() < deadline) {
      await sleep(50);
    }
    if (normalizeObservedMessageText(observedComposerText())) {
      throw new Error("browser-native retry could not clear its own draft");
    }
    await clientEvent("NATIVE_RETRY_OWNED_DRAFT_CLEARED", {
      attempt,
      chars:staged.length
    });
  }

  async function sendPromptNative(prompt) {
    const commitMarker = agpCommitMarker();
    prompt = `${commitMarker}\n${String(prompt || "")}`;
    const transport = createSendTransport(prompt);

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
        if (!isKnownCockpitDraft(stagedComposerText)) {
          throw new Error(
            "browser-native transport found non-empty foreign composer content; refusing to overwrite"
          );
        }
        setComposerText(composer(), "");
        await clientEvent("NATIVE_STALE_OWNED_COMPOSER_RECOVERED", {
          chars:stagedComposerText.length,
          ownership:"known_cockpit_prompt_after_reload"
        });
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

    let nativeAck = null;
    for (let attempt = 1; attempt <= 2; attempt += 1) {
      if (attempt > 1) await clearOwnedDraftBeforeRetry(prompt, commitMarker, attempt);
      nativeAck = await nativeTransport.submit(prompt, {attempt, commitMarker});
      if (String(nativeAck.stage || "") !== "COMPOSER_MODEL_NOT_VERIFIED") break;
      await clientEvent("COMPOSER_MODEL_NOT_VERIFIED", {
        attempt,
        model: nativeAck.model || null
      });
      if (attempt < 2) await sleep(250);
    }

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

    if (String(nativeAck.stage || "") === "COMPOSER_MODEL_NOT_VERIFIED") {
      const error = new Error("COMPOSER_MODEL_NOT_VERIFIED after bounded refocus retry");
      error.code = "COMPOSER_MODEL_NOT_VERIFIED";
      await clientEvent("COMPOSER_MODEL_RECOVERY_EXHAUSTED", {
        attempts:2,
        model:nativeAck.model || null
      });
      throw error;
    }

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
      const reconciliation = await waitForSentUserMessage(
        prompt,
        beforeMessages,
        beforeAssistantText,
        observedComposerText(),
        beforeGenerationActive
      );
      if (reconciliation.confirmed) {
        PENDING_SEND_TRANSPORT = null;
        transport.acknowledgement = reconciliation;
        transport.transition(SEND_TRANSPORT.ACCEPTED_LATE, {
          via:"reconciliation",
          native_stage:"USER_TURN_INDETERMINATE"
        });
        await clientEvent("ACCEPTED_LATE", {via:"reconciliation", evidence:reconciliation.via || ""});
        return;
      }
      // An empty composer is composer mutation, not send acceptance
      // (COMMUNICATION_PROTOCOL.md). Without decisive commit evidence the
      // send stays indeterminate and fails closed.
      const reservedStep = Number(STATE.nextLocalStep || 0);
      if (reservedStep > 0) {
        try {
          await reserveRemoteStep("native-send-indeterminate", reservedStep);
        } catch (reserveError) {
          await clientEvent("K07_REMOTE_STEP_RESERVE_FAILED", {
            step:reservedStep,
            error:String(reserveError && reserveError.message ? reserveError.message : reserveError)
          });
        }
      }
      await clientEvent("SEND_INDETERMINATE", {
        reconciliation:"not_confirmed",
        commit_marker_outside_composer:commitMarkerOutsideComposer(commitMarker),
        native_diagnostics:nativeAck.diagnostics || null,
        provisional:reconciliation.provisional || "",
        generation_started_observed:Boolean(reconciliation.generation_started_observed),
        native_after_summary:nativeAck.after && {
          user_message_count:Number(nativeAck.after.user_message_count || 0),
          exact_user_message_found:Boolean(nativeAck.after.exact_user_message_found),
          composer_chars:String(nativeAck.after.composer_text || "").length,
          generation_active:Boolean(nativeAck.after.generation_active)
        }
      });
      STATE.lastEvent = "SEND_INDETERMINATE";
      STATE.note = "Prompt nicht reconcilierbar bestätigt; kein weiterer Turn";
      throw new Error("SEND_INDETERMINATE: user turn not reconciled");
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

  // Used by the native transport retry and stale-draft recovery; it was never
  // defined (ReferenceError "sleep is not defined", live 1510 and 1518).
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  async function sendPrompt(prompt) {
    let failure = null;
    try {
      return await sendPromptNative(prompt);
    } catch (error) {
      failure = error;
    }
    // AGP_SEND_NOT_READY_RETRY_V1 (live 2026-10-02, twice at "Arbeit
    // beginnen"): nothing was sent; log what the composer offered, clear our
    // own text (attachments of this send stay) and try once more after 15 s.
    const rejected = failure && failure.response;
    if (rejected && rejected.stage === "SEND_BUTTON_NOT_READY") {
      await clientEvent("SEND_BUTTON_NOT_READY_DIAGNOSED", {
        form_buttons:Array.isArray(rejected.form_buttons) ? rejected.form_buttons : [],
        send_diagnostics:Array.isArray(rejected.send_diagnostics) ? rejected.send_diagnostics.slice(0, 8) : [],
        readiness_wait_ms:Number(rejected.readiness_wait_ms || 0)
      });
      let cleaned = null;
      try {
        cleaned = await chrome.runtime.sendMessage({type:"AGP_K07_CLEAN_COMPOSER", files:false});
      } catch (_) {
        cleaned = null;
      }
      if (cleaned && cleaned.ok === true) {
        await sleep(15000);
        await clientEvent("SEND_RETRY_AFTER_NOT_READY", {clean_stage:String(cleaned.stage || "")});
        try {
          return await sendPromptNative(prompt);
        } catch (error) {
          failure = error;
        }
      }
    }
    return await sendPromptFailed(failure, prompt);
  }

  async function sendPromptFailed(error, prompt) {
    {
      if (error && error.code === "COMPOSER_MODEL_NOT_VERIFIED") {
        STATE.lastTransportFailureClass = "COMPOSER_MODEL_NOT_VERIFIED";
        await clientEvent("COMPOSER_MODEL_RECOVERY_EXHAUSTED", {
          message:String(error.message || error)
        });
      }
      await clientEvent("NATIVE_TRANSPORT_FAILED", {
        message:String(error && error.message ? error.message : error),
        failure_class:STATE.lastTransportFailureClass || ""
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
      "Every work order MUST execute at least one agentic-kit command during its real run; the Kit is the command authority. Use only commands from the agentic-kit command digest attached to the mission start, prefer the most comprehensive orchestrator command, and never run git push, git fetch or git pull. Other allowed tools such as git may only be used in addition. Record every agentic-kit command's argv, returncode, stdout and stderr (tails) in the return bundle. Work-order shape, checked locally before anything runs: a main() function and an if __name__ == '__main__': guard; a module constant STEP equal to the expected local step; a --self-test mode (sys.argv or argparse) that only checks the file itself, runs no command, writes no file and exits 0; the real run writes exactly one JSON return bundle named Download/<STEP>_<topic>_return_bundle.json. Parse the JSON output of every agentic-kit --json command and record its top-level result_status, final_signal, failed_step and next_action separately in the return bundle; a stdout tail alone loses the verdict. Never re-run a command with remote effects to check a result: each continuation carries Cockpit-verified repository facts.",
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
      "Never answer with prose only: the Cockpit reads exactly one attached file per turn."
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
        newest.querySelectorAll("a[href], button, [role=\"button\"]")
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
    const candidates = assistantPythonAttachmentCandidates();
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
        message:String(err)
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
    return Array.from(document.querySelectorAll("form button, [data-testid*='composer'] button"))
      .some(button => !button.disabled && (
        /^(stop|stoppen)\b/i.test(String(button.getAttribute("aria-label") || "").trim()) ||
        /stop/i.test(String(button.getAttribute("data-testid") || ""))));
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
          conversation_url:location.href,
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
          conversation_url:location.href,
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
          conversation_url:location.href,
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
    if (retireIfOrphaned()) return;
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

    const extensionVersion = document.createElement("span");
    extensionVersion.style.fontSize = "11px";
    extensionVersion.style.color = "#b6c8d4";
    extensionVersion.textContent = `v${chrome.runtime.getManifest().version}`;
    extensionVersion.title = `Build ${globalThis.AGP_EXTENSION_BUILD_ID || "unknown"}`;
    head.appendChild(extensionVersion);

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

    // Developer diagnostics remain available through bridge/CLI diagnostics;
    // historical phase controls are intentionally absent from the normal overlay.
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
    // Same count as the Cockpit: the mission's remote turns (not the
    // browser-local send counter, which also counts bootstrap messages).
    const shownTurns = STATE.mission ? Number(STATE.mission.turn_count || 0) : Number(STATE.turns || 0);
    tBig.textContent = `${shownTurns} / ${LIMITS.maxTurns}`;
    turns.appendChild(tBig);

    const progress = document.createElement("div");
    progress.className = "agp-progress";
    const fill = document.createElement("div");
    fill.style.width =
      `${Math.min(100, shownTurns / LIMITS.maxTurns * 100)}%`;
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

    const phaseText = STATE.running && typeof agpMissionPhaseText === "function"
      ? agpMissionPhaseText(STATE, Date.now()) : "";
    if (phaseText) {
      const phase = document.createElement("div");
      phase.className = "agp-note";
      phase.style.marginTop = "4px";
      phase.textContent = phaseText;
      mission.appendChild(phase);
    }

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
    /* AGP_K07_OPERATOR_TRACE_RUNTIME_CONTROL_1137 */
    debug.textContent = "";
    const traceRow = document.createElement("div");
    traceRow.className = "agp-k07-trace-control";
    const traceState = document.createElement("span");
    traceState.textContent = `Last event: ${STATE.lastEvent} | K07 trace: ${STATE.k07DebugTraceEnabled ? "AN" : "AUS"}`;
    traceRow.appendChild(traceState);
    const traceButton = document.createElement("button");
    traceButton.type = "button";
    traceButton.textContent = STATE.k07DebugTraceEnabled ? "Trace aus" : "Trace an";
    traceButton.title = "Schaltet den vorhandenen K07-Debug-Trace; Ereignisse gehen ueber /v1/client-event ins Bridge-Log.";
    traceButton.addEventListener("mousedown", event => event.stopPropagation());
    traceButton.addEventListener("click", async event => {
      event.preventDefault();
      event.stopPropagation();
      setK07DebugTraceEnabled(!STATE.k07DebugTraceEnabled, "overlay");
      render();
    });
    traceRow.appendChild(document.createTextNode(" "));
    traceRow.appendChild(traceButton);
    // K07 trace is a dedicated operator test control. Keep historical
    // diagnostics hidden, but expose this control independently.
    root.appendChild(traceRow);

    if (STATE.errorId) {
      const error = document.createElement("span");
      error.className = "agp-error";
      error.textContent = ` · ${STATE.errorId}`;
      debug.appendChild(error);
    }

    // Historical diagnostics remain hidden unless explicitly opened.
    if (AGP_DIAGNOSTICS_OPEN) {
      root.appendChild(debug);
    }
  }

  render();

  sendHandshake();
  AGP_HANDSHAKE_TIMER = setInterval(sendHandshake, 15000);

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
