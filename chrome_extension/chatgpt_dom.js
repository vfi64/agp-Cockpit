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
(function () {
  const SELECTORS = Object.freeze({
    assistantTurn: '[data-message-author-role="assistant"]',
    fileCardCandidate: 'a[href], button, [role="button"]',
    fileCardExcluded: 'form, [data-message-author-role="user"], [role="dialog"], [aria-modal="true"]',
    hiddenContainer: '[inert], [aria-hidden="true"]',
    fileCardDownload: 'button[aria-label="Datei herunterladen"], button[aria-label="Download"]',
    alert: '[role="alert"]',
  });

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

  globalThis.AGP_DOM = Object.freeze({SELECTORS, assistantTurns, fileCardRow, stepFileCards, alertNotices});
})();
