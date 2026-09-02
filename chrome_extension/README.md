# AGP Cockpit Chrome Extension

## Local development setup

1. Start the bridge service from the Cockpit repository:

   `.venv/bin/python -m agp_cockpit.bridge_main --repository .`

2. Read the token from:

   `.local/agp-cockpit/bridge/token.txt`

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
