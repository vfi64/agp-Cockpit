# ADR-0001: macOS-first product with platform-portable core

Status: Accepted

## Context

The first useful AGP Cockpit installation will run on macOS and integrate with locally installed Chrome, Ollama, Hermes, Python, and the Agentic Project Kit. At the same time, the product should not embed macOS assumptions into its domain/application core, because future Windows or Linux support should be possible without a rewrite.

## Decision

AGP Cockpit is macOS-first at the product-support level and platform-portable at the architecture level.

The application uses explicit ports/adapters for all operating-system-dependent behavior. macOS-specific executable paths, Homebrew assumptions, process tools, browser application locations, listener inspection, application-support directories, and desktop-launch behavior are confined to the macOS platform adapter and composition layer.

Portable core/application code must run in CI on a non-macOS host using fake adapters.

## Consequences

Positive:

- the first implementation remains focused on one real platform;
- macOS integration can be optimized without contaminating core logic;
- future platform adapters can be added independently;
- Linux CI can detect accidental platform coupling early.

Negative:

- more interfaces and adapter code are required initially;
- some macOS behavior will need both CI-safe fixture tests and explicit local integration tests;
- true Windows/Linux support still requires concrete adapters and validation later.

## Verification

This decision is continuously enforced by architecture fitness tests and CI:

- core/application packages must not import macOS-specific modules;
- portable tests must pass on Linux CI;
- macOS adapter tests must pass on macOS CI;
- each implementation slice remains incomplete until the applicable CI and Agentic Project Kit gates are green on the exact accepted commit.
