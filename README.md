# AGP Cockpit

AGP Cockpit is a local desktop control plane for mechanically bridging a browser-based LLM session and local repository work governed by the Agentic Project Kit.

Initial target platform: macOS.

Architecture goal: a platform-portable, deterministic application in which browser interaction, process execution, platform integration, and Agentic Project Kit access are isolated behind explicit ports/adapters. The local LLM/Hermes layer is transport/execution only and must not make development or workflow decisions.

Canonical planning documents live under `docs/planning/`.

Document ownership and authority boundaries are defined in `docs/planning/DOCUMENT_AUTHORITY.md`.

## Standard Tasks

The desktop Cockpit provides a `Standard Tasks` tab for repeatable, pre-authored
task templates. `Chat wechseln` creates a validated successor-handoff mission
using the existing Task Contract and browser file-loop transport. The template
registry is intentionally small and can be extended with additional tasks only
when their local contract, evidence, and failure behavior are defined.
