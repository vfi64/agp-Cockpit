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

function agpNativeMessageSnapshot() {
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
  const composer = document.querySelector('#prompt-textarea, textarea[data-id="root"], form [contenteditable="true"]');
  return {
    url:location.href,
    messages,
    user_message_count:messages.length,
    latest_user_message:messages.length ? messages[messages.length - 1].text : "",
    composer_text:norm(composer ? ("value" in composer ? composer.value : composer.innerText || composer.textContent) : ""),
    generation_active:Boolean(document.querySelector('[data-testid="stop-button"], [data-is-streaming="true"]'))
  };
}
