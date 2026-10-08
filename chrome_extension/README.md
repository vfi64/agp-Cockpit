# AGP Cockpit Chrome Extension

## Production desktop setup

1. Start AGP Cockpit. The production bridge runtime is stored outside the repository.

2. Read the production bridge token from:

   `~/Library/Application Support/AGP Cockpit/bridge/token.txt`

3. Open `chrome://extensions`.

4. Enable **Developer mode**.

5. Choose **Load unpacked** and select:

   `chrome_extension/`

6. Open the extension options and enter:
   - Base URL: `http://127.0.0.1:9876`
   - Local bridge token: contents of `token.txt`

7. Reload the ChatGPT tab after reloading the extension.

For the first browser test use only:

- `DRY_RUN`
- `SINGLE_STEP`

Do not switch to `LIVE` until the HTTP dry-run path is green.

## Explicit repository-local development bridge

When intentionally starting the development bridge with `.venv/bin/python -m agp_cockpit.bridge_main --repository .`, its token is repository-local at `.local/agp-cockpit/bridge/token.txt`. Do not use that development token for the production desktop bridge.\n\n## Production installation and token synchronization\n\nOn macOS, do not load the unpacked extension directly from a Dropbox/File Provider working tree.\nAGP Cockpit stages the production extension at:\n\n`~/Library/Application Support/AGP Cockpit/chrome_extension/`\n\nLoad that staged directory with Chrome Developer mode -> **Load unpacked**. Chrome does not permit\nAGP Cockpit to silently install or rewrite the internal storage of an unpacked extension, so initial\ntoken synchronization is an explicit operator step.\n\nThe production bridge token authority is:\n\n`~/Library/Application Support/AGP Cockpit/bridge/token.txt`\n\nAfter the extension is loaded:\n\n1. Open `chrome://extensions/`.\n2. Locate **AGP Cockpit Bridge** and open **Details**.\n3. Open **Extension options** from the Details page. Direct navigation to a\n   `chrome-extension://<id>/options.html` URL can be blocked by Chrome with\n   `ERR_BLOCKED_BY_CLIENT`; use the Details page instead.\n4. Put the production token into **Local bridge token** and choose **Save**.\n5. Reload the extension if necessary and reload the ChatGPT tab.\n6. Verify the overlay reports **CONNECTED** and its latest status event is **STATUS_OK**.\n   A persistent `Error: forbidden` means the token stored in `chrome.storage.local` does not\n   match the running production bridge token.\n\nThe repository-local development bridge remains separate. Its `.local/agp-cockpit/bridge/token.txt`\ntoken is only for an explicitly repository-local development bridge, never the production desktop bridge.\n

## Content scripts (manifest order) and their jobs

- `chatgpt_selectors.js` — every ChatGPT selector (`AGP_SELECTORS`) and `agpPageExpression()` for
  helpers injected into the page; when ChatGPT changes its page, the fix belongs here.
- `native_message_evidence.js` — composer resolver, committed-turn evidence, touchpoint self-test,
  UI fingerprint and failure shapes.
- `cockpit_panel.js` — the AGP Cockpit Bridge overlay (`AGP_PANEL`).
- `cockpit_ingress.js` — file ingress (`AGP_INGRESS`): the expected step's file card from ChatGPT's
  answer to the bridge.
- `cockpit_send.js` — send transport (`AGP_SEND`): prompt into the composer, native submit, commit
  nonce, acceptance evidence and the bounded retry; the native submit is the only send path.
- `chatgpt_dom.js` — page adapter (`AGP_DOM`): assistant turns, file cards, send/stop controls,
  preview and dialogs.
- `content.js` — the controller: state, mission loop and actions; it may only shrink.

Removed on 2026-10-08 (AGP_LEGACY_PATHS_REMOVED_V1): `protocol_action_contract_v1.js`,
`transport_protocol_v1.js`, `conversation_contract.js`, `protocol_canonicalizer_v1.js`,
`phase7_single_round.js` and `phase8_multi_round.js` — loaded only by operator paths without a button
since 2026-09-15.

Failure shapes from `.local/agp-cockpit/browser/dom-snapshots/` can be replayed against this code with
`AGP_DOM_SNAPSHOT=<file> npx playwright test tests/e2e/test_dom_snapshot_replay.spec.js`.

