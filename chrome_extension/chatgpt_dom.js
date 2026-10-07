// AGP_DOM_ADAPTER_V1 (DOM hardening step 3, owner 2026-10-07): the one place that names
// ChatGPT's page structure. content.js asks this adapter for touchpoints instead of using
// selectors itself; when ChatGPT changes its page, the fix belongs here and the contract
// of each touchpoint (below) stays. Loaded by the manifest before content.js, a classic
// script with one frozen namespace (no bundler, no ES modules in content scripts).
//
// Touchpoints in this slice (3a):
// - assistantTurns(): the assistant messages in document order.
// - fileCardRow(anchor): name, href, button flag and download control of a file card.
// - stepFileCards(step, kind): visible file cards of the expected step — "command"
//   (<step>_*.py) or "terminal" (<step>_agp_terminal.json); never in the composer form,
//   a user turn, a dialog or a hidden/inert container; first card per name wins.
// - alertNotices(): ChatGPT's own short alert texts (no chat content), for diagnosis.
//
// Slice 3b (composer and send controls):
// - composerFallback(): the composer when the resolver (agpResolveComposer, rule 67) finds
//   none: #prompt-textarea, a textarea, then any contenteditable.
// - sendButton(anchor): a usable (connected, enabled, visible) send control, first inside
//   the anchor's form, then anywhere; null when ChatGPT shows none (the send never needs it,
//   AGP_SEND_OUTCOME_FIRST_V1).
// - generationActive(): a visible stop control or a streaming marker.
// - stopLikeButtonVisible(): an enabled stop-like button in a composer form (activity signal).
//
// Slice 3c (attachment preview of a file card without href):
// - previewTextbox(filename): the readable preview of that file — a code textbox inside a
//   dialog, or a textbox labelled with the file name (side panel).
// - previewContainer(preview): the nearest ancestor holding both a close and a download
//   control, else the enclosing dialog.
// - previewDownloadButton(preview): the preview's download control.
// - openDialog(): the first dialog on the page.
// - dialogCloseControl(dialog, active): the control that closes it (OK, close, Schließen,
//   exit full screen; the focused button inside the dialog first), or null.
(function () {
  const SELECTORS = Object.freeze({
    assistantTurn: '[data-message-author-role="assistant"]',
    fileCardCandidate: 'a[href], button, [role="button"]',
    fileCardExcluded: 'form, [data-message-author-role="user"], [role="dialog"], [aria-modal="true"]',
    hiddenContainer: '[inert], [aria-hidden="true"]',
    fileCardDownload: 'button[aria-label="Datei herunterladen"], button[aria-label="Download"]',
    alert: '[role="alert"]',
    composerFallback: Object.freeze(['#prompt-textarea', 'textarea', '[contenteditable="true"]']),
    sendButton: Object.freeze([
      'button[data-testid="send-button"]',
      'button[aria-label*="Send"]',
      'button[aria-label*="Senden"]',
      'button[type="submit"]',
    ]),
    generationActive: Object.freeze([
      'button[data-testid="stop-button"]',
      'button[aria-label*="Stop generating"]',
      'button[aria-label*="Stop response"]',
      'button[aria-label*="Generierung stoppen"]',
      'button[aria-label*="Antwort stoppen"]',
      '[data-is-streaming="true"]',
      '[data-testid="stop-generating-button"]',
    ]),
    stopLikeButton: "form button, [data-testid*='composer'] button",
    dialog: '[role="dialog"], [aria-modal="true"]',
    previewTextbox: '[role="dialog"] .cm-content[role="textbox"], [role="dialog"] .cm-content, ' +
      '.cm-content[role="textbox"], [role="textbox"][aria-label]',
    dialogClose: '[data-testid="close-button"], button[aria-label="Vollbildmodus beenden"], ' +
      'button[aria-label="Exit full screen"], button[aria-label="Schließen"], ' +
      'button[aria-label="Close"], button',
  });

  const CLOSE_LABELS = Object.freeze(["ok", "close", "schließen", "exit full screen", "vollbildmodus beenden"]);
  const DOWNLOAD_LABELS = Object.freeze(["download", "herunterladen", "datei herunterladen"]);
  const labelOf = button => String(
    button.getAttribute("aria-label") || button.textContent || button.title || ""
  ).replace(/\s+/g, " ").trim().toLowerCase();

  function assistantTurns() {
    return Array.from(document.querySelectorAll(SELECTORS.assistantTurn));
  }

  function fileCardRow(anchor) {
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
      downloadNode = row.querySelector(SELECTORS.fileCardDownload);
      if (downloadNode) break;
    }
    return {href, name, isButton: anchor.tagName === "BUTTON", node: anchor, downloadNode};
  }

  function stepFileCards(expectedStep, kind = "command") {
    const pattern = kind === "terminal"
      ? new RegExp(`^${Number(expectedStep)}_agp_terminal\\.json(?:[?#]|$)`)
      : new RegExp(`^${Number(expectedStep)}_[^\\s/]+\\.py(?:[?#]|$)`, "i");
    const unique = new Map();
    for (const anchor of document.querySelectorAll(SELECTORS.fileCardCandidate)) {
      if (anchor.closest(SELECTORS.fileCardExcluded)) continue;
      if (anchor.closest(SELECTORS.hiddenContainer)) continue;
      const rect = anchor.getBoundingClientRect();
      if (!(rect.width > 0 && rect.height > 0)) continue;
      const item = fileCardRow(anchor);
      if (!pattern.test(String(item.name || ""))) continue;
      if (!(item.href || item.isButton)) continue;
      const key = `${item.href}\n${item.name}`;
      if (!unique.has(key)) unique.set(key, item);
    }
    return Array.from(unique.values());
  }

  function alertNotices(limit = 5) {
    return Array.from(document.querySelectorAll(SELECTORS.alert))
      .map(node => String(node.innerText || node.textContent || "").trim())
      .filter(text => text && text.length <= 120 && !text.includes("\n"))
      .slice(0, limit);
  }

  function composerFallback() {
    for (const selector of SELECTORS.composerFallback) {
      const el = document.querySelector(selector);
      if (el) return el;
    }
    return null;
  }

  function isUsableSendControl(el) {
    if (!el || !el.isConnected || el.disabled) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function sendButton(anchor = null) {
    const form = anchor && anchor.closest ? anchor.closest("form") : null;
    if (form) {
      for (const selector of SELECTORS.sendButton) {
        const candidate = form.querySelector(selector);
        if (isUsableSendControl(candidate)) return candidate;
      }
    }
    for (const selector of SELECTORS.sendButton) {
      const candidate = Array.from(document.querySelectorAll(selector)).find(isUsableSendControl);
      if (candidate) return candidate;
    }
    return null;
  }

  function generationActive() {
    return SELECTORS.generationActive.some(selector => {
      const el = document.querySelector(selector);
      return Boolean(el && !el.disabled);
    });
  }

  function stopLikeButtonVisible() {
    return Array.from(document.querySelectorAll(SELECTORS.stopLikeButton))
      .some(button => !button.disabled && (
        /^(stop|stoppen)\b/i.test(String(button.getAttribute("aria-label") || "").trim()) ||
        /stop/i.test(String(button.getAttribute("data-testid") || ""))));
  }

  function previewTextbox(filename) {
    const expectedName = String(filename || "").trim().toLowerCase();
    return Array.from(document.querySelectorAll(SELECTORS.previewTextbox)).find(candidate => {
      const content = String(candidate.innerText || candidate.textContent || "").trim();
      if (!content) return false;
      if (candidate.closest(SELECTORS.dialog)) return true;
      const label = String(candidate.getAttribute("aria-label") || "").trim().toLowerCase();
      return Boolean(expectedName) && (label === expectedName || label.endsWith(`/${expectedName}`));
    }) || null;
  }

  function previewContainer(preview) {
    let current = preview;
    for (let depth = 0; current && depth < 12; depth += 1, current = current.parentElement) {
      const labels = Array.from(current.querySelectorAll("button")).map(labelOf);
      const hasClose = labels.some(label => label === "close" || label === "schließen");
      const hasDownload = labels.some(label => label === "download" || label === "herunterladen");
      if (hasClose && hasDownload) return current;
    }
    return preview ? preview.closest(SELECTORS.dialog) : null;
  }

  function previewDownloadButton(preview) {
    const root = previewContainer(preview) || preview;
    if (!root) return null;
    return Array.from(root.querySelectorAll("button")).find(button => DOWNLOAD_LABELS.includes(labelOf(button))) || null;
  }

  function openDialog() {
    return document.querySelector(SELECTORS.dialog);
  }

  function dialogCloseControl(dialog, active = null) {
    if (!dialog) return null;
    const candidates = Array.from(dialog.querySelectorAll(SELECTORS.dialogClose));
    if (active && active.tagName === "BUTTON" && dialog.contains(active)) candidates.unshift(active);
    return candidates.find(button => CLOSE_LABELS.includes(labelOf(button)) ||
      button.getAttribute("data-testid") === "close-button") || null;
  }

  globalThis.AGP_DOM = Object.freeze({
    SELECTORS, assistantTurns, fileCardRow, stepFileCards, alertNotices,
    composerFallback, isUsableSendControl, sendButton, generationActive, stopLikeButtonVisible,
    previewTextbox, previewContainer, previewDownloadButton, openDialog, dialogCloseControl,
  });
})();
