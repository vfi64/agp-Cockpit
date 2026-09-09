# Cross-platform Product Readiness — S12

## Status and scope

S12 starts only after the macOS target runtime has satisfied S0-S11. It does not
retroactively redefine the accepted macOS architecture. The product remains
macOS-first while the deterministic core is kept portable.

The repository currently has no normative Windows/Linux product-acceptance test
plan. Therefore S12 must not claim Windows or Linux product support merely
because portable-core tests pass.

## Platform boundary

Portable and platform-neutral:
- protocol framing and validation;
- durable task/action/message/evidence persistence;
- Task Controller state transitions, budgets, stall and cancellation;
- governance evidence semantics;
- remote-context binding/refresh;
- completion-contract verification;
- local-observation value-gate logic.

macOS-owned adapters/integration:
- AppleScript and /usr/bin/osascript;
- ChatGPT desktop and Chrome automation through macOS accessibility;
- ~/Library/Application Support/AGP Cockpit/;
- macOS application packaging and Finder launch smoke;
- production browser-extension staging at the macOS Application Support path.

These macOS mechanisms must remain behind explicit platform/adaptor boundaries.
Portable core code must not acquire new Darwin/Application-Support/AppleScript
dependencies.

## Readiness levels

1. MACOS_ACCEPTED: S0-S11 applicable gates pass.
2. PORTABLE_CORE_READY: platform-neutral core runs in a non-Darwin simulated
   environment and platform-specific integrations fail closed or report
   unsupported status rather than attempting macOS commands.
3. WINDOWS_PRODUCT_READY and LINUX_PRODUCT_READY: reserved. They require
   explicit native adapters, packaging, CI runners and native acceptance tests.
   They are not implied by S12 portable-core readiness.

## S12 acceptance gate

S12 may close as PORTABLE_CORE_READY when:
- architecture and S3-S11 regressions remain green;
- a non-Darwin contract test proves core imports/state-machine operation do not
  require macOS integration;
- macOS-only runtime adapters reject non-Darwin use fail-closed;
- first-run diagnostics report the current desktop target accurately;
- documentation does not claim native Windows/Linux product support;
- CI/platform expansion is explicitly classified as future native-product work.

No raw Git/GitHub lifecycle is introduced; repository changes remain under Kit
governance.
