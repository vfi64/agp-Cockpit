// AGP_PANEL_MODULE_V1 (content.js split, module 1, owner 2026-10-07): the AGP Cockpit Bridge
// overlay on the ChatGPT page — style, buttons, pills, drag/minimize state and render.
// content.js stays the controller: it owns STATE and the actions and creates the panel once
// (AGP_PANEL.create) before its first render. The panel reads STATE and calls back; it never
// talks to the bridge or the page itself. Manifest: loaded before chatgpt_dom.js and content.js.
(() => {
  const STYLE = `
    #agp-cockpit-bridge {
      position:fixed;right:18px;bottom:88px;z-index:2147483647;
      width:620px;max-width:calc(100vw - 36px);
      background:linear-gradient(180deg,#18202a,#111820);
      color:#eef4f8;border:1px solid #3b82a9;border-radius:12px;
      box-shadow:0 10px 28px rgba(0,0,0,.34);
      font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
      overflow:hidden;
    }
    #agp-cockpit-bridge * {box-sizing:border-box}
    #agp-cockpit-bridge .agp-head {
      display:flex;align-items:center;gap:8px;padding:10px 12px;
      border-bottom:1px solid rgba(255,255,255,.10);font-weight:700
    }
    /* AGP_OVERLAY_DRAG_MINIMIZE_063S2 */
    #agp-cockpit-bridge .agp-head {
      cursor:move;user-select:none
    }
    #agp-cockpit-bridge .agp-minimize {
      background:#263543;padding:2px 8px;min-height:24px;font-size:13px;
      line-height:1;border-radius:6px
    }
    #agp-cockpit-bridge.agp-minimized .agp-actions,
    #agp-cockpit-bridge.agp-minimized .agp-body,
    #agp-cockpit-bridge.agp-minimized .agp-debug {
      display:none
    }
    #agp-cockpit-bridge.agp-minimized .agp-head {
      border-bottom:0
    }
    #agp-cockpit-bridge .agp-grow {flex:1}
    #agp-cockpit-bridge .agp-dot {
      width:9px;height:9px;border-radius:50%;display:inline-block;background:#7c8791
    }
    #agp-cockpit-bridge .agp-dot.on {
      background:#35c759;box-shadow:0 0 8px rgba(53,199,89,.55)
    }
    /* AGP_BROWSER_BUSY_INDICATOR_064_R2 */
    #agp-cockpit-bridge .agp-busy {
      display:inline-flex;align-items:center;gap:6px;
      color:#8fdcff;font-size:11px;font-weight:700;white-space:nowrap
    }
    #agp-cockpit-bridge .agp-spinner {
      width:12px;height:12px;border-radius:50%;
      border:2px solid rgba(143,220,255,.30);
      border-top-color:#8fdcff;
      animation:agp-cockpit-spin .8s linear infinite
    }
    @keyframes agp-cockpit-spin {
      to { transform:rotate(360deg) }
    }

    #agp-cockpit-bridge .agp-pill {
      border:1px solid rgba(255,255,255,.22);border-radius:7px;
      padding:3px 8px;font-size:11px;font-weight:700;background:#222d38;color:#dbe7ee
    }
    #agp-cockpit-bridge .agp-pill.mode {
      border-color:#2d7fc0;color:#73c4ff;background:#12314b
    }
    #agp-cockpit-bridge .agp-pill.run {
      border-color:#8046bd;color:#d6a4ff;background:#35194d
    }
    #agp-cockpit-bridge .agp-actions {
      display:grid;grid-template-columns:repeat(6,1fr);gap:8px;
      padding:10px 12px;border-bottom:1px solid rgba(255,255,255,.10)
    }
    #agp-cockpit-bridge button {
      appearance:none;border:1px solid rgba(255,255,255,.18);border-radius:7px;
      padding:8px 7px;color:white;font-weight:700;cursor:pointer;min-height:38px
    }
    #agp-cockpit-bridge button:hover {filter:brightness(1.12)}
    #agp-cockpit-bridge .start {background:#238636}
    #agp-cockpit-bridge .stop {background:#b85d09}
    #agp-cockpit-bridge .mission {background:#145f91}
    #agp-cockpit-bridge .liveprobe {background:#8a2432}
    #agp-cockpit-bridge .next {background:#6531a8}
    #agp-cockpit-bridge .status {background:#236980}
    #agp-cockpit-bridge .agp-body {
      display:grid;grid-template-columns:145px 1fr 155px;min-height:90px
    }
    #agp-cockpit-bridge .agp-cell {
      padding:10px 12px;border-right:1px solid rgba(255,255,255,.08)
    }
    #agp-cockpit-bridge .agp-cell:last-child {border-right:0}
    #agp-cockpit-bridge .agp-label {color:#9fb0bc;font-size:11px;margin-bottom:4px}
    #agp-cockpit-bridge .agp-big {font-size:18px;font-weight:800}
    #agp-cockpit-bridge .agp-note {
      font-size:12px;line-height:1.35;color:#dbe7ee;overflow-wrap:anywhere
    }
    #agp-cockpit-bridge .agp-progress {
      margin-top:6px;height:5px;border-radius:999px;background:#303a43;overflow:hidden
    }
    #agp-cockpit-bridge .agp-progress > div {
      height:100%;background:#35c759;width:0%;transition:width .2s ease
    }
    #agp-cockpit-bridge .agp-debug {
      padding:6px 12px;border-top:1px solid rgba(255,255,255,.08);
      color:#9fc8dc;font-size:11px
    }
    #agp-cockpit-bridge .agp-error {color:#ff9a9a;font-weight:700}
  `;

  function create(host) {
    const STATE = host.state;
    const LIMITS = host.limits;

    function ensureStyle() {
      if (document.getElementById("agp-cockpit-style")) return;
      const style = document.createElement("style");
      style.id = "agp-cockpit-style";
      style.textContent = STYLE;
      document.documentElement.appendChild(style);
    }

    function btn(label, cls, handler) {
      const b = document.createElement("button");
      b.type = "button";
      b.className = cls;
      b.textContent = label;
      b.addEventListener("mousedown", event => event.stopPropagation());
      b.addEventListener("click", async event => {
        event.preventDefault();
        event.stopPropagation();

        STATE.lastEvent = "UI_BUTTON_CLICKED";
        STATE.note = `Button: ${label}`;
        render();
        await host.clientEvent("UI_BUTTON_CLICKED", {
          label,
          class_name:cls
        });

        try {
          await handler();
        } catch (err) {
          STATE.note = String(err);
          STATE.lastEvent = "UI_ACTION_ERROR";
          await host.clientEvent("UI_ACTION_ERROR", {
            label,
            class_name:cls,
            message:String(err)
          });
          render();
        }
      });
      return b;
    }

    function pill(text, cls="") {
      const p = document.createElement("span");
      p.className = `agp-pill ${cls}`.trim();
      p.textContent = text;
      return p;
    }

    // AGP_OVERLAY_DRAG_MINIMIZE_063S2
    const AGP_OVERLAY_UI_KEY = "agpOverlayUi063S2";
    let AGP_OVERLAY_UI = {left:null, top:null, minimized:false};
    let AGP_OVERLAY_UI_LOADED = false;
    let AGP_DRAG = null;

    async function loadOverlayUiState() {
      if (AGP_OVERLAY_UI_LOADED) return;
      AGP_OVERLAY_UI_LOADED = true;
      try {
        const stored = await chrome.storage.local.get([AGP_OVERLAY_UI_KEY]);
        const value = stored && stored[AGP_OVERLAY_UI_KEY];
        if (value && typeof value === "object") {
          AGP_OVERLAY_UI = {
            left:Number.isFinite(value.left) ? value.left : null,
            top:Number.isFinite(value.top) ? value.top : null,
            minimized:Boolean(value.minimized)
          };
        }
      } catch (_) {}
    }

    function saveOverlayUiState() {
      try {
        chrome.storage.local.set({[AGP_OVERLAY_UI_KEY]:AGP_OVERLAY_UI});
      } catch (_) {}
    }

    function clampOverlayPosition(root, left, top) {
      const rect = root.getBoundingClientRect();
      const maxLeft = Math.max(0, window.innerWidth - rect.width);
      const maxTop = Math.max(0, window.innerHeight - rect.height);
      return {
        left:Math.min(Math.max(0, left), maxLeft),
        top:Math.min(Math.max(0, top), maxTop)
      };
    }

    function applyOverlayUiState(root) {
      root.classList.toggle("agp-minimized", Boolean(AGP_OVERLAY_UI.minimized));
      if (Number.isFinite(AGP_OVERLAY_UI.left) && Number.isFinite(AGP_OVERLAY_UI.top)) {
        const pos = clampOverlayPosition(root, AGP_OVERLAY_UI.left, AGP_OVERLAY_UI.top);
        root.style.left = `${pos.left}px`;
        root.style.top = `${pos.top}px`;
        root.style.right = "auto";
        root.style.bottom = "auto";
      }
    }

    function beginOverlayDrag(event, root) {
      if (event.button !== 0) return;
      if (event.target && event.target.closest && event.target.closest("button")) return;
      const rect = root.getBoundingClientRect();
      AGP_DRAG = {
        root,
        dx:event.clientX - rect.left,
        dy:event.clientY - rect.top
      };
      event.preventDefault();
    }

    function moveOverlayDrag(event) {
      if (!AGP_DRAG) return;
      const pos = clampOverlayPosition(
        AGP_DRAG.root,
        event.clientX - AGP_DRAG.dx,
        event.clientY - AGP_DRAG.dy
      );
      AGP_DRAG.root.style.left = `${pos.left}px`;
      AGP_DRAG.root.style.top = `${pos.top}px`;
      AGP_DRAG.root.style.right = "auto";
      AGP_DRAG.root.style.bottom = "auto";
      AGP_OVERLAY_UI.left = pos.left;
      AGP_OVERLAY_UI.top = pos.top;
    }

    function endOverlayDrag() {
      if (!AGP_DRAG) return;
      AGP_DRAG = null;
      saveOverlayUiState();
    }

    window.addEventListener("mousemove", moveOverlayDrag);
    window.addEventListener("mouseup", endOverlayDrag);
    window.addEventListener("resize", () => {
      const root = document.getElementById("agp-cockpit-bridge");
      if (!root) return;
      if (!Number.isFinite(AGP_OVERLAY_UI.left) || !Number.isFinite(AGP_OVERLAY_UI.top)) return;
      const pos = clampOverlayPosition(root, AGP_OVERLAY_UI.left, AGP_OVERLAY_UI.top);
      AGP_OVERLAY_UI.left = pos.left;
      AGP_OVERLAY_UI.top = pos.top;
      applyOverlayUiState(root);
      saveOverlayUiState();
    });

    function render() {
      if (host.retired()) return;
      ensureStyle();
      loadOverlayUiState().then(() => {
        const current = document.getElementById("agp-cockpit-bridge");
        if (current) applyOverlayUiState(current);
      });

      let root = document.getElementById("agp-cockpit-bridge");
      if (!root) {
        root = document.createElement("div");
        root.id = "agp-cockpit-bridge";
        document.body.appendChild(root);
      }

      root.innerHTML = "";

      const head = document.createElement("div");
      head.className = "agp-head";
      head.title = "Ziehen zum Verschieben";
      head.addEventListener("mousedown", event => beginOverlayDrag(event, root));

      const title = document.createElement("span");
      title.textContent = "AGP Cockpit Bridge";
      head.appendChild(title);

      const extensionVersion = document.createElement("span");
      extensionVersion.style.fontSize = "11px";
      extensionVersion.style.color = "#b6c8d4";
      extensionVersion.textContent = `v${chrome.runtime.getManifest().version}`;
      extensionVersion.title = `Build ${globalThis.AGP_EXTENSION_BUILD_ID || "unknown"}`;
      head.appendChild(extensionVersion);

      const dot = document.createElement("span");
      dot.className = `agp-dot ${STATE.connected ? "on" : ""}`;
      head.appendChild(dot);

      const conn = document.createElement("span");
      conn.style.fontSize = "11px";
      conn.style.color = STATE.connected ? "#62d879" : "#9fb0bc";
      conn.textContent = STATE.connected ? "CONNECTED" : "LOCAL";
      head.appendChild(conn);

      if (STATE.running) {
        const busy = document.createElement("span");
        busy.className = "agp-busy";
        busy.setAttribute("role", "status");
        busy.setAttribute("aria-live", "polite");

        const spinner = document.createElement("span");
        spinner.className = "agp-spinner";
        spinner.setAttribute("aria-hidden", "true");
        busy.appendChild(spinner);

        const busyText = document.createElement("span");
        busyText.textContent = STATE.waitingForAssistant
          ? "ChatGPT arbeitet…"
          : "Cockpit arbeitet…";
        busy.appendChild(busyText);

        head.appendChild(busy);
      }

      const grow = document.createElement("span");
      grow.className = "agp-grow";
      head.appendChild(grow);

      head.appendChild(pill(STATE.state || "IDLE"));

      if (STATE.mission) {
        head.appendChild(pill(STATE.mission.execution_mode || "", "mode"));
        head.appendChild(pill(STATE.mission.run_mode || "", "run"));
      }

      const minimize = document.createElement("button");
      minimize.className = "agp-minimize";
      minimize.type = "button";
      minimize.title = AGP_OVERLAY_UI.minimized ? "Cockpit einblenden" : "Cockpit minimieren";
      minimize.textContent = AGP_OVERLAY_UI.minimized ? "▣" : "—";
      minimize.addEventListener("mousedown", event => event.stopPropagation());
      minimize.addEventListener("click", event => {
        event.preventDefault();
        event.stopPropagation();
        AGP_OVERLAY_UI.minimized = !AGP_OVERLAY_UI.minimized;
        saveOverlayUiState();
        render();
      });
      head.appendChild(minimize);

      applyOverlayUiState(root);
      root.appendChild(head);

      const actions = document.createElement("div");
      actions.className = "agp-actions";

      actions.appendChild(
        btn(
          STATE.running ? "▶ Aufgabe läuft" : "▶ Aufgabe starten",
          "start",
          host.actions.start
        )
      );
      actions.appendChild(btn("■ Stoppen", "stop", host.actions.stop));
      actions.appendChild(btn("⏭ Nächster Schritt", "next", host.actions.next));
      actions.appendChild(btn("↻ Aktualisieren", "status", host.actions.refresh));

      // Developer diagnostics remain available through bridge/CLI diagnostics;
      // historical phase controls are intentionally absent from the normal overlay.
      root.appendChild(actions);

      const body = document.createElement("div");
      body.className = "agp-body";

      const turns = document.createElement("div");
      turns.className = "agp-cell";

      const tLabel = document.createElement("div");
      tLabel.className = "agp-label";
      tLabel.textContent = "Turns";
      turns.appendChild(tLabel);

      const tBig = document.createElement("div");
      tBig.className = "agp-big";
      // Same count as the Cockpit: the mission's remote turns (not the
      // browser-local send counter, which also counts bootstrap messages).
      const shownTurns = STATE.mission ? Number(STATE.mission.turn_count || 0) : Number(STATE.turns || 0);
      tBig.textContent = `${shownTurns} / ${LIMITS.maxTurns}`;
      turns.appendChild(tBig);

      const progress = document.createElement("div");
      progress.className = "agp-progress";
      const fill = document.createElement("div");
      fill.style.width =
        `${Math.min(100, shownTurns / LIMITS.maxTurns * 100)}%`;
      progress.appendChild(fill);
      turns.appendChild(progress);
      body.appendChild(turns);

      const mission = document.createElement("div");
      mission.className = "agp-cell";

      const mLabel = document.createElement("div");
      mLabel.className = "agp-label";
      mLabel.textContent = "Mission";
      mission.appendChild(mLabel);

      const mText = document.createElement("div");
      mText.className = "agp-note";
      mText.textContent = STATE.mission
        ? `${STATE.mission.state} — ${STATE.mission.title || "Mission"} · Steps ${STATE.mission.step_count || 0}`
        : "IDLE — Keine aktive Mission";
      mission.appendChild(mText);

      const phaseText = STATE.running && typeof agpMissionPhaseText === "function"
        ? agpMissionPhaseText(STATE, Date.now()) : "";
      if (phaseText) {
        const phase = document.createElement("div");
        phase.className = "agp-note";
        phase.style.marginTop = "4px";
        phase.textContent = phaseText;
        mission.appendChild(phase);
      }

      if (STATE.note) {
        const note = document.createElement("div");
        note.className = "agp-note";
        note.style.marginTop = "4px";
        note.textContent = STATE.note;
        mission.appendChild(note);
      }

      body.appendChild(mission);

      const refreshed = document.createElement("div");
      refreshed.className = "agp-cell";

      const rLabel = document.createElement("div");
      rLabel.className = "agp-label";
      rLabel.textContent = "Aktualisiert";
      refreshed.appendChild(rLabel);

      const rText = document.createElement("div");
      rText.className = "agp-big";
      rText.style.fontSize = "14px";
      rText.textContent = STATE.lastRefresh
        ? STATE.lastRefresh.toLocaleTimeString()
        : "—";
      refreshed.appendChild(rText);

      body.appendChild(refreshed);
      root.appendChild(body);

      const debug = document.createElement("div");
      debug.className = "agp-debug";
      /* AGP_K07_OPERATOR_TRACE_RUNTIME_CONTROL_1137 */
      debug.textContent = "";
      const traceRow = document.createElement("div");
      traceRow.className = "agp-k07-trace-control";
      const traceState = document.createElement("span");
      traceState.textContent = `Last event: ${STATE.lastEvent} | K07 trace: ${STATE.k07DebugTraceEnabled ? "AN" : "AUS"}`;
      traceRow.appendChild(traceState);
      const traceButton = document.createElement("button");
      traceButton.type = "button";
      traceButton.textContent = STATE.k07DebugTraceEnabled ? "Trace aus" : "Trace an";
      traceButton.title = "Schaltet den vorhandenen K07-Debug-Trace; Ereignisse gehen ueber /v1/client-event ins Bridge-Log.";
      traceButton.addEventListener("mousedown", event => event.stopPropagation());
      traceButton.addEventListener("click", async event => {
        event.preventDefault();
        event.stopPropagation();
        host.actions.toggleTrace();
        render();
      });
      traceRow.appendChild(document.createTextNode(" "));
      traceRow.appendChild(traceButton);
      // K07 trace is a dedicated operator test control. Keep historical
      // diagnostics hidden, but expose this control independently.
      root.appendChild(traceRow);

      if (STATE.errorId) {
        const error = document.createElement("span");
        error.className = "agp-error";
        error.textContent = ` · ${STATE.errorId}`;
        debug.appendChild(error);
      }

      // Historical diagnostics remain hidden unless explicitly opened.
      if (host.diagnosticsOpen()) {
        root.appendChild(debug);
      }
    }

    return Object.freeze({render});
  }

  globalThis.AGP_PANEL = Object.freeze({create});
})();
