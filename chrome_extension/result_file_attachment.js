/* K07 result-file attachment seam.
 * Transport only: no workflow semantics, no JSON-in-composer fallback.
 */
(() => {
  "use strict";

  async function attachResultFile(chromeApi, target, filePath) {
    if (!chromeApi || !chromeApi.debugger || typeof chromeApi.debugger.sendCommand !== "function") {
      throw new Error("chrome debugger API unavailable");
    }
    if (!target || typeof target.tabId !== "number") {
      throw new Error("valid debugger target required");
    }
    if (typeof filePath !== "string" || !filePath.startsWith("/")) {
      throw new Error("absolute local file path required");
    }

    let attached = false;
    try {
      await chromeApi.debugger.attach(target, "1.3");
      attached = true;
      const evaluate = await chromeApi.debugger.sendCommand(target, "Runtime.evaluate", {
        expression: `(() => {
          const inputs = Array.from(document.querySelectorAll('input[type="file"]'));
          const usable = inputs.find((el) => !el.disabled) || null;
          return usable;
        })()`,
        returnByValue: false,
        userGesture: true
      });

      const objectId = evaluate && evaluate.result && evaluate.result.objectId;
      if (!objectId) {
        throw new Error("ChatGPT file input not found");
      }

      await chromeApi.debugger.sendCommand(target, "DOM.setFileInputFiles", {
        files: [filePath],
        objectId
      });

      const confirmation = await chromeApi.debugger.sendCommand(target, "Runtime.callFunctionOn", {
        objectId,
        functionDeclaration: `function () {
          this.dispatchEvent(new Event('input', {bubbles: true}));
          this.dispatchEvent(new Event('change', {bubbles: true}));
          return {
            files: this.files ? Array.from(this.files).map((f) => f.name) : [],
            disabled: !!this.disabled
          };
        }`,
        returnByValue: true,
        userGesture: true
      });

      const names = confirmation && confirmation.result && confirmation.result.value &&
        Array.isArray(confirmation.result.value.files)
        ? confirmation.result.value.files.map(String)
        : [];
      const expectedName = filePath.split("/").pop();
      if (!expectedName || !names.includes(expectedName)) {
        throw new Error("ChatGPT file input did not confirm the selected result file");
      }

      // Give ChatGPT's attachment state a bounded settling window before the
      // continuation prompt is submitted in the next browser operation.
      await new Promise(resolve => setTimeout(resolve, 2000));

      return {ok: true, stage: "RESULT_FILE_ATTACHED", file_path: filePath, file_name: expectedName};
    } finally {
      if (attached) {
        try { await chromeApi.debugger.detach(target); } catch (_) {}
      }
    }
  }

  globalThis.AGPResultFileAttachment = Object.freeze({attachResultFile});
})();
