# ADR-0002: Python/Tkinter product and scripted local operations

Status: Accepted

## Context

AGP Cockpit is initially a macOS desktop application, but its architecture must remain portable. Maintainer-local development operations also need to be reproducible and governed by the current Agentic Project Kit rather than by ad-hoc terminal command sequences.

## Decision

1. The product is implemented in Python.
2. The desktop GUI uses `tkinter` for the initial product line.
3. `tkinter` is a presentation adapter only; core/application logic remains GUI-independent.
4. macOS-specific behavior is isolated behind platform ports/adapters.
5. Maintainer-local work instructions are distributed as Python scripts whenever practical.
6. Those scripts prefer the highest-level current Agentic Project Kit orchestrator that matches the intended workflow.
7. Local scripts do not substitute for remote CI or Kit gates.

## Consequences

Positive:

- one implementation language for product, utilities, tests, and local maintenance tooling;
- low deployment complexity on macOS;
- deterministic and inspectable local workflows;
- later Windows/Linux adapters can be added without redesigning domain logic;
- Kit orchestration remains the source of workflow semantics rather than duplicated Python logic.

Trade-offs:

- Tkinter appearance is less native/polished than some platform-specific frameworks;
- browser automation and OS integration still require concrete adapters;
- packaging must ensure a compatible Python/Tk runtime is present;
- Windows/Linux support is architectural readiness, not an initial product claim.

## Revisit triggers

Reconsider the GUI toolkit only if measured requirements cannot be met with Tkinter without contaminating the core architecture, or if packaging/accessibility constraints materially outweigh the migration cost. Such a change requires a new ADR and corresponding gates.
