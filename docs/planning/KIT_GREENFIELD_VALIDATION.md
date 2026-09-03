# Agentic Project Kit Greenfield Validation

Status: active
Status-date: 2026-09-03
Decision status: maintainer-approved
Review policy: on material change

## 1. Purpose

Development of AGP Cockpit is simultaneously a real-world Greenfield validation
of `agentic-project-kit` as an external-workspace development control plane.

The Cockpit product remains independent of the Kit. This validation obligation
governs how AGP Cockpit itself is developed with the Kit.

The goal is to ensure that defects discovered through normal, realistic Kit use
are preserved as evidence instead of being silently worked around and forgotten.

## 2. Mandatory finding capture

During normal AGP Cockpit development, every credible problem attributable to
the Agentic Project Kit or to its external-workspace integration MUST be recorded
when discovered.

This includes, at minimum:

- reproducible Kit defects or regressions;
- incorrect command or workflow behavior;
- incorrect PASS, BLOCKED, FAIL, WARN, or gate semantics;
- missing required capability in an otherwise supported workflow;
- unsafe or misleading workflow behavior;
- misleading, incomplete, or contradictory diagnostics;
- documentation defects that materially impede correct Kit use;
- generated-state or handoff defects;
- external-workspace integration defects;
- unnecessary manual workarounds required because the supported Kit path fails.

A problem MUST NOT be silently bypassed and then forgotten.

Cockpit development MAY continue with a bounded documented workaround when the
underlying product work is otherwise safe. The Kit finding remains open until it
is classified and resolved, rejected with evidence, or explicitly deferred.

## 3. Classification boundary

Every development problem that could plausibly originate outside the Cockpit
product must be classified before it is treated as a Cockpit bug.

Use one of these primary classes:

- `cockpit-product`
- `agentic-kit`
- `kit-integration`
- `environment`
- `test-model`

If evidence is initially insufficient, use `unclassified` and perform bounded
diagnosis. Do not prematurely repair Cockpit code to compensate for a possible
Kit defect.

## 4. Required evidence for Kit findings

A recorded Kit finding should contain, where available:

- stable finding ID;
- discovery date;
- status;
- severity/impact;
- Kit version and/or commit;
- AGP Cockpit branch and commit;
- triggering Kit command or governed workflow;
- expected behavior;
- observed behavior;
- minimal reproduction;
- bounded log/evidence reference;
- classification;
- workaround, if any;
- disposition or resolution reference.

Secrets, tokens, credentials, and private browser/session data MUST NOT be
placed in the finding record.

## 5. Canonical finding ledger

The durable project ledger is:

`docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.md`

The ledger is repository evidence. Individual large logs remain outside the
ledger and are referenced by bounded identifiers/paths when appropriate.

The absence of an open finding does not prove the Kit is defect-free; it means
no unresolved qualifying finding has yet been recorded by this Greenfield test.

## 6. Development gate

Before a slice is accepted, the developer/agent MUST ask:

1. Did this slice expose any possible Agentic Project Kit or Kit-integration defect?
2. If yes, was it classified using the boundary above?
3. If it qualifies as a Kit finding, was it added to the canonical ledger with
   sufficient evidence before the slice was declared complete?

A slice that knowingly encountered a qualifying Kit defect but discarded the
evidence is not complete.

## 7. Relationship to product scope

This validation contract does NOT expand AGP Cockpit runtime scope.

The Cockpit application MUST NOT gain Kit diagnostic, Kit issue-tracking,
Git/GitHub workflow, or FILE_TRANSFER policy logic merely because the repository
is used as a Greenfield Kit test.

Greenfield validation belongs to repository development governance and evidence,
not to the Cockpit product runtime.

## 8. Handoff durability

This rule is durable development context and must survive chat switches.

Generated successor/handoff projections must not be edited manually to encode
this rule. Their canonical sources must be refreshed through the supported
Agentic Project Kit handoff path after the governance change is accepted.
