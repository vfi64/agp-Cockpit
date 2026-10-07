// AGP_SELECTOR_TABLE_V1 (DOM hardening step 3, owner 2026-10-07): every selector that names
// ChatGPT's page lives here and nowhere else. One frozen data object, no functions, so that
// - the content scripts read it as the global AGP_SELECTORS (manifest: loaded first),
// - the service worker reads it through importScripts, and
// - every helper that the service worker injects into the page through Runtime.evaluate
//   (background.js, result_file_attachment.js) gets the same table: agpPageExpression() wraps
//   the expression in a scope that defines AGP_SELECTORS from this object (JSON), because the
//   page world cannot see extension globals.
// When ChatGPT changes its page, the fix belongs in this file.
globalThis.AGP_SELECTORS = (() => {
  const freeze = value => {
    if (value && typeof value === "object") {
      Object.values(value).forEach(freeze);
      Object.freeze(value);
    }
    return value;
  };
  return freeze({
    // Composer (AGP_COMPOSER_RESOLVER_V1): resolver candidates, the preferred id, fallbacks.
    composer: '#prompt-textarea, textarea[data-id="root"], [contenteditable="true"][role="textbox"], ' +
      'form [contenteditable="true"]',
    composerPreferredId: "prompt-textarea",
    composerFallback: ['#prompt-textarea', 'textarea', '[contenteditable="true"]'],
    composerSnapshotFallback: '#prompt-textarea, textarea[data-id="root"], form [contenteditable="true"]',
    composerTextbox: '[contenteditable="true"][role="textbox"]',
    nativeComposerCanonical: ["#prompt-textarea", 'textarea[data-id="root"]', "textarea"],
    nativeComposerChain: [
      "#prompt-textarea",
      'textarea[data-id="root"]',
      "textarea",
      '[contenteditable="true"][data-testid*="composer"]',
      '[contenteditable="true"][id*="prompt"]',
      '[contenteditable="true"][role="textbox"]',
      'form [contenteditable="true"]',
    ],
    // Turns: user turn wrappers in preference order (never combined), its content, assistant turns.
    userTurn: [
      '[data-message-author-role="user"]',
      'article[data-testid^="conversation-turn-user"]',
      '[data-testid*="conversation-turn"][data-testid*="user"]',
    ],
    userTurnContent: '[data-testid="collapsible-user-message-content"]',
    assistantTurn: '[data-message-author-role="assistant"]',
    // Send controls: the usable send button (form first), the form-bound submit, diagnostics.
    sendButton: [
      'button[data-testid="send-button"]',
      'button[aria-label*="Send"]',
      'button[aria-label*="Senden"]',
      'button[type="submit"]',
    ],
    sendButtonTestId: "send-button",
    sendButtonByTestId: 'button[data-testid="send-button"]',
    formSendButton: 'button[data-testid="send-button"], button[type="submit"]',
    sendButtonProbe: [
      'button[data-testid="send-button"]',
      'button[aria-label*="Send"]',
      'button[aria-label*="Senden"]',
      'form button[type="submit"]',
    ],
    sendButtonDiagnostics: 'button[data-testid="send-button"], button[aria-label*="Send"], ' +
      'button[aria-label*="Senden"], form button[type="submit"]',
    // Diagnostics only (K07_ASSISTANT_WAIT_OBSERVATION): structures counted while waiting.
    waitObservation: {
      role_assistant: '[data-message-author-role="assistant"]',
      role_user: '[data-message-author-role="user"]',
      role_any: "[data-message-author-role]",
      message_ids: "[data-message-id]",
      turn_articles: 'article[data-testid^="conversation-turn"]',
      testid_turns: '[data-testid*="conversation-turn"]',
    },
    // Generation and stop signals.
    generationActive: [
      'button[data-testid="stop-button"]',
      'button[data-testid="stop-generating-button"]',
      'button[aria-label*="Stop generating"]',
      'button[aria-label*="Stop response"]',
      'button[aria-label*="Generierung stoppen"]',
      'button[aria-label*="Antwort stoppen"]',
      '[data-is-streaming="true"]',
      '[data-testid="stop-generating-button"]',
    ],
    generationActiveQuick: '[data-testid="stop-button"], [data-is-streaming="true"]',
    stopButton: '[data-testid="stop-button"]',
    stopLikeButton: "form button, [data-testid*='composer'] button",
    // File cards, preview and dialogs (slices 3a/3c).
    fileCardCandidate: 'a[href], button, [role="button"]',
    pythonFileControl: 'a[href$=".py"], button[aria-label$=".py"], button, [role="button"]',
    pythonFileRow: 'a[href], button[aria-label$=".py"], button, [role="button"]',
    fileCardExcluded: 'form, [data-message-author-role="user"], [role="dialog"], [aria-modal="true"]',
    hiddenContainer: '[inert], [aria-hidden="true"]',
    fileCardDownload: 'button[aria-label="Datei herunterladen"], button[aria-label="Download"]',
    alert: '[role="alert"]',
    dialog: '[role="dialog"], [aria-modal="true"]',
    previewTextbox: '[role="dialog"] .cm-content[role="textbox"], [role="dialog"] .cm-content, ' +
      '.cm-content[role="textbox"], [role="textbox"][aria-label]',
    dialogClose: '[data-testid="close-button"], button[aria-label="Vollbildmodus beenden"], ' +
      'button[aria-label="Exit full screen"], button[aria-label="Schließen"], ' +
      'button[aria-label="Close"], button',
  });
})();

// AGP_SELECTOR_TABLE_V1: the one way an expression reaches the page world with the table.
globalThis.agpPageExpression = expression =>
  `(() => { const AGP_SELECTORS = ${JSON.stringify(globalThis.AGP_SELECTORS)}; return (${expression}); })()`;
