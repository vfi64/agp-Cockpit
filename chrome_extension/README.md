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
   - Base URL: `http://127.0.0.1:8765`
   - Local bridge token: contents of `token.txt`

7. Reload the ChatGPT tab after reloading the extension.

For the first browser test use only:

- `DRY_RUN`
- `SINGLE_STEP`

Do not switch to `LIVE` until the HTTP dry-run path is green.

## Explicit repository-local development bridge

When intentionally starting the development bridge with `.venv/bin/python -m agp_cockpit.bridge_main --repository .`, its token is repository-local at `.local/agp-cockpit/bridge/token.txt`. Do not use that development token for the production desktop bridge.
