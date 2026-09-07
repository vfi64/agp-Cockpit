(() => {
  "use strict";

  const ALLOWED_HOSTS = new Set(["chatgpt.com", "www.chatgpt.com"]);
  let pendingApproval = null;

  function normalizeText(text) {
    return String(text || "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function normalizeConversationUrl(value) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    let url;
    try {
      url = new URL(raw);
    } catch (_) {
      return "";
    }
    if (url.protocol !== "https:" || !ALLOWED_HOSTS.has(url.hostname.toLowerCase())) {
      return "";
    }
    const match = url.pathname.match(/\/c\/([^/?#]+)/);
    if (!match) return "";
    return `https://chatgpt.com/c/${match[1]}`;
  }

  async function sha256(text) {
    const bytes = new TextEncoder().encode(String(text || ""));
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return Array.from(new Uint8Array(digest))
      .map(x => x.toString(16).padStart(2, "0"))
      .join("");
  }

  async function configuredConversationUrl() {
    const cfg = await chrome.storage.local.get({conversationUrl: ""});
    return normalizeConversationUrl(cfg.conversationUrl);
  }

  async function bindConfiguredConversation() {
    const configured = await configuredConversationUrl();
    if (!configured) {
      throw new Error("PHASE5_CONVERSATION_NOT_CONFIGURED");
    }
    const current = normalizeConversationUrl(location.href);
    if (!current || current !== configured) {
      throw new Error(
        `PHASE5_CONVERSATION_MISMATCH configured=${configured} current=${current || "<invalid>"}`
      );
    }
    return Object.freeze({conversationUrl: configured});
  }

  function composer() {
    return (
      document.querySelector("#prompt-textarea") ||
      document.querySelector("textarea") ||
      document.querySelector('[contenteditable="true"]')
    );
  }

  function composerText(el = composer()) {
    if (!el) return "";
    if (el instanceof HTMLTextAreaElement) return String(el.value || "");
    return String(el.innerText || el.textContent || "");
  }

  function setComposerText(el, text) {
    if (!el) throw new Error("PHASE5_COMPOSER_NOT_FOUND");
    if (el instanceof HTMLTextAreaElement) {
      const setter = Object.getOwnPropertyDescriptor(
        HTMLTextAreaElement.prototype,
        "value"
      ).set;
      setter.call(el, text);
      el.dispatchEvent(new Event("input", {bubbles: true}));
      return;
    }
    el.focus();
    el.textContent = text;
    el.dispatchEvent(
      new InputEvent("input", {
        bubbles: true,
        inputType: "insertText",
        data: text
      })
    );
  }

  function generationActive() {
    const selectors = [
      'button[data-testid="stop-button"]',
      'button[data-testid="stop-generating-button"]',
      'button[aria-label*="Stop generating"]',
      'button[aria-label*="Stop response"]',
      'button[aria-label*="Generierung stoppen"]',
      'button[aria-label*="Antwort stoppen"]',
      '[data-is-streaming="true"]'
    ];
    return selectors.some(selector => {
      const el = document.querySelector(selector);
      return Boolean(el && !el.disabled);
    });
  }

  function visibleAssistantNodes() {
    return Array.from(
      document.querySelectorAll('[data-message-author-role="assistant"]')
    ).filter(el => {
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    });
  }

  // AGP_PHASE7_PROTOCOL_TEXT_EXTRACTION_259
  function extractSingleProtocolFrame(text, { includeControl = false } = {}) {
    const value = String(text || "").trim();
    const pairs = [
      ["AGP_COCKPIT_ACTION_BEGIN", "AGP_COCKPIT_ACTION_END"],
      ["AGP_COCKPIT_RESULT_BEGIN", "AGP_COCKPIT_RESULT_END"],
      ...(includeControl ? [["AGP_COCKPIT_CONTROL_BEGIN", "AGP_COCKPIT_CONTROL_END"]] : [])
    ];
    const matches = [];
    for (const [begin, end] of pairs) {
      const start = value.indexOf(begin);
      if (start < 0) continue;
      const secondStart = value.indexOf(begin, start + begin.length);
      const finish = value.indexOf(end, start + begin.length);
      if (secondStart >= 0 || finish < 0 || value.indexOf(end, finish + end.length) >= 0) {
        throw new Error("PHASE7_PROTOCOL_FRAME_AMBIGUOUS");
      }
      matches.push(value.slice(start, finish + end.length).trim());
    }
    if (matches.length === 0) return value;
    if (matches.length !== 1) throw new Error("PHASE7_PROTOCOL_FRAME_AMBIGUOUS");
    return matches[0];
  }

  async function currentAssistantSnapshot() {
    const binding = await bindConfiguredConversation();
    if (generationActive()) {
      throw new Error("PHASE5_ASSISTANT_STILL_STREAMING");
    }
    const nodes = visibleAssistantNodes();
    if (!nodes.length) {
      throw new Error("PHASE5_ASSISTANT_NOT_FOUND");
    }
    const observedText = String(
      nodes[nodes.length - 1].innerText ||
      nodes[nodes.length - 1].textContent ||
      ""
    ).trim();
    const text = extractSingleProtocolFrame(observedText);
    if (!text) throw new Error("PHASE5_ASSISTANT_EMPTY");
    const fingerprint = await sha256(`${binding.conversationUrl}\n${text}`);
    return Object.freeze({
      conversationUrl: binding.conversationUrl,
      text,
      fingerprint
    });
  }

  async function waitForCompletedAssistant({
    afterFingerprint = "",
    timeoutMs = 30000,
    pollMs = 250,
    stablePolls = 3
  } = {}) {
    const deadline = Date.now() + timeoutMs;
    let candidate = "";
    let candidateText = "";
    let stable = 0;

    while (Date.now() < deadline) {
      await bindConfiguredConversation();

      if (generationActive()) {
        candidate = "";
        candidateText = "";
        stable = 0;
        await new Promise(resolve => setTimeout(resolve, pollMs));
        continue;
      }

      try {
        const snapshot = await currentAssistantSnapshot();
        if (snapshot.fingerprint === afterFingerprint) {
          candidate = "";
          candidateText = "";
          stable = 0;
        } else if (snapshot.fingerprint !== candidate) {
          candidate = snapshot.fingerprint;
          candidateText = snapshot.text;
          stable = 1;
        } else {
          stable += 1;
        }

        if (candidate && stable >= stablePolls) {
          return Object.freeze({
            conversationUrl: snapshot.conversationUrl,
            text: candidateText,
            fingerprint: candidate,
            stablePolls: stable
          });
        }
      } catch (err) {
        if (!String(err).includes("PHASE5_ASSISTANT")) throw err;
      }

      await new Promise(resolve => setTimeout(resolve, pollMs));
    }

    throw new Error("PHASE5_COMPLETED_ASSISTANT_TIMEOUT");
  }

  async function stageDraft(text) {
    const binding = await bindConfiguredConversation();
    if (generationActive()) {
      throw new Error("PHASE5_CANNOT_DRAFT_WHILE_STREAMING");
    }
    const value = String(text || "");
    if (!value.trim()) throw new Error("PHASE5_EMPTY_DRAFT");
    const el = composer();
    if (!el) throw new Error("PHASE5_COMPOSER_NOT_FOUND");
    setComposerText(el, value);
    pendingApproval = null;
    return Object.freeze({
      conversationUrl: binding.conversationUrl,
      draftHash: await sha256(normalizeText(value)),
      chars: value.length
    });
  }

  async function approveCurrentDraft() {
    const binding = await bindConfiguredConversation();
    if (generationActive()) {
      throw new Error("PHASE5_CANNOT_APPROVE_WHILE_STREAMING");
    }
    const value = composerText();
    if (!value.trim()) throw new Error("PHASE5_EMPTY_DRAFT");
    const approval = Object.freeze({
      conversationUrl: binding.conversationUrl,
      draftHash: await sha256(normalizeText(value)),
      nonce: crypto.randomUUID()
    });
    pendingApproval = approval;
    return approval;
  }

  function usableSendButton(anchor = composer()) {
    const selectors = [
      'button[data-testid="send-button"]',
      'button[aria-label*="Send"]',
      'button[aria-label*="Senden"]',
      'button[type="submit"]'
    ];
    const form = anchor && anchor.closest ? anchor.closest("form") : null;
    const candidates = [];
    if (form) {
      for (const selector of selectors) {
        candidates.push(...form.querySelectorAll(selector));
      }
    }
    for (const selector of selectors) {
      candidates.push(...document.querySelectorAll(selector));
    }
    return candidates.find(el => {
      if (!el || !el.isConnected || el.disabled) return false;
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0;
    }) || null;
  }

  async function sendApprovedDraft(approval) {
    if (!approval || approval !== pendingApproval) {
      throw new Error("PHASE5_APPROVAL_MISSING_OR_STALE");
    }

    let binding;
    try {
      binding = await bindConfiguredConversation();
    } catch (err) {
      pendingApproval = null;
      throw err;
    }
    if (approval.conversationUrl !== binding.conversationUrl) {
      pendingApproval = null;
      throw new Error("PHASE5_APPROVAL_CONVERSATION_CHANGED");
    }
    if (generationActive()) {
      throw new Error("PHASE5_CANNOT_SEND_WHILE_STREAMING");
    }

    const currentHash = await sha256(normalizeText(composerText()));
    if (currentHash !== approval.draftHash) {
      pendingApproval = null;
      throw new Error("PHASE5_APPROVAL_DRAFT_CHANGED");
    }

    const button = usableSendButton();
    if (!button) throw new Error("PHASE5_SEND_CONTROL_NOT_FOUND");

    pendingApproval = null;
    button.click();
    return Object.freeze({
      conversationUrl: binding.conversationUrl,
      draftHash: approval.draftHash,
      submitted: true
    });
  }

  function invalidateApproval() {
    pendingApproval = null;
  }

  // AGP_PHASE7_VERBATIM_PROTOCOL_BLOCK_260

async function currentAssistantProtocolSnapshot() {
  // AGP_PHASE7_PROTOCOL_PRE_DEDUP_261
  //
  // ChatGPT can render one logical code block through multiple <pre> nodes.
  // De-duplicate only byte-for-byte identical protocol-bearing blocks.
  // Different protocol frames remain ambiguous and fail closed.
  const binding = await bindConfiguredConversation();
  if (generationActive()) {
    throw new Error("PHASE7_PROTOCOL_STREAMING");
  }

  const assistants = visibleAssistantNodes();
  if (!assistants.length) {
    throw new Error("PHASE7_PROTOCOL_ASSISTANT_NOT_FOUND");
  }
  const assistant = assistants[assistants.length - 1];

  const rawCandidates = Array.from(assistant.querySelectorAll("pre"))
    .map((node) => String(node.textContent || "").trim())
    .filter((text) =>
      text.includes("AGP_COCKPIT_ACTION_BEGIN") ||
      text.includes("AGP_COCKPIT_RESULT_BEGIN") ||
      text.includes("AGP_COCKPIT_CONTROL_BEGIN")
    );

  const uniqueCandidates = [...new Set(rawCandidates)];

  // AGP_PHASE8_PROTOCOL_RENDERING_FALLBACK_298
  // Prefer exact <pre> extraction. Real ChatGPT may render a protocol response
  // as ordinary assistant text; only when no protocol-bearing <pre> exists,
  // extract one strict framed payload from that same assistant message.
  let frame = "";
  let source = "";
  if (uniqueCandidates.length === 1) {
    const text = uniqueCandidates[0];
    frame = extractSingleProtocolFrame(text, { includeControl: true });
    if (frame !== text) {
      throw new Error("PHASE7_PROTOCOL_BLOCK_NOT_PURE_FRAME");
    }
    source = "pre";
  } else if (uniqueCandidates.length === 0) {
    const observedText = String(
      assistant.innerText || assistant.textContent || ""
    ).trim();
    frame = extractSingleProtocolFrame(observedText, { includeControl: true });
    const isProtocolFrame =
      frame.startsWith("AGP_COCKPIT_ACTION_BEGIN") ||
      frame.startsWith("AGP_COCKPIT_RESULT_BEGIN") ||
      frame.startsWith("AGP_COCKPIT_CONTROL_BEGIN");
    if (!isProtocolFrame) {
      throw new Error(
        `PHASE7_PROTOCOL_BLOCK_COUNT expected=1 actual=0 raw=${rawCandidates.length}`
      );
    }
    source = "assistant-text";
  } else {
    throw new Error(
      `PHASE7_PROTOCOL_BLOCK_COUNT expected=1 actual=${uniqueCandidates.length} raw=${rawCandidates.length}`
    );
  }

  const conversationUrl = binding.conversationUrl;
  const fingerprintBytes = new TextEncoder().encode(`${conversationUrl}\n${frame}`);
  const fingerprintDigest = await crypto.subtle.digest("SHA-256", fingerprintBytes);
  const fingerprint = Array.from(new Uint8Array(fingerprintDigest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  return {
    conversationUrl,
    text: frame,
    fingerprint,
    source,
    rawProtocolBlockCount: rawCandidates.length,
    uniqueProtocolBlockCount: uniqueCandidates.length,
  };
}

  // AGP_PHASE8_PROTOCOL_WAIT_CONSOLIDATION_308
  async function waitForCompletedProtocolAssistant({
    afterFingerprint = "",
    timeoutMs = 30000,
    pollMs = 250,
    stablePolls = 3
  } = {}) {
    const deadline = Date.now() + timeoutMs;
    let candidate = "";
    let candidateText = "";
    let candidateSnapshot = null;
    let stable = 0;
    while (Date.now() < deadline) {
      await bindConfiguredConversation();
      if (generationActive()) {
        candidate = ""; candidateText = ""; candidateSnapshot = null; stable = 0;
        await new Promise(resolve => setTimeout(resolve, pollMs));
        continue;
      }
      try {
        const snapshot = await currentAssistantProtocolSnapshot();
        if (snapshot.fingerprint === afterFingerprint) {
          candidate = ""; candidateText = ""; candidateSnapshot = null; stable = 0;
        } else if (snapshot.fingerprint !== candidate) {
          candidate = snapshot.fingerprint; candidateText = snapshot.text;
          candidateSnapshot = snapshot; stable = 1;
        } else {
          stable += 1;
        }
        if (candidate && stable >= stablePolls) {
          return Object.freeze({
            conversationUrl: candidateSnapshot.conversationUrl,
            text: candidateText, fingerprint: candidate,
            stablePolls: stable, source: candidateSnapshot.source
          });
        }
      } catch (err) {
        const message = String(err && err.message || err);
        const transient =
          message.includes("PHASE7_PROTOCOL_STREAMING") ||
          message.includes("PHASE7_PROTOCOL_ASSISTANT_NOT_FOUND") ||
          message.includes("PHASE7_PROTOCOL_BLOCK_COUNT expected=1 actual=0");
        if (!transient) throw err;
      }
      await new Promise(resolve => setTimeout(resolve, pollMs));
    }
    throw new Error("PHASE8_COMPLETED_PROTOCOL_ASSISTANT_TIMEOUT");
  }

  globalThis.AGPCockpitConversationContract = Object.freeze({
    marker: "AGP_PHASE5_CONVERSATION_CONTRACT_204",
    normalizeConversationUrl,
    configuredConversationUrl,
    bindConfiguredConversation,
    currentAssistantSnapshot,
    currentAssistantProtocolSnapshot,
    waitForCompletedAssistant,
    waitForCompletedProtocolAssistant,
    stageDraft,
    approveCurrentDraft,
    sendApprovedDraft,
    invalidateApproval
  });
})();

