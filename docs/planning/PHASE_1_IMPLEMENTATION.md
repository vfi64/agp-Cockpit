# Phase 1 – Application Skeleton

Status: active
Status-date: 2026-08-31
Decision status: accepted
Review policy: on material change

Phase 1 begins the actual AGP Cockpit implementation.

The application remains a transport/execution cockpit. It does not
implement Agentic Project Kit workflow policy and does not make
development decisions.

Initial architecture:

- `core/`: platform-independent domain types and ports
- `ui/`: Tkinter presentation
- later adapters: macOS terminal/process/browser integration
- Kit interaction through explicit adapter boundaries

The first slice deliberately contains no browser automation and no
Ollama/Hermes process mutation.
