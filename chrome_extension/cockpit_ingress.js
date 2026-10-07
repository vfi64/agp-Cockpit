// AGP_INGRESS_MODULE_V1 (content.js split, module 2, owner 2026-10-07): the file ingress — from a
// file card in ChatGPT's answer to the bridge. Finds the card of the expected step (command
// work order or terminal reply), materializes it (link, button download or preview), submits it
// to /v1/file-loop/command-file or the terminal route and forgets the browser copy afterwards.
// content.js stays the controller: it creates the module once (AGP_INGRESS.create) with its
// state and the services named below and calls the exported functions. Page lookups go through
// AGP_DOM / AGP_SELECTORS; the module never sends a prompt and never renders.
(() => {
  function create(host) {
    const STATE = host.state;
    const self = {};
    const api = (...args) => host.api(...args);
    const clientEvent = (...args) => host.clientEvent(...args);
    const composer = (...args) => host.composer(...args);
    const assistantBaselineIds = (...args) => host.assistantBaselineIds(...args);
    const selectedAssistantMessageNode = (...args) => host.selectedAssistantMessageNode(...args);
    const lastAssistantMessageId = (...args) => host.lastAssistantMessageId(...args);
    const reserveRemoteStep = (...args) => host.reserveRemoteStep(...args);
    const snapshotAssistantBaseline = (...args) => host.snapshotAssistantBaseline(...args);
    const applyAssistantBaseline = (...args) => host.applyAssistantBaseline(...args);

    function pythonAttachmentRow(anchor) {
      return AGP_DOM.fileCardRow(anchor);   // AGP_DOM_ADAPTER_V1
    }

    // AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1
    // The local bridge assigns a fresh work-order number for every remote turn
    // and reserves every number that may already be visible remotely. A file
    // card named <expectedStep>_*.py is therefore the identity of the awaited
    // response, exactly like the send nonce identifies the committed user turn.
    // Discovery must not depend on assistant-turn wrappers: on 2026-09-30 the
    // live DOM exposed the 1475 file card while no assistant node was found for
    // 180 s. Composer, user-turn and dialog copies are excluded; the first card
    // in document order wins among identical names.
    function expectedStepAttachmentCandidates(expectedStep, kind="command") {
      // AGP_K07_TERMINAL_REPLY_FILE_V1: a terminal answer is the file card
      // <expectedStep>_agp_terminal.json, with the same identity rules.
      // AGP_COMPOSER_RESOLVER_V1: cards in hidden/inert containers are skipped.
      return AGP_DOM.stepFileCards(expectedStep, kind);   // AGP_DOM_ADAPTER_V1
    }

    function expectedStepFileVisible(step) {
      return self.expectedStepAttachmentCandidates(step).length > 0 ||
        self.expectedStepAttachmentCandidates(step, "terminal").length > 0;
    }

    function expectedStepTerminalCandidates() {
      const step = Number(STATE.nextLocalStep || 0);
      return step > 0 ? self.expectedStepAttachmentCandidates(step, "terminal") : [];
    }

    // AGP_K07_COMMAND_FILE_INGRESS_989
    function assistantPythonAttachmentCandidates() {
      const expectedStepIdentity = Number(STATE.nextLocalStep || 0);
      if (expectedStepIdentity > 0) {
        return self.expectedStepAttachmentCandidates(expectedStepIdentity);
      }
      const nodes = AGP_DOM.assistantTurns();
      if (!nodes.length) return [];
      const baselineNames = new Set(STATE.assistantBaselineAttachmentNames || []);
      // Use the same identity-aware selection as assistant text extraction. The
      // ChatGPT DOM can contain virtualized or stale assistant nodes alongside
      // the currently observed response.
      const baselineIds = assistantBaselineIds();
      const assistant = [...nodes].reverse().find(node => {
        const id = String(node.getAttribute("data-message-id") || "");
        if (id && baselineIds.has(id)) return false;
        return node.querySelector(AGP_SELECTORS.pythonFileControl);
      }) || selectedAssistantMessageNode();
      if (!assistant) return [];
      // ChatGPT currently renders the attachment card as a plain button with
      // visible filename text. Keep links and labelled controls supported, but
      // also inspect ordinary buttons so the real file-card DOM is covered.
      const rows = Array.from(assistant.querySelectorAll(AGP_SELECTORS.pythonFileRow))
        .map(anchor => AGP_DOM.fileCardRow(anchor))   // AGP_DOM_ADAPTER_V1 (the .py filter follows)
        .filter(item => (
          /\.py(?:$|[?#\s])/i.test(item.name || "") ||
          /\.py(?:$|[?#])/i.test(item.href || "")
        ))
        .filter(item =>
          (item.href || item.isButton)
        );
      const unique = new Map();
      for (const row of rows) unique.set(`${row.href}\n${row.name}`, row);
      const candidates = Array.from(unique.values());
      const expectedStep = Number(STATE.nextLocalStep || 0);
      if (expectedStep > 0) {
        return candidates.filter(item => {
          const match = String(item.name || "").match(/^(\d+)_/);
          return match && Number(match[1]) === expectedStep;
        });
      }
      // A stable message id does not prove that the attachment is new: an
      // in-flight assistant response can materialize after the baseline was
      // captured, and ChatGPT may recycle or expose that old response again.
      // The filename is therefore a second, mandatory turn boundary. A remote
      // retry must receive a new filename instead of being executed locally as
      // a fresh step.
      if (baselineNames.size) {
        return candidates.filter(item => !baselineNames.has(item.name));
      }
      return candidates;
    }

    // AGP_DOM_ADAPTER_V1 (slice 3c): the attachment preview is named by the page adapter.
    // Contract kept: a textbox inside a dialog, or one labelled with the file name
    // ([role="textbox"][aria-label], label === expectedName); its container holds close and
    // download (label === "herunterladen").
    function readableAttachmentPreview(filename) {
      return AGP_DOM.previewTextbox(filename);
    }

    function attachmentPreviewContainer(preview) {
      return AGP_DOM.previewContainer(preview);
    }

    function attachmentPreviewDownloadButton(preview) {
      return AGP_DOM.previewDownloadButton(preview);
    }

    async function materializeDownloadedAttachment(attachment, downloadNode) {
      if (!downloadNode || !downloadNode.isConnected) {
        throw new Error("K07 assistant attachment has no authoritative download control");
      }
      const armed = await chrome.runtime.sendMessage({
        type:"AGP_K07_ARM_COMMAND_FILE_DOWNLOAD",
        filename:attachment.name
      });
      if (!armed || armed.ok !== true) {
        throw new Error(armed && armed.error ? String(armed.error) : "K07 browser download could not be armed");
      }
      downloadNode.click();
      const downloaded = await chrome.runtime.sendMessage({
        type:"AGP_K07_WAIT_COMMAND_FILE_DOWNLOAD",
        filename:attachment.name
      });
      if (!downloaded || downloaded.ok !== true || !downloaded.download_path) {
        throw new Error(downloaded && downloaded.error ? String(downloaded.error) : "K07 browser download did not complete");
      }
      const fetched = await api("/v1/file-loop/download", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({filename:attachment.name, download_path:downloaded.download_path})
      });
      if (!fetched || fetched.ok !== true || fetched.stage !== "COMMAND_FILE_FETCHED" || typeof fetched.content !== "string" || !fetched.content.trim()) {
        throw new Error("K07 downloaded command file could not be materialized");
      }
      // AGP_K07_DOWNLOAD_PROVENANCE_V1: the bytes the bridge read must be the
      // bytes Chrome reported for this exact download item.
      const browserBytes = Number(downloaded.download_bytes || 0);
      if (browserBytes > 0 && Number(fetched.bytes || 0) !== browserBytes) {
        throw new Error(`K07 download size mismatch: browser ${browserBytes} bytes, bridge ${Number(fetched.bytes || 0)} bytes`);
      }
      await clientEvent("K07_ATTACHMENT_DOWNLOAD_USED", {
        filename:attachment.name,
        download_path:downloaded.download_path,
        download_id:downloaded.download_id || null,
        download_bytes:Number(downloaded.download_bytes || 0),
        chars:fetched.content.length
      });
      return {
        ok:true,
        stage:"COMMAND_FILE_FETCHED",
        filename:attachment.name,
        href:`chatgpt://assistant-download/${encodeURIComponent(attachment.name)}`,
        content:fetched.content,
        content_type:String(fetched.content_type || "text/x-python"),
        chars:fetched.content.length,
        download_sha256:String(fetched.sha256 || ""),
        download_id:Number.isInteger(downloaded.download_id) ? downloaded.download_id : null
      };
    }

    // AGP_DOWNLOAD_HYGIENE_V1: after the bridge has persisted an accepted file in
    // the repository, the browser copy in ~/Downloads is removed. Since
    // AGP_REJECTED_ORDER_KEPT_V1 the bridge also keeps a rejected work order beside
    // its rejection record, so its browser copy is removed as well.
    async function forgetBrowserDownload(fetched) {
      if (!fetched || !Number.isInteger(fetched.download_id)) return;
      try {
        const removed = await chrome.runtime.sendMessage({
          type:"AGP_K07_FORGET_DOWNLOAD",
          download_id:fetched.download_id,
          filename:fetched.filename
        });
        await clientEvent("K07_BROWSER_DOWNLOAD_REMOVED", {
          filename:fetched.filename,
          download_id:fetched.download_id,
          stage:String(removed && removed.stage || ""),
          ok:Boolean(removed && removed.ok)
        });
      } catch (_) {}
    }

    async function readAssistantButtonAttachment(attachment) {
      const button = attachment && attachment.node;
      if (!button || !button.isConnected) {
        throw new Error("K07 assistant attachment button is no longer connected");
      }
      if (attachment.downloadNode && attachment.downloadNode.isConnected) {
        const downloaded = await self.materializeDownloadedAttachment(attachment, attachment.downloadNode);
        const target = composer();
        if (target && target.isConnected) {
          const activeBefore = document.activeElement;
          if (activeBefore && activeBefore !== target && typeof activeBefore.blur === "function") {
            activeBefore.blur();
          }
          if (typeof window !== "undefined" && typeof window.focus === "function") window.focus();
          if (typeof target.focus === "function") target.focus();
        }
        return downloaded;
      }
      button.click();
      const deadline = Date.now() + 45000;
      let preview = null;
      while (Date.now() < deadline) {
        preview = self.readableAttachmentPreview(attachment.name);
        const previewText = preview
          ? String(preview.innerText || preview.textContent || "")
          : "";
        if (preview && previewText.trim()) break;
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      if (!preview) {
        const unavailableDialog = AGP_DOM.openDialog();   // AGP_DOM_ADAPTER_V1
        const closeUnavailable = AGP_DOM.dialogCloseControl(unavailableDialog);
        if (closeUnavailable) closeUnavailable.click();
        else if (unavailableDialog) {
          document.dispatchEvent(new KeyboardEvent("keydown", {key:"Escape", code:"Escape", bubbles:true, cancelable:true}));
        }
        throw new Error("K07 assistant attachment preview did not become readable");
      }
      const dialog = self.attachmentPreviewContainer(preview);
      const previewDownload = self.attachmentPreviewDownloadButton(preview);
      let downloadedContent = null;
      let downloadError = null;
      if (previewDownload) {
        try {
          downloadedContent = await self.materializeDownloadedAttachment(attachment, previewDownload);
        } catch (error) {
          downloadError = error;
        }
      } else {
        downloadError = new Error("K07 assistant attachment preview is not an authoritative payload; browser download is required");
      }
      const normalizedLabel = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();
      // AGP_DOM_ADAPTER_V1: the close control (label === "ok", close, schließen, exit full
      // screen; the focused button inside the dialog first) is named by the page adapter.
      const close = AGP_DOM.dialogCloseControl(dialog, document.activeElement);
      let closeMethod = "none";
      if (close) {
        close.click();
        closeMethod = normalizedLabel(close.textContent) === "ok" ? "dialog_ok" : "dialog_control";
      } else {
        document.dispatchEvent(new KeyboardEvent("keydown", {
          key:"Escape", code:"Escape", bubbles:true, cancelable:true
        }));
        closeMethod = "escape";
      }
      const closeDeadline = Date.now() + 3000;
      while (Date.now() < closeDeadline) {
        const stillOpen = dialog && dialog.isConnected && (() => {
          const rect = dialog.getBoundingClientRect();
          const style = getComputedStyle(dialog);
          return rect.width > 0 && rect.height > 0 &&
            style.display !== "none" && style.visibility !== "hidden";
        })();
        if (!stillOpen) break;
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      const stillOpen = dialog && dialog.isConnected && (() => {
        const rect = dialog.getBoundingClientRect();
        const style = getComputedStyle(dialog);
        return rect.width > 0 && rect.height > 0 &&
          style.display !== "none" && style.visibility !== "hidden";
      })();
      if (stillOpen) {
        throw new Error("K07 assistant attachment preview did not close");
      }

      // Closing the preview can leave focus on its now-detached OK button.
      // Restore and verify composer ownership before the background transport
      // attaches the result files and sends the recovery prompt.
      const focusDeadline = Date.now() + 1500;
      let focusEvidence = null;
      while (Date.now() < focusDeadline) {
        const target = composer();
        if (target && target.isConnected) {
          const activeBefore = document.activeElement;
          if (activeBefore && activeBefore !== target && typeof activeBefore.blur === "function") {
            activeBefore.blur();
          }
          if (typeof window.focus === "function") window.focus();
          if (typeof target.focus === "function") target.focus();
          focusEvidence = {
            focused: document.activeElement === target,
            active_tag: document.activeElement ? document.activeElement.tagName : "",
            active_id: document.activeElement ? document.activeElement.id : "",
            composer_tag: target.tagName,
            composer_id: target.id || ""
          };
          if (focusEvidence.focused) break;
        }
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      if (!focusEvidence || !focusEvidence.focused) {
        throw new Error("K07 composer focus could not be restored after attachment preview");
      }
      await clientEvent("K07_ATTACHMENT_PREVIEW_CLOSED", {
        filename:attachment.name,
        method:closeMethod,
        composer_focus:focusEvidence
      });
      if (downloadError) throw downloadError;
      return downloadedContent;
    }

    async function fetchSingleAssistantPythonAttachment(candidates = self.assistantPythonAttachmentCandidates()) {
      if (candidates.length !== 1) {
        throw new Error(
          `expected exactly one assistant remote-file attachment; observed ${candidates.length}`
        );
      }
      const attachment = candidates[0];
      if (!attachment.href && attachment.isButton) {
        return self.readAssistantButtonAttachment(attachment);
      }
      const response = await chrome.runtime.sendMessage({
        type:"AGP_K07_COMMAND_FILE_FETCH",
        href:attachment.href,
        filename:attachment.name
      });
      if (!response || response.ok !== true || response.stage !== "COMMAND_FILE_FETCHED") {
        throw new Error(
          response && response.error
            ? String(response.error)
            : "assistant .py attachment could not be materialized"
        );
      }
      return response;
    }

    // AGP_K07_TERMINAL_REPLY_FILE_V1: materialize the terminal file through the
    // same download/provenance path and let the bridge decide the final state.
    async function submitAssistantTerminalReply(candidates) {
      const fetched = await self.fetchSingleAssistantPythonAttachment(candidates);
      const result = await api("/v1/file-loop/terminal", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          filename:fetched.filename,
          content:fetched.content,
          download_sha256:fetched.download_sha256 || undefined
        })
      });
      // AGP_CI_GREEN_COMPLETION_V1: the Cockpit may reject a remote DONE (CI not
      // green) and continue the task with a prompt instead of ending it.
      const continued = result && result.terminal === false && String(result.state || "") === "CONTINUE" &&
        typeof result.prompt === "string" && result.prompt.length > 0;
      if (!result || (!continued && (result.terminal !== true ||
          !["DONE", "NEEDS_HUMAN"].includes(String(result.state || ""))))) {
        throw new Error("K07 terminal-reply bridge response incomplete");
      }
      await clientEvent("K07_TERMINAL_REPLY_OBSERVED", {
        filename:fetched.filename,
        state:String(result.state),
        remote_state:String(result.remote_state || ""),
        authority:String(result.authority || ""),
        replayed:Boolean(result.replayed)
      });
      void self.forgetBrowserDownload(fetched);
      return result;
    }

    async function submitAssistantCommandFile(runGeneration = STATE.runGeneration) {
      await clientEvent("K07_FILE_INGRESS_REQUESTED", {
        stage:"FETCH_ATTACHMENT",
        message_id:lastAssistantMessageId()
      });
      const fetched = await self.fetchSingleAssistantPythonAttachment();
      await clientEvent("K07_FILE_INGRESS_ATTACHMENT_FETCHED", {
        filename:fetched.filename,
        chars:Number(fetched.chars || String(fetched.content || "").length)
      });
      const result = await api(
        "/v1/file-loop/command",
        {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({
            filename:fetched.filename,
            content:fetched.content,
            href:fetched.href,
            download_sha256:fetched.download_sha256 || undefined,
            message_id:lastAssistantMessageId()
          })
        }
      );
      const terminal = Boolean(result && result.terminal === true);
      // AGP_CORRECTABLE_REJECTION_V1: the work order broke the command authority,
      // was not executed and the remote side gets a correction prompt.
      const rejectedForCorrection = Boolean(result && result.terminal === false &&
        String(result.state || "") === "CONTINUE" && typeof result.prompt === "string" && result.prompt);
      if (rejectedForCorrection) {
        await clientEvent("K07_WORK_ORDER_REJECTED_FOR_CORRECTION", {
          filename:fetched.filename,
          next_step:Number(result.next_step || 0)
        });
        void self.forgetBrowserDownload(fetched);   // AGP_REJECTED_ORDER_KEPT_V1
        return result;
      }
      if (
        !result ||
        (result.state !== "COMMAND_FILE" && !terminal) ||
        (!terminal && (typeof result.result_file !== "string" || !result.result_file)) ||
        (!terminal && result.held !== true &&
          (result.replayed !== true || result.delivery_pending === true) &&
          (typeof result.prompt !== "string" || !result.prompt))
      ) {
        throw new Error("K07 command-file bridge response incomplete");
      }
      await clientEvent("K07_FILE_INGRESS_ACCEPTED", {
        filename:fetched.filename,
        state:String(result.state || ""),
        step:Number(result.step || 0),
        terminal,
        replayed:Boolean(result.replayed)
      });
      void self.forgetBrowserDownload(fetched);
      // AGP_K07_ADVANCE_STEP_AFTER_DELIVERY_V1: the expected step is the
      // identity of the awaited remote response. It advances only when the
      // result reached the remote side (or delivery is not required). Advancing
      // earlier hid the current card after a failed delivery (live 2026-09-30:
      // expected 1477 while 1476 still needed re-delivery).
      const advanceExpectedStep = () => {
        if (Number(result.next_step || 0) > 0) {
          STATE.nextLocalStep = Number(result.next_step);
        }
      };
      // AGP_K07_DELIVERY_STATE_V1: a replay whose earlier delivery was never
      // confirmed is re-delivered; a confirmed one is suppressed. A result held
      // by operator PAUSE is not sent now; it is re-delivered after resume.
      if (result.held === true) {
        return result;
      }
      if (terminal) {
        advanceExpectedStep();
        return result;
      }
      if (result.replayed === true && result.delivery_pending !== true) {
        advanceExpectedStep();
        return result;
      }
      if (!STATE.running || STATE.runGeneration !== runGeneration) {
        await clientEvent("K07_CONTINUATION_SUPPRESSED_BY_GENERATION", {
          step:Number(result.step || 0),
          result_sha256:result.result_sha256 || null
        });
        return Object.assign({}, result, {delivery_skipped:true});
      }
      const upcomingStep = Number(result.next_step || 0);
      if (upcomingStep > 0 && self.expectedStepFileVisible(upcomingStep)) {
        // The continuation would ask for a number that is already visible;
        // its stale card would be consumed as the next response. Fail closed.
        const currentExpectedStep = STATE.nextLocalStep;
        await reserveRemoteStep("visible-unmaterialized-remote-attachment", upcomingStep);
        STATE.nextLocalStep = currentExpectedStep;
        throw new Error(`K07 next step ${upcomingStep} is already visible in the conversation; continuation not sent`);
      }
      const nextBaseline = snapshotAssistantBaseline();
      // AGP_K07_RESULT_CONTINUATION_CALL_991
      const continuation = await chrome.runtime.sendMessage({
        type:"AGP_K07_RESULT_CONTINUATION",
        result_file:result.result_file,
        output_file:result.output_file || null,
        prompt:result.prompt,
        cycle_id:result.cycle_id || null,
        result_sha256:result.result_sha256 || null
      });
      if (!continuation || continuation.ok !== true || continuation.stage !== "RESULT_ATTACHED_AND_CONTINUATION_SENT") {
        throw new Error(continuation && continuation.error ? String(continuation.error) : "result continuation transport failed");
      }
      applyAssistantBaseline(nextBaseline);
      advanceExpectedStep();
      if (result.completion_pending !== true) {
        try {
          await api("/v1/file-loop/delivery-ack", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({cycle_id:result.cycle_id, result_sha256:result.result_sha256})
          });
        } catch (ackError) {
          // The continuation is committed; a later remote command implies
          // delivery. Never resend because only the acknowledgement failed.
          await clientEvent("K07_DELIVERY_ACK_FAILED", {
            result_sha256:result.result_sha256 || null,
            error:String(ackError && ackError.message ? ackError.message : ackError)
          });
        }
      }
      if (result.completion_pending === true) {
        const completed = await api("/v1/file-loop/result-delivered", {
          method:"POST",
          headers:{"Content-Type":"application/json"},
          body:JSON.stringify({cycle_id:result.cycle_id, result_sha256:result.result_sha256})
        });
        if (completed.state !== "DONE" || completed.terminal !== true) {
          throw new Error("handoff completion acknowledgement rejected");
        }
        return Object.assign({}, result, completed);
      }
      return result;
    }

    // Calls between these functions go through `self`, so a test can replace one step (for
    // example the materialization) and drive the rest; the object is sealed, never extended.
    Object.assign(self, {
      pythonAttachmentRow,
      expectedStepAttachmentCandidates,
      expectedStepFileVisible,
      expectedStepTerminalCandidates,
      assistantPythonAttachmentCandidates,
      readableAttachmentPreview,
      attachmentPreviewContainer,
      attachmentPreviewDownloadButton,
      materializeDownloadedAttachment,
      forgetBrowserDownload,
      readAssistantButtonAttachment,
      fetchSingleAssistantPythonAttachment,
      submitAssistantTerminalReply,
      submitAssistantCommandFile,
    });
    return Object.seal(self);
  }

  globalThis.AGP_INGRESS = Object.freeze({create});
})();
