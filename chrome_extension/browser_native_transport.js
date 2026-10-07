(() => {
  "use strict";

  const MESSAGE_TYPE = "AGP_BROWSER_NATIVE_TRANSPORT_V1";

  function correlationId() {
    if (globalThis.crypto && typeof globalThis.crypto.randomUUID === "function") {
      return globalThis.crypto.randomUUID();
    }
    return `agp-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function resolveComposer() {
    // AGP_COMPOSER_RESOLVER_V1: same identity as the service worker.
    if (typeof globalThis.agpResolveComposer === "function") {
      const resolved = globalThis.agpResolveComposer();
      if (resolved) return resolved;
    }
    // AGP_SELECTOR_TABLE_V1: the canonical order and the chain come from chatgpt_selectors.js.
    const table = globalThis.AGP_SELECTORS;
    if (typeof document.querySelector === "function") {
      for (const selector of table.nativeComposerCanonical) {
        const el = document.querySelector(selector);
        if (el && el.getBoundingClientRect().width > 0 &&
            el.getBoundingClientRect().height > 0 && !el.disabled) return el;
      }
    }
    const selectors = table.nativeComposerChain;
    if (!document || typeof document.querySelectorAll !== "function") return null;
    for (const selector of selectors) {
      for (const el of document.querySelectorAll(selector)) {
        const rect = el.getBoundingClientRect();
        if (rect.width > 0 && rect.height > 0 && !el.disabled) {
          return el;
        }
      }
    }
    return undefined;
  }

  function observedComposerText(el) {
    if (!el) return "";
    if (el instanceof HTMLTextAreaElement) return String(el.value || "");
    return String(el.innerText || el.textContent || "");
  }

  async function runtimeMessage(payload) {
    return await new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(payload, response => {
        const lastError = chrome.runtime.lastError;
        if (lastError) {
          const error = new Error(lastError.message || "runtime messaging failed");
          error.runtime_message_error = lastError.message || "";
          reject(error);
          return;
        }
        if (!response) {
          reject(new Error(`native transport rejected: ${JSON.stringify(response || null)}`));
          return;
        }
        if (response.ok !== true &&
            response.stage !== "USER_TURN_INDETERMINATE" &&
            response.stage !== "COMPOSER_MODEL_NOT_VERIFIED") {
          const rejected = new Error(
            response.error
              ? String(response.error)
              : `native transport rejected: ${JSON.stringify(response)}`
          );
          rejected.response = response;   // AGP_SEND_NOT_READY_RETRY_V1: structured stage/diagnostics
          reject(rejected);
          return;
        }
        resolve(response);
      });
    });
  }

  async function submit(text, options = {}) {
    const prompt = String(text || "");
    if (!prompt) throw new Error("native transport refuses empty prompt");

    const composer = resolveComposer();
    if (!composer) throw new Error("native transport composer not found");

    const existing = observedComposerText(composer).trim();
    if (existing) {
      throw new Error(
        "native transport requires an empty composer; refusing to overwrite existing text"
      );
    }

    composer.focus();

    const requestId = correlationId();
    const response = await runtimeMessage({
      type: MESSAGE_TYPE,
      request_id: requestId,
      operation: "insert_and_submit",
      text: prompt,
      commit_marker: String(options.commitMarker || ""),
      attempt: Number(options.attempt || 1),
      page_url: location.href
    });

    if (String(response.request_id || "") !== requestId) {
      throw new Error("native transport correlation mismatch");
    }
    if (response.stage === "USER_TURN_INDETERMINATE") {
      return {
        request_id: requestId,
        stage: response.stage,
        tab_id: response.tab_id,
        commit: response.commit || null,
        inserted: response.inserted || null,
        submit_attempts: response.submit_attempts || [],
        after: response.after || null
        ,diagnostics: response.diagnostics || null
      };
    }
    if (response.stage === "COMPOSER_MODEL_NOT_VERIFIED") {
      return {
        request_id: requestId,
        stage: response.stage,
        tab_id: response.tab_id,
        inserted: response.inserted || null,
        model: response.model || null
      };
    }
    if (response.stage !== "USER_TURN_COMMITTED") {
      const error = new Error(
        `native transport uncommitted stage: ${String(response.stage || "")}`
      );
      error.native_transport_evidence = response;
      throw error;
    }

    return {
      request_id: requestId,
      stage: response.stage,
      tab_id: response.tab_id,
      commit: response.commit || null,
      inserted: response.inserted || null,
      diagnostics: response.diagnostics || null
    };
  }

  window.AGPBrowserNativeTransport = Object.freeze({
    version: "1",
    available() {
      return Boolean(
        globalThis.chrome &&
        chrome.runtime &&
        typeof chrome.runtime.sendMessage === "function"
      );
    },
    submit
  });
})();
