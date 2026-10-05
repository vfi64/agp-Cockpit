/* K07 result-file attachment seam.
 * Transport only: no workflow semantics, no JSON-in-composer fallback.
 *
 * AGP_K07_RESULT_ATTACHMENT_EVIDENCE_V2
 * Live 2026-09-30: both evidence files were visibly attached in the ChatGPT
 * composer, yet the previous confirmation (re-dispatching input/change and
 * then reading `input.files`) reported failure and the continuation was never
 * sent. DOM.setFileInputFiles already dispatches the selection events; the
 * page consumes the files and may clear the input. Confirmation is therefore
 * the appearance of every evidence file name (fresh, step-scoped names) in the
 * composer after the selection, not the transient state of the input element.
 *
 * AGP_RESULT_ATTACHMENT_COMPOSER_BOUND_V1
 * Live 2026-10-05: the ChatGPT start page renders three composer forms (two of
 * them 0x0), each with its own enabled file inputs. Selecting the first file
 * input of the whole document put the evidence into an invisible composer and
 * the mission start failed. The file input and the evidence are now bound to
 * the form of the composer that agpResolveComposer (the same identity used for
 * text insertion) resolves. There is no document-wide file-input fallback.
 */
(() => {
  "use strict";

  function presenceExpression(names, resolverSource) {
    return `(() => {
      const names = ${JSON.stringify(names)};
      const composer = (${resolverSource})();
      const root = composer && typeof composer.closest === "function" ? composer.closest('form') : null;
      const textsOf = el => [
        String(el.textContent || ""),
        String((el.getAttribute && el.getAttribute('aria-label')) || ""),
        String((el.getAttribute && el.getAttribute('title')) || "")
      ].map(value => value.replace(/\\s+/g, " ").trim()).filter(Boolean);
      const matches = (text, name) => {
        if (text.includes(name)) return true;
        const truncated = text.match(/^(.*?)(?:…|\\.\\.\\.)$/);
        const prefix = truncated ? truncated[1].trim() : "";
        return prefix.length >= 12 && name.startsWith(prefix);
      };
      const count = (scope, name) => {
        if (!scope) return 0;
        let hits = 0;
        for (const el of scope.querySelectorAll('*')) {
          const labelled = el.hasAttribute('aria-label') || el.hasAttribute('title');
          if (el.children.length && !labelled) continue;
          if (textsOf(el).some(text => matches(text, name))) hits += 1;
        }
        return hits;
      };
      const sample = root
        ? Array.from(root.querySelectorAll('*'))
            .filter(el => !el.children.length)
            .map(el => String(el.textContent || "").replace(/\\s+/g, " ").trim())
            .filter(Boolean).slice(-10).map(text => text.slice(0, 60))
        : [];
      return {
        composer_found: Boolean(root),
        in_composer: names.map(name => count(root, name)),
        in_document: names.map(name => count(document.body, name)),
        composer_sample: sample
      };
    })()`;
  }

  async function attachResultFiles(chromeApi, target, filePaths, options = {}) {
    if (!chromeApi || !chromeApi.debugger || typeof chromeApi.debugger.sendCommand !== "function") {
      throw new Error("chrome debugger API unavailable");
    }
    if (!target || typeof target.tabId !== "number") {
      throw new Error("valid debugger target required");
    }
    if (!Array.isArray(filePaths) || filePaths.length < 1 || filePaths.some((filePath) => typeof filePath !== "string" || !filePath.startsWith("/"))) {
      throw new Error("absolute local file paths required");
    }
    const expectedNames = filePaths.map((filePath) => filePath.split("/").pop()).filter(Boolean);
    if (expectedNames.length !== filePaths.length) {
      throw new Error("absolute local file paths required");
    }
    const confirmTimeoutMs = Number(options.confirmTimeoutMs || 10000);
    const settleMs = Number(options.settleMs === undefined ? 2000 : options.settleMs);
    const resolveComposer = options.resolveComposer || globalThis.agpResolveComposer;
    if (typeof resolveComposer !== "function") {
      throw new Error("ChatGPT composer resolver unavailable");
    }
    const resolverSource = resolveComposer.toString();

    let attached = false;
    try {
      await chromeApi.debugger.attach(target, "1.3");
      attached = true;
      const evaluateValue = async expression => {
        const result = await chromeApi.debugger.sendCommand(target, "Runtime.evaluate", {
          expression, returnByValue: true, awaitPromise: true
        });
        return result && result.result ? result.result.value : null;
      };
      const presence = () => evaluateValue(presenceExpression(expectedNames, resolverSource));

      const before = await presence();
      // Re-delivery after a failed send: the evidence can still be attached in
      // the composer. Attaching again would duplicate it.
      if (before && before.composer_found && before.in_composer.every(hits => hits > 0)) {
        return {ok: true, stage: "RESULT_FILES_ATTACHED", file_paths: filePaths, file_names: expectedNames,
          evidence: "already_in_composer"};
      }

      const evaluate = await chromeApi.debugger.sendCommand(target, "Runtime.evaluate", {
        expression: `(() => {
          const composer = (${resolverSource})();
          const form = composer && typeof composer.closest === "function" ? composer.closest("form") : null;
          if (!form) return null;
          const inputs = Array.from(form.querySelectorAll('input[type="file"]'));
          return inputs.find((el) => !el.disabled) || null;
        })()`,
        returnByValue: false,
        userGesture: true
      });
      const objectId = evaluate && evaluate.result && evaluate.result.objectId;
      if (!objectId) {
        throw new Error("ChatGPT file input not found in the active composer form");
      }

      // DOM.setFileInputFiles dispatches the input/change events itself.
      // Do not dispatch them again: the page has already consumed the files.
      await chromeApi.debugger.sendCommand(target, "DOM.setFileInputFiles", {
        files: filePaths,
        objectId
      });

      const baseline = before || {composer_found: false, in_composer: expectedNames.map(() => 0), in_document: expectedNames.map(() => 0)};
      const deadline = Date.now() + confirmTimeoutMs;
      let observed = null;
      let evidence = "";
      const grew = scope => expectedNames.every((_, index) =>
        Number((observed[scope] || [])[index] || 0) > Number((baseline[scope] || [])[index] || 0));
      while (true) {
        observed = await presence();
        if (observed) {
          // Prefer evidence inside the active composer form; the chips may be
          // rendered outside the form, so a document-wide increase still counts
          // but is reported as the weaker "document" evidence.
          if (observed.composer_found && grew("in_composer")) { evidence = "composer"; break; }
          if (grew("in_document")) { evidence = "document"; break; }
        }
        if (Date.now() >= deadline) {
          throw new Error(
            "ChatGPT composer did not show the selected result evidence files: " +
            JSON.stringify({expected: expectedNames, before: baseline, observed})
          );
        }
        await new Promise(resolve => setTimeout(resolve, 250));
      }

      // Give ChatGPT's attachment state a bounded settling window before the
      // continuation prompt is submitted in the next browser operation.
      if (settleMs > 0) await new Promise(resolve => setTimeout(resolve, settleMs));

      return {ok: true, stage: "RESULT_FILES_ATTACHED", file_paths: filePaths, file_names: expectedNames,
        evidence};
    } finally {
      if (attached) {
        try { await chromeApi.debugger.detach(target); } catch (_) {}
      }
    }
  }

  async function attachResultFile(chromeApi, target, filePath) {
    const result = await attachResultFiles(chromeApi, target, [filePath]);
    return {ok: result.ok, stage: "RESULT_FILE_ATTACHED", file_path: filePath, file_name: result.file_names[0]};
  }

  globalThis.AGPResultFileAttachment = Object.freeze({attachResultFile, attachResultFiles});
})();
