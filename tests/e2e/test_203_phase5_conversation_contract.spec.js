const {test, expect} = require("@playwright/test");
const path = require("path");

const ROOT = process.env.AGP_COCKPIT_ROOT ||
  path.resolve(__dirname, "../..");
const CONTRACT = path.join(
  ROOT, "chrome_extension", "conversation_contract.js"
);

async function install(page, {url="https://chatgpt.com/c/phase5-target"}={}) {
  await page.goto(url);

  await page.setContent(`
    <!doctype html>
    <html>
      <body>
        <main>
          <div id="messages">
            <div data-message-author-role="assistant">baseline response</div>
          </div>
          <form id="composer-form">
            <textarea id="prompt-textarea"></textarea>
            <button data-testid="send-button" type="submit">Send</button>
          </form>
        </main>
      </body>
    </html>
  `);

  await page.evaluate(() => {
    window.__sent = [];
    window.__store = {
      conversationUrl: "https://chatgpt.com/c/phase5-target"
    };
    window.chrome = {
      storage: {
        local: {
          get: async defaults => Object.assign({}, defaults || {}, window.__store),
          set: async values => Object.assign(window.__store, values || {})
        }
      }
    };
    const form = document.querySelector("#composer-form");
    form.addEventListener("submit", event => {
      event.preventDefault();
      const composer = document.querySelector("#prompt-textarea");
      window.__sent.push(composer.value);
      const user = document.createElement("div");
      user.setAttribute("data-message-author-role", "user");
      user.textContent = composer.value;
      document.querySelector("#messages").appendChild(user);
      composer.value = "";
    });
  });

  await page.addScriptTag({path: CONTRACT});
}

test("configured conversation binds exactly and foreign conversation fails closed", async ({page}) => {
  await install(page);
  const bound = await page.evaluate(() =>
    AGPCockpitConversationContract.bindConfiguredConversation()
  );
  expect(bound.conversationUrl).toBe("https://chatgpt.com/c/phase5-target");

  await page.evaluate(() => {
    window.__store.conversationUrl = "https://chatgpt.com/c/other";
  });

  const error = await page.evaluate(async () => {
    try {
      await AGPCockpitConversationContract.bindConfiguredConversation();
      return "";
    } catch (err) {
      return String(err);
    }
  });
  expect(error).toContain("PHASE5_CONVERSATION_MISMATCH");
});

test("draft insertion never sends by itself", async ({page}) => {
  await install(page);
  const staged = await page.evaluate(() =>
    AGPCockpitConversationContract.stageDraft("result to review")
  );
  expect(staged.chars).toBeGreaterThan(0);
  expect(await page.locator("#prompt-textarea").inputValue())
    .toBe("result to review");
  expect(await page.evaluate(() => window.__sent.slice())).toEqual([]);
});

test("send requires explicit approval and approval is bound to exact draft", async ({page}) => {
  await install(page);
  await page.evaluate(() =>
    AGPCockpitConversationContract.stageDraft("approved draft")
  );

  const withoutApproval = await page.evaluate(async () => {
    try {
      await AGPCockpitConversationContract.sendApprovedDraft(null);
      return "";
    } catch (err) {
      return String(err);
    }
  });
  expect(withoutApproval).toContain("PHASE5_APPROVAL_MISSING_OR_STALE");
  expect(await page.evaluate(() => window.__sent.slice())).toEqual([]);

  await page.evaluate(async () => {
    window.__approval =
      await AGPCockpitConversationContract.approveCurrentDraft();
    document.querySelector("#prompt-textarea").value = "changed after approval";
  });

  const changed = await page.evaluate(async () => {
    try {
      await AGPCockpitConversationContract.sendApprovedDraft(window.__approval);
      return "";
    } catch (err) {
      return String(err);
    }
  });
  expect(changed).toContain("PHASE5_APPROVAL_DRAFT_CHANGED");
  expect(await page.evaluate(() => window.__sent.slice())).toEqual([]);
});

test("approved unchanged draft sends exactly once", async ({page}) => {
  await install(page);
  await page.evaluate(async () => {
    await AGPCockpitConversationContract.stageDraft("send once");
    const approval =
      await AGPCockpitConversationContract.approveCurrentDraft();
    await AGPCockpitConversationContract.sendApprovedDraft(approval);
  });

  expect(await page.evaluate(() => window.__sent.slice()))
    .toEqual(["send once"]);
});

test("completed assistant detection rejects streaming and detects next stable response", async ({page}) => {
  await install(page);
  const baseline = await page.evaluate(async () => {
    const snap =
      await AGPCockpitConversationContract.currentAssistantSnapshot();
    const stop = document.createElement("button");
    stop.dataset.testid = "stop-button";
    stop.textContent = "Stop";
    document.body.appendChild(stop);
    return snap.fingerprint;
  });

  const streamingError = await page.evaluate(async () => {
    try {
      await AGPCockpitConversationContract.currentAssistantSnapshot();
      return "";
    } catch (err) {
      return String(err);
    }
  });
  expect(streamingError).toContain("PHASE5_ASSISTANT_STILL_STREAMING");

  const next = await page.evaluate(async baselineFingerprint => {
    const stop = document.querySelector('[data-testid="stop-button"]');
    setTimeout(() => {
      stop.remove();
      const node = document.createElement("div");
      node.setAttribute("data-message-author-role", "assistant");
      node.textContent = "next completed response";
      document.querySelector("#messages").appendChild(node);
    }, 120);

    return AGPCockpitConversationContract.waitForCompletedAssistant({
      afterFingerprint: baselineFingerprint,
      timeoutMs: 5000,
      pollMs: 50,
      stablePolls: 3
    });
  }, baseline);

  expect(next.text).toBe("next completed response");
  expect(next.fingerprint).not.toBe(baseline);
  expect(next.stablePolls).toBeGreaterThanOrEqual(3);
});

test("conversation change invalidates an existing approval permanently", async ({page}) => {
  await install(page);
  await page.evaluate(async () => {
    await AGPCockpitConversationContract.stageDraft("bound draft");
    window.__approval = await AGPCockpitConversationContract.approveCurrentDraft();
    history.pushState({}, "", "/c/phase5-other");
  });

  const changed = await page.evaluate(async () => {
    try {
      await AGPCockpitConversationContract.sendApprovedDraft(window.__approval);
      return "";
    } catch (err) {
      return String(err);
    }
  });
  expect(changed).toContain("PHASE5_CONVERSATION_MISMATCH");
  expect(await page.evaluate(() => window.__sent.slice())).toEqual([]);

  await page.evaluate(() => history.pushState({}, "", "/c/phase5-target"));
  const reused = await page.evaluate(async () => {
    try {
      await AGPCockpitConversationContract.sendApprovedDraft(window.__approval);
      return "";
    } catch (err) {
      return String(err);
    }
  });
  expect(reused).toContain("PHASE5_APPROVAL_MISSING_OR_STALE");
  expect(await page.evaluate(() => window.__sent.slice())).toEqual([]);
});

test("duplicate rendering of the previous response is not accepted as next response", async ({page}) => {
  await install(page);
  const baseline = await page.evaluate(async () =>
    (await AGPCockpitConversationContract.currentAssistantSnapshot()).fingerprint
  );

  const next = await page.evaluate(async baselineFingerprint => {
    setTimeout(() => {
      const duplicate = document.createElement("div");
      duplicate.setAttribute("data-message-author-role", "assistant");
      duplicate.textContent = "baseline response";
      document.querySelector("#messages").appendChild(duplicate);
    }, 60);
    setTimeout(() => {
      const actual = document.createElement("div");
      actual.setAttribute("data-message-author-role", "assistant");
      actual.textContent = "genuinely new response";
      document.querySelector("#messages").appendChild(actual);
    }, 260);

    return AGPCockpitConversationContract.waitForCompletedAssistant({
      afterFingerprint: baselineFingerprint,
      timeoutMs: 5000,
      pollMs: 40,
      stablePolls: 3
    });
  }, baseline);

  expect(next.text).toBe("genuinely new response");
  expect(next.fingerprint).not.toBe(baseline);
});

test("DOM text mutation resets stability before completion", async ({page}) => {
  await install(page);
  const baseline = await page.evaluate(async () =>
    (await AGPCockpitConversationContract.currentAssistantSnapshot()).fingerprint
  );

  const next = await page.evaluate(async baselineFingerprint => {
    const node = document.createElement("div");
    node.setAttribute("data-message-author-role", "assistant");
    node.textContent = "partial";
    document.querySelector("#messages").appendChild(node);
    setTimeout(() => { node.textContent = "partial but changed"; }, 55);
    setTimeout(() => { node.textContent = "final stable response"; }, 115);

    return AGPCockpitConversationContract.waitForCompletedAssistant({
      afterFingerprint: baselineFingerprint,
      timeoutMs: 5000,
      pollMs: 40,
      stablePolls: 3
    });
  }, baseline);

  expect(next.text).toBe("final stable response");
  expect(next.stablePolls).toBeGreaterThanOrEqual(3);
});

test("re-rendering identical previous response does not create a new response", async ({page}) => {
  await install(page);
  const baseline = await page.evaluate(async () =>
    (await AGPCockpitConversationContract.currentAssistantSnapshot()).fingerprint
  );

  const result = await page.evaluate(async baselineFingerprint => {
    setTimeout(() => {
      const messages = document.querySelector("#messages");
      const old = messages.querySelector('[data-message-author-role="assistant"]');
      old.remove();
      const replacement = document.createElement("div");
      replacement.setAttribute("data-message-author-role", "assistant");
      replacement.textContent = "baseline response";
      messages.appendChild(replacement);
    }, 60);

    try {
      await AGPCockpitConversationContract.waitForCompletedAssistant({
        afterFingerprint: baselineFingerprint,
        timeoutMs: 450,
        pollMs: 40,
        stablePolls: 3
      });
      return "unexpected-response";
    } catch (err) {
      return String(err);
    }
  }, baseline);

  expect(result).toContain("PHASE5_COMPLETED_ASSISTANT_TIMEOUT");
});
