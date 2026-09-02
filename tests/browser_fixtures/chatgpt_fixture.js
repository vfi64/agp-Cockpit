(() => {
  const params = new URLSearchParams(location.search);
  const mode = params.get("mode") || "normal";
  const messages = document.getElementById("messages");
  const form = document.getElementById("composer-form");
  const composer = document.getElementById("prompt-textarea");

  window.__AGP_FIXTURE = {
    acceptedPrompts: [],
    assistantGenerationCount: 0,
    mode
  };

  function addMessage(role, text) {
    const node = document.createElement("div");
    node.setAttribute("data-message-author-role", role);
    node.textContent = text;
    messages.appendChild(node);
    return node;
  }

  function assistantJsonFor(prompt) {
    return JSON.stringify({
      kind: "generic",
      cwd: "/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit",
      argv: ["/usr/bin/git", "status", "--short"],
      timeout_seconds: 30,
      label: "066 fixture read-only status"
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const prompt = composer.value || composer.textContent || "";
    if (!prompt.trim()) return;

    if (mode === "real-send-failure") return;

    window.__AGP_FIXTURE.acceptedPrompts.push(prompt);
    composer.value = "";
    composer.dispatchEvent(new Event("input", {bubbles: true}));

    if (mode !== "missing-user-bubble") {
      const userText = mode === "normalized-user-bubble"
        ? prompt.replace(/\s+/g, " ").trim()
        : prompt;
      addMessage("user", userText);
    }

    window.setTimeout(() => {
      window.__AGP_FIXTURE.assistantGenerationCount += 1;
      addMessage("assistant", assistantJsonFor(prompt));
    }, 120);
  });

  window.__AGP_FIXTURE.addMessage = addMessage;
})();
