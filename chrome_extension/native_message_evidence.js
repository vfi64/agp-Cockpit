// Shared by the content script and the serialized CDP observation.
// Keep this function self-contained: toString() preserves regex escapes in CDP.
function agpNativeMessageSnapshot() {
  const norm = value => String(value || "").replace(/\s+/g, " ").trim();
  const nodes = Array.from(document.querySelectorAll('[data-message-author-role="user"]'))
    .filter(node => {
      const r = node.getBoundingClientRect();
      return r.width > 0 && r.height > 0;
    });
  const messages = nodes.map(node => {
    const content = node.querySelector('[data-testid="collapsible-user-message-content"]');
    const copy = (content || node).cloneNode(true);
    copy.querySelectorAll('button, [role="button"], [aria-hidden="true"]').forEach(control => control.remove());
    copy.querySelectorAll('br').forEach(br => br.replaceWith(document.createTextNode("\n")));
    copy.querySelectorAll('div, p, pre, li, h1, h2, h3, h4, blockquote, tr').forEach(block => {
      block.prepend(document.createTextNode("\n"));
      block.append(document.createTextNode("\n"));
    });
    const text = copy.textContent || "";
    return {id:node.getAttribute("data-message-id") || "", text:norm(text)};
  });
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
