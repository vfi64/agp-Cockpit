const { test } = require("@playwright/test");


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
      const original = globalThis.crypto;
      Object.defineProperty(globalThis, "crypto", {
        configurable: true,
        value: {
          subtle: {digest},
          getRandomValues: original && typeof original.getRandomValues === "function"
            ? original.getRandomValues.bind(original)
            : array => { for (let i = 0; i < array.length; i += 1) array[i] = Math.floor(Math.random() * 256); return array; }
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

test("066-B1-D1 trace actual content.js bootstrap path", async ({page}) => {
  await installCryptoSubtleHarness(page);
  const consoleLines = [];
  page.on("console", msg => consoleLines.push("CONSOLE:" + msg.type() + ":" + msg.text()));
  page.on("pageerror", err => consoleLines.push("PAGEERROR:" + String(err)));

  await page.setContent(`
    <!doctype html><html><body><main>
      <div data-message-author-role="assistant">previous assistant response</div>
      <form><!-- AGP_MISSION_TOUCHPOINT_SELFTEST_V1: composer, its form and a file input -->
      <textarea id="prompt-textarea"></textarea>
      <input type="file" multiple>
      <button data-testid="send-button" type="button">Send</button>
      </form>
    </main></body></html>
  `);

  await page.evaluate(() => {
    window.__agpStore = {
      token: "phase066-test-token",
      baseUrl: "http://127.0.0.1:9876"
    };
    window.__fetchLog = [];
    window.__mission = null;

    window.chrome = {
      storage: {local: {
        get: async (keys) => {
          const s = window.__agpStore;
          if (Array.isArray(keys)) {
            const out = {};
            for (const k of keys) if (k in s) out[k] = s[k];
            return out;
          }
          if (typeof keys === "string") return {[keys]: s[keys]};
          if (keys && typeof keys === "object") return Object.assign({}, keys, s);
          return Object.assign({}, s);
        },
        set: async values => Object.assign(window.__agpStore, values || {}),
        remove: async keys => {
          for (const k of (Array.isArray(keys) ? keys : [keys])) delete window.__agpStore[k];
        }
      }},
      runtime: {id:"phase066-test-extension"}
    };

    const reply = (data, status=200) =>
      new Response(JSON.stringify(data), {
        status,
        headers: {"Content-Type":"application/json"}
      });

    window.fetch = async (url, options={}) => {
      const u = new URL(String(url), "http://127.0.0.1:9876");
      const method = String(options.method || "GET").toUpperCase();
      let body = null;
      if (options.body) {
        try { body = JSON.parse(options.body); } catch (_) { body = String(options.body); }
      }
      window.__fetchLog.push({method, path:u.pathname, body});

      if (u.pathname === "/v1/mission" && method === "POST") {
        window.__mission = Object.assign({
          schema_version:1,
          mission_id:"phase066-b1-d1",
          repository_root:"/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit",
          state:"READY",
          current_step:0,
          turns:0
        }, body || {});
        return reply({state:"READY", mission:window.__mission});
      }

      if (u.pathname === "/v1/status") {
        return reply({
          state:window.__mission ? (window.__mission.state || "READY") : "IDLE",
          mission:window.__mission
        });
      }

      return reply({ok:true});
    };
  });

  // Manifest order (AGP_SELECTOR_TABLE_V1, AGP_PANEL_MODULE_V1).
  await page.addScriptTag({path: path.join(ROOT, "chrome_extension", "chatgpt_selectors.js")});
  await page.addScriptTag({path: path.join(ROOT, "chrome_extension", "native_message_evidence.js")});
  await page.addScriptTag({path: path.join(ROOT, "chrome_extension", "cockpit_panel.js")});
  await page.addScriptTag({path: path.join(ROOT, "chrome_extension", "cockpit_ingress.js")});
  await page.addScriptTag({path: path.join(ROOT, "chrome_extension", "chatgpt_dom.js")});
  await page.addScriptTag({path: CONTENT_JS});

  const send = page.locator('button[data-testid="send-button"]');
  await send.evaluate(button => {
    button.addEventListener("click", () => {
      setTimeout(() => {
        const a = document.querySelector('[data-message-author-role="assistant"]');
        if (a) a.textContent = "assistant accepted prompt";
      }, 120);
    });
  });

  const live3 = page.getByRole("button", {name:"③ LIVE 3-Turn"});
  const start = page.getByRole("button", {name:"Start Auto"});

  console.log("LIVE3_COUNT=" + await live3.count());
  console.log("START_COUNT=" + await start.count());

  if (await live3.count()) await live3.click();
  await page.waitForTimeout(250);

  console.log("AFTER_LIVE3_FETCH=" + JSON.stringify(await page.evaluate(() => window.__fetchLog)));
  console.log("AFTER_LIVE3_TEXT=" + (await page.locator("body").innerText()));

  if (await start.count()) await start.click();
  await page.waitForTimeout(4000);

  console.log("AFTER_START_FETCH=" + JSON.stringify(await page.evaluate(() => window.__fetchLog)));
  console.log("AFTER_START_TEXT=" + (await page.locator("body").innerText()));
  console.log("COMPOSER_VALUE=" + await page.locator("#prompt-textarea").inputValue());
  console.log("DIAGNOSTIC_CONSOLE=" + JSON.stringify(consoleLines));
});
