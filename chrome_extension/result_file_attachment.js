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

    await chromeApi.debugger.sendCommand(target, "Runtime.callFunctionOn", {
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

    return {ok: true, stage: "RESULT_FILE_ATTACHED", file_path: filePath};
  }

  globalThis.AGPResultFileAttachment = Object.freeze({attachResultFile});
})();
