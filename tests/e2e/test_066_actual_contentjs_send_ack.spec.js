const { test, expect } = require("@playwright/test");


// AGP_PHASE066_PLAYWRIGHT_CRYPTO_SUBTLE_HARNESS
async function installCryptoSubtleHarness(page) {
  const cryptoHarnessInstaller = () => {
    const digest = async (_algorithm, data) => {
      const input = new Uint8Array(data);
      const output = new Uint8Array(32);

      // Deterministic test-only digest. It is intentionally not cryptographic:
      // content.js only needs a stable ArrayBuffer for change detection here.
      for (let i = 0; i < input.length; i += 1) {
        const slot = i % 32;
        output[slot] = (output[slot] + input[i] + ((i * 17) & 0xff)) & 0xff;
      }
      return output.buffer;
    };

    if (
      !globalThis.crypto ||
      !globalThis.crypto.subtle ||
      typeof globalThis.crypto.subtle.digest !== "function"
    ) {
      Object.defineProperty(globalThis, "crypto", {
        configurable: true,
        value: {
          subtle: {digest}
        }
      });
    }
  };

  await page.addInitScript(cryptoHarnessInstaller);
  await page.evaluate(cryptoHarnessInstaller);

  const ready = await page.evaluate(() =>
    Boolean(
      globalThis.crypto &&
      globalThis.crypto.subtle &&
      typeof globalThis.crypto.subtle.digest === "function"
    )
  );

  if (!ready) {
    throw new Error("phase066 inline crypto harness verification failed");
  }
}

const path = require("path");

const ROOT = path.resolve(__dirname, "../..");
const CONTENT_JS = path.join(ROOT, "chrome_extension", "content.js");

async function installBridgeMocks(page) {
  await page.setContent(`
    <!doctype html>
    <html>
      <body>
        <main>
          <div id="assistant" data-message-author-role="assistant">previous assistant response</div>
          <textarea id="prompt-textarea"></textarea>
          <button data-testid="send-button" type="button">Send</button>
        </main>
      </body>
    </html>
  `);

  await page.evaluate(() => {
    window.__agpStore = {
      token: "phase066-test-token",
      baseUrl: "http://127.0.0.1:9876"
    };
    window.__agpEvents = [];
    window.__agpMission = {schema_version:1, mission_id:"phase066-b1", title:"Task · Fixture", mission_text:"Test status", state:"READY", current_step:0, turns:0, execution_mode:"LIVE", run_mode:"FULL_AUTO"};

    const storageGet = async (keys) => {
      const store = window.__agpStore;
      if (Array.isArray(keys)) {
        const result = {};
        for (const key of keys) {
          if (Object.prototype.hasOwnProperty.call(store, key)) result[key] = store[key];
        }
        return result;
      }
      if (typeof keys === "string") return {[keys]: store[keys]};
      if (keys && typeof keys === "object") return Object.assign({}, keys, store);
      return Object.assign({}, store);
    };

    window.chrome = {
      storage: {
        local: {
          get: storageGet,
          set: async (values) => Object.assign(window.__agpStore, values || {}),
          remove: async (keys) => {
            for (const key of (Array.isArray(keys) ? keys : [keys])) delete window.__agpStore[key];
          }
        }
      },
      runtime: {
        id: "phase066-test-extension",
        onMessage: {addListener: () => {}}
      }
    };

    const jsonResponse = (data, status=200) =>
      new Response(JSON.stringify(data), {
        status,
        headers: {"Content-Type": "application/json"}
      });

    window.fetch = async (url, options={}) => {
      const u = new URL(String(url), "http://127.0.0.1:9876");
      const method = String(options.method || "GET").toUpperCase();
      let body = {};
      if (options.body) {
        try { body = JSON.parse(options.body); } catch (_) {}
      }

      if (u.pathname.includes("client-event")) {
        if (body && body.event) window.__agpEvents.push(body.event);
        return jsonResponse({ok:true});
      }

      if (u.pathname === "/v1/mission" && method === "POST") {
        window.__agpMission = Object.assign({
          schema_version: 1,
          mission_id: "phase066-b1",
          repository_root: "/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit",
          state: "READY",
          current_step: 0,
          turns: 0
        }, body || {});
        return jsonResponse({state:"READY", mission:window.__agpMission});
      }

      if (u.pathname === "/v1/status") {
        return jsonResponse({
          state: window.__agpMission ? (window.__agpMission.state || "READY") : "IDLE",
          mission: window.__agpMission
        });
      }

      if (u.pathname === "/v1/task/start-request" && method === "GET") {
        window.__agpStartRequestGeneration = Number(window.__agpStartRequestGeneration || 0) + 1;
        if (!window.__agpMission) {
          window.__agpMission = {
            schema_version: 1,
            mission_id: "phase066-b1",
            repository_root: "/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit",
            state: "READY",
            title: "Task · Fixture",
            mission_text: "Test status",
            current_step: 0,
            turns: 0,
            execution_mode: "LIVE",
            run_mode: "FULL_AUTO"
          };
        }
        return jsonResponse({
          generation: window.__agpStartRequestGeneration,
          mission_id: "phase066-b1"
        });
      }

      window.__agpEvents.push("UNEXPECTED_FETCH:" + method + ":" + u.pathname);
      return jsonResponse({error:"unexpected endpoint", path:u.pathname}, 500);
    };
  });

  await page.addScriptTag({path: path.join(ROOT, "chrome_extension/native_message_evidence.js")});
  await page.addScriptTag({path: CONTENT_JS});
  await expect(page.getByText("AGP Cockpit Bridge")).toBeVisible();
}

for (const stage of ["USER_TURN_COMMITTED", "USER_TURN_INDETERMINATE"]) {
  test("actual content.js handles native stage " + stage, async ({page}) => {
    await installCryptoSubtleHarness(page);
    await installBridgeMocks(page);
    await page.evaluate(stage => {
      window.AGPBrowserNativeTransport = {
        available: () => true,
        submit: async prompt => {
          if (stage === "USER_TURN_INDETERMINATE") {
            const node = document.createElement("div");
            node.dataset.messageAuthorRole = "user";
            node.textContent = prompt;
            document.querySelector("main").append(node);
          }
          return {stage, request_id:"fixture-native", tab_id:1};
        }
      };
    }, stage);
    await expect.poll(() => page.evaluate(() => window.__agpEvents)).toContain("MISSION_BOOTSTRAP_SENT");
    const events = await page.evaluate(() => window.__agpEvents);
    expect(events).not.toContain("MISSION_BOOTSTRAP_SEND_FAILED");
    if (stage === "USER_TURN_COMMITTED") expect(events).toContain("NATIVE_SEND_ACCEPTED");
    else expect(events).not.toContain("NATIVE_SEND_ACCEPTED");
  });
}
