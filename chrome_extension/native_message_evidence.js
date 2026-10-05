// Shared by the content script and the serialized CDP observation.
// Keep this function self-contained: toString() preserves regex escapes in CDP.
function agpNormalizeUserTurnText(value) {
  return String(value || "")
    .normalize("NFKC")
    .replace(/[\u200b\u200c\u200d\ufeff]/g, "")
    .replace(/\u00a0/g, " ")
    // ChatGPT exposes the rendered user Markdown, not the raw composer text.
    .replace(/```[^\n]*\n?/g, "")
    .replace(/`/g, "")
    .replace(/\\([\\`*_{}\[\]()#+.!>~-])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
}

function agpRenderedUserTurnMatches(observed, expected) {
  const observedText = agpNormalizeUserTurnText(observed);
  const expectedText = agpNormalizeUserTurnText(expected);
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

// AGP_COMPOSER_RESOLVER_V1: one self-contained composer identity for the
// content script and every serialized CDP expression (toString()).
// Live 2026-09-30 on a new chat (https://chatgpt.com/): the focus step took
// the first [contenteditable][role=textbox] in document order, blurred the
// focused visible composer and could not focus its choice
// (COMPOSER_FOCUS_NOT_VERIFIED, active element BODY). Only visible, enabled,
// non-inert candidates count; the focused candidate wins.
function agpResolveComposer() {
  const usable = el => {
    if (!el || el.disabled || el.isConnected === false) return false;
    if (typeof el.closest === "function" && el.closest('[inert], [aria-hidden="true"]')) return false;
    const rect = el.getBoundingClientRect();
    if (!(rect.width > 0 && rect.height > 0)) return false;
    const style = getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") return false;
    // AGP_COMPOSER_VISIBLE_FORM_V1: the ChatGPT start page (live 2026-10-05)
    // renders three composer forms, two of them 0x0. A composer inside an
    // invisible form is never the owner's composer.
    const form = typeof el.closest === "function" ? el.closest("form") : null;
    if (form) {
      const formRect = form.getBoundingClientRect();
      if (!(formRect.width > 0 && formRect.height > 0)) return false;
    }
    return true;
  };
  const candidates = Array.from(document.querySelectorAll(
    '#prompt-textarea, textarea[data-id="root"], [contenteditable="true"][role="textbox"], form [contenteditable="true"]'
  )).filter(usable);
  if (!candidates.length) return null;
  const active = document.activeElement;
  if (active && candidates.includes(active)) return active;
  const byId = candidates.find(el => el.id === "prompt-textarea");
  if (byId) return byId;
  return candidates.find(el => typeof el.closest === "function" && el.closest("form")) || candidates[0];
}

function agpNativeMessageSnapshot(resolveComposer) {
  // Keep the snapshot self-contained: background.js serializes this function
  // into the page through Runtime.evaluate(...toString()).
  const norm = value => String(value || "")
    .normalize("NFKC")
    .replace(/[\u200b\u200c\u200d\ufeff]/g, "")
    .replace(/\u00a0/g, " ")
    .replace(/```[^\n]*\n?/g, "")
    .replace(/`/g, "")
    .replace(/\\([\\`*_{}\[\]()#+.!>~-])/g, "$1")
    .replace(/\s+/g, " ")
    .trim();
  // ChatGPT has used several equivalent user-turn wrappers. Prefer the
  // semantic role selector, then fall back to the turn/test-id wrappers. Do
  // not combine selector results: nested wrappers would double-count a turn.
  const userSelectors = [
    '[data-message-author-role="user"]',
    'article[data-testid^="conversation-turn-user"]',
    '[data-testid*="conversation-turn"][data-testid*="user"]'
  ];
  const visibleElement = node => {
    if (!node || typeof node.getBoundingClientRect !== "function") return false;
    const r = node.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const cloneMessageText = node => {
    const content = node.querySelector('[data-testid="collapsible-user-message-content"]');
    const copy = (content || node).cloneNode(true);
    copy.querySelectorAll('button, [role="button"], [aria-hidden="true"]').forEach(control => control.remove());
    copy.querySelectorAll('br').forEach(br => br.replaceWith(document.createTextNode("\n")));
    copy.querySelectorAll('div, p, pre, li, h1, h2, h3, h4, blockquote, tr').forEach(block => {
      block.prepend(document.createTextNode("\n"));
      block.append(document.createTextNode("\n"));
    });
    return norm(copy.textContent || "");
  };
  let nodes = [];
  for (const selector of userSelectors) {
    const candidates = Array.from(document.querySelectorAll(selector))
      .filter(visibleElement);
    if (candidates.length) {
      nodes = candidates;
      break;
    }
  }
  nodes = nodes.filter(visibleElement);
  let messages = nodes.map(node => ({
    id:node.getAttribute("data-message-id") || "",
    text:cloneMessageText(node)
  }));
  if (!messages.length) {
    const userLabels = new Set(["du hast gesagt", "du hast gesagt:", "you said", "you said:"]);
    const authorLabels = new Set([
      "du hast gesagt", "du hast gesagt:", "you said", "you said:",
      "chatgpt hat gesagt", "chatgpt hat gesagt:", "chatgpt said", "chatgpt said:"
    ]);
    const labelCandidates = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6,[role='heading'],strong,span,div"))
      .filter(visibleElement)
      .filter(node => {
        const value = norm(node.textContent).toLowerCase();
        return value.length <= 40 && userLabels.has(value);
      });
    const textFromLabel = label => {
      for (let base = label; base; base = base.parentElement) {
        const parent = base.parentElement;
        if (!parent || parent === document.body || parent === document.documentElement) break;
        const parts = [];
        for (let sibling = base.nextElementSibling; sibling; sibling = sibling.nextElementSibling) {
          const boundary = norm(sibling.textContent).toLowerCase();
          if (boundary.length <= 40 && authorLabels.has(boundary)) break;
          if (!visibleElement(sibling)) continue;
          const text = cloneMessageText(sibling);
          if (text) parts.push(text);
          if (parts.length) break;
        }
        if (parts.length) return parts.join(" ");
      }
      return "";
    };
    messages = labelCandidates
      .map(label => ({
        id:label.getAttribute("data-message-id") || "",
        text:textFromLabel(label)
      }))
      .filter(message => message.text);
  }
  const composer = typeof resolveComposer === "function"
    ? resolveComposer()
    : document.querySelector('#prompt-textarea, textarea[data-id="root"], form [contenteditable="true"]');
  return {
    url:location.href,
    messages,
    user_message_count:messages.length,
    latest_user_message:messages.length ? messages[messages.length - 1].text : "",
    composer_text:norm(composer ? ("value" in composer ? composer.value : composer.innerText || composer.textContent) : ""),
    generation_active:Boolean(document.querySelector('[data-testid="stop-button"], [data-is-streaming="true"]'))
  };
}

// AGP_SUBMIT_FOCUS_AND_FORM_BUTTON_V1 (live 2026-10-05, build r6, new chat):
// after Input.insertText on the ChatGPT start page the focus moved from the
// composer to <main> (inserted.active_tag MAIN; in every earlier successful
// send it was the composer DIV), so the trusted Enter went nowhere; the DOM
// fallback then looked only for button[data-testid="send-button"], which the
// current UI no longer renders. Both helpers are self-contained: background.js
// serializes them into the page with Function.prototype.toString().
function agpRefocusComposerForSubmit(resolveComposer) {
  const composer = typeof resolveComposer === "function" ? resolveComposer() : null;
  if (!composer) return {ok:false, reason:"composer_not_found", active_tag:"", active_id:""};
  const before = document.activeElement;
  const refocused = before !== composer;
  if (refocused) {
    if (typeof window.focus === "function") window.focus();
    if (typeof composer.focus === "function") composer.focus();
    if (!("value" in composer) && typeof window.getSelection === "function") {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(composer);
      range.collapse(false);
      selection.removeAllRanges();
      selection.addRange(range);
    }
  }
  const active = document.activeElement;
  return {
    ok:active === composer,
    refocused,
    before_tag:before ? before.tagName : "",
    active_tag:active ? active.tagName : "",
    active_id:active ? active.id : ""
  };
}

function agpComposerSendButton(resolveComposer) {
  const composer = typeof resolveComposer === "function" ? resolveComposer() : null;
  const form = composer && typeof composer.closest === "function" ? composer.closest("form") : null;
  if (!form) return null;
  const buttons = Array.from(form.querySelectorAll('button[data-testid="send-button"], button[type="submit"]'));
  return buttons.find(button => {
    const label = String(button.getAttribute("aria-label") || "");
    if (button.getAttribute("data-testid") !== "send-button" && !/^(send|senden)\b/i.test(label)) return false;
    if (button.disabled || button.getAttribute("aria-disabled") === "true") return false;
    const rect = button.getBoundingClientRect();
    const style = getComputedStyle(button);
    return rect.width > 0 && rect.height > 0 && style.visibility !== "hidden" &&
      style.display !== "none" && style.pointerEvents !== "none";
  }) || null;
}

// AGP_PANEL_LIVE_STATUS_V1 (live 2026-10-05): the bridge panel showed
// "0 / 40" and "Aktualisiert 10:25:46" for the whole run although the bridge
// counted turn 1 at 10:27:17; a local step that waits for CI (8 min) showed no
// sign of life either. Pure helpers, used by content.js and tested in node.
function agpMergeLiveMission(current, fresh) {
  // Observational only: take the counters of the same mission, nothing else.
  if (!current || !fresh || !current.mission_id || fresh.mission_id !== current.mission_id) return null;
  return Object.assign({}, current, {
    turn_count: Number(fresh.turn_count || 0),
    step_count: Number(fresh.step_count || 0)
  });
}

function agpMissionPhaseText(phase, nowMs) {
  const since = startedAt => {
    const seconds = Math.max(0, Math.floor((Number(nowMs) - Number(startedAt)) / 1000));
    return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
  };
  if (!phase) return "";
  if (Number(phase.processingStartedAt) > 0) {
    const file = String(phase.processingFile || "").trim();
    return `${file || "Auftrag"} läuft lokal seit ${since(phase.processingStartedAt)}`;
  }
  if (phase.waitingForAssistant && Number(phase.assistantWaitStartedAt) > 0) {
    return `wartet auf ChatGPT seit ${since(phase.assistantWaitStartedAt)}`;
  }
  return "";
}
