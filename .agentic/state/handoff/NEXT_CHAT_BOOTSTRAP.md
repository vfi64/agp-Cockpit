# Successor Chat Prompt

Repository: `vfi64/agp-Cockpit`.

Read the machine-readable execution contract and source manifest first.
The versioned projection describes content only. Exact repository identity and the validator result for this handoff are in `.agentic/tmp/handoff/runtime_identity.json`.
Unknown projection versions block continuation. Stop on BLOCKED or FAIL.

```text
agentic-kit transfer repo-status
agentic-kit check --root .
agentic-kit doctor --root .
```

## Execution contract

```json
{
  "command_reference": {
    "ack": "COMMAND_MANIFEST_ACK 8ec3727bd6f1",
    "json": "@kit/agentic-kit-commands.json",
    "manifest_sha": "8ec3727bd6f1",
    "must_not_reconstruct_commands_from_memory": true,
    "source_hashes": {
      "@kit/agentic-kit-commands.json": "8c72a09192113a19625aa7772ef5376942427ebb783c8fa78054b29d0798d3fc"
    }
  },
  "current_state_contract": {
    "document_registry_source": ".agentic/registries/documentation.yaml",
    "next_action_rule": "Use current_state_contract only as continuation state; do not promote it to durable rules.",
    "open_tasks": [
      {
        "files": [
          ".agentic/state/status.md",
          ".agentic/state/handoff/README.md"
        ],
        "id": "external-workspace-no-project-direction",
        "status": "review",
        "summary": "Continue from external workspace status, handoff and project authority files."
      }
    ],
    "open_tasks_source": "docs/planning/PROJECT_DIRECTION.yaml",
    "recent_lessons": [],
    "repo": {
      "full_name": "vfi64/agp-Cockpit"
    },
    "scope": "current-continuation-state"
  },
  "general_contract": {
    "rule_ids": [
      "copy-paste-output-discipline",
      "documentation-authority-model",
      "gc-retention-not-document-migration",
      "generated-handoff-projection-update-policy",
      "ns-legacy-not-active-control-plane",
      "patch-cycle-diagnostic-gate",
      "repo-backed-rules-and-gates",
      "successor-final-head-identity",
      "successor-package-not-prompt-only",
      "wrapper-first-complete-development-cycle"
    ],
    "scope": "durable-agentic-kit-operating-model",
    "source_authorities": [
      ".agentic/config.yaml",
      ".agentic/state/status.md",
      ".agentic/state/handoff/README.md",
      ".agentic/registries/documentation.yaml",
      ".agentic/registries/rules.yaml"
    ],
    "summary": {
      "agentic_kit_is_control_plane": true,
      "complete_development_cycle_required": true,
      "do_not_plan_from_stale_chat_memory": true,
      "documentation_authority_model_required": true,
      "gc_is_retention_not_document_migration": true,
      "ns_is_legacy_not_active_control_plane": true,
      "repo_backed_rules_and_gates_required": true,
      "wrapper_first": true
    }
  },
  "handoff_projection_contract": {
    "allowed_update_path": [
      "Change successor_handoff_package.py, execution contract inputs, or repo-backed rule sources.",
      "Add or update tests and validation for new handoff content.",
      "Run agentic-kit transfer prepare-successor-handoff --render-prompt to regenerate projections."
    ],
    "dedicated_update_only_paths": [],
    "default_direct_write_paths": [
      ".agentic/state/handoff/packages/latest/execution_contract.json",
      ".agentic/state/handoff/packages/latest/source_manifest.json",
      ".agentic/state/handoff/packages/latest/successor_context.yaml",
      ".agentic/state/handoff/packages/latest/successor_prompt.md",
      ".agentic/state/handoff/packages/latest/validation_report.json",
      ".agentic/state/handoff/NEXT_CHAT_BOOTSTRAP.md",
      ".agentic/state/handoff/START_NEW_CHAT_PROMPT.md",
      ".agentic/state/handoff/CLOSEOUT_BEFORE_CHAT_SWITCH_PROMPT.md"
    ],
    "do_not_use_uploaded_or_copied_prompt_text_as_sole_source": true,
    "dpa_generated_output_contract": {
      "acceptance_state_invalidated_without_renderer_reproducibility": true,
      "contract_id": "DPA-GENERATED-SUCCESSOR-HANDOFF-PROJECTION-v2",
      "current_generator_command": "agentic-kit transfer chat-switch-complete --render-prompt",
      "current_handoff_target_byte_writer": false,
      "dedicated_update_only_paths": [],
      "default_direct_write_paths": [
        ".agentic/state/handoff/packages/latest/execution_contract.json",
        ".agentic/state/handoff/packages/latest/source_manifest.json",
        ".agentic/state/handoff/packages/latest/successor_context.yaml",
        ".agentic/state/handoff/packages/latest/successor_prompt.md",
        ".agentic/state/handoff/packages/latest/validation_report.json",
        ".agentic/state/handoff/NEXT_CHAT_BOOTSTRAP.md",
        ".agentic/state/handoff/START_NEW_CHAT_PROMPT.md",
        ".agentic/state/handoff/CLOSEOUT_BEFORE_CHAT_SWITCH_PROMPT.md"
      ],
      "exact_byte_rollback_claims_renderer_reproducibility": false,
      "full_probe_pass_claimed": false,
      "generated_output_class": "command_generated_successor_handoff_projection",
      "generated_outputs_manually_patched": false,
      "generated_projection_paths": [
        ".agentic/state/handoff/packages/latest/execution_contract.json",
        ".agentic/state/handoff/packages/latest/source_manifest.json",
        ".agentic/state/handoff/packages/latest/successor_context.yaml",
        ".agentic/state/handoff/packages/latest/successor_prompt.md",
        ".agentic/state/handoff/packages/latest/validation_report.json",
        ".agentic/state/handoff/NEXT_CHAT_BOOTSTRAP.md",
        ".agentic/state/handoff/START_NEW_CHAT_PROMPT.md",
        ".agentic/state/handoff/CLOSEOUT_BEFORE_CHAT_SWITCH_PROMPT.md"
      ],
      "generator_command": "agentic-kit transfer prepare-successor-handoff --render-prompt",
      "initial_create_if_missing_paths": [],
      "kind": "dpa_generated_successor_handoff_projection_contract",
      "kit_conformance_claimed": false,
      "manual_durable_target_patches_allowed": false,
      "production_mutation_claimed": false,
      "schema_version": 1,
      "source_command_contract_required": true,
      "source_paths": [
        "src/agentic_project_kit/successor_handoff_package.py",
        "src/agentic_project_kit/external_handoff_projection.py",
        "src/agentic_project_kit/cli_commands/transfer_handoff_flow.py"
      ],
      "target_scope": "GENERATED_SUCCESSOR_HANDOFF_PACKAGE_AND_PROMPT_PROJECTIONS",
      "writer_id": "WRT-CH-006"
    },
    "final_head_identity": {
      "content_validation": "deterministic_regeneration_and_byte_comparison",
      "exact_runtime_identity_required": true,
      "model": "content_projection_with_ignored_runtime_identity",
      "runtime_identity_path": ".agentic/tmp/handoff/runtime_identity.json"
    },
    "forbidden_update_path": [
      "manual direct edits to generated handoff projections",
      "adding durable rules only to docs/handoff/*.md",
      "editing latest handoff-package JSON/YAML/Markdown as the primary patch"
    ],
    "generated_projection_paths": [
      ".agentic/state/handoff/packages/latest/execution_contract.json",
      ".agentic/state/handoff/packages/latest/source_manifest.json",
      ".agentic/state/handoff/packages/latest/successor_context.yaml",
      ".agentic/state/handoff/packages/latest/successor_prompt.md",
      ".agentic/state/handoff/packages/latest/validation_report.json",
      ".agentic/state/handoff/NEXT_CHAT_BOOTSTRAP.md",
      ".agentic/state/handoff/START_NEW_CHAT_PROMPT.md",
      ".agentic/state/handoff/CLOSEOUT_BEFORE_CHAT_SWITCH_PROMPT.md"
    ],
    "generator_command": "agentic-kit transfer prepare-successor-handoff --render-prompt",
    "initial_create_if_missing_paths": [],
    "machine_readable_files_take_precedence": true,
    "must_read_files": [
      ".agentic/state/handoff/packages/latest/execution_contract.json",
      ".agentic/state/handoff/packages/latest/successor_context.yaml",
      ".agentic/state/handoff/packages/latest/validation_report.json",
      ".agentic/state/handoff/packages/latest/source_manifest.json",
      ".agentic/state/handoff/packages/latest/successor_prompt.md"
    ],
    "prompt_is_projection_only": true,
    "source_of_truth": "generator_and_machine_readable_successor_package",
    "stale_local_prompt_files_are_not_authoritative": true
  },
  "kind": "successor_execution_contract",
  "projection_contract_version": 2,
  "repo": {
    "full_name": "vfi64/agp-Cockpit"
  },
  "rules": [
    {
      "forbidden": [
        "manual editor instructions",
        "loose command fragments",
        "naked python",
        "naked pytest",
        "git add .",
        "{ ... } > \"$OUT\" 2>&1 as the recommended logging pattern"
      ],
      "must": [
        "Use one complete copy-and-paste Bash block per local action.",
        "Start every local block by changing into the repository root.",
        "Write verbose output to ~/Downloads/*.log.",
        "Print LOG=... and RC=... at the end.",
        "Use ./.venv/bin/python and ./.venv/bin/python -m pytest."
      ],
      "priority": "critical",
      "rule_id": "local-copy-paste-protocol",
      "scope": "local-user-command-blocks"
    },
    {
      "allowed_next_actions": [
        "diagnose_dirty_state",
        "commit_admin_refresh_after_passed_protected_plan",
        "sync_main",
        "start_product_slice_only_from_clean_main"
      ],
      "must": [
        "Inspect validation_report.json if present.",
        "Inspect branch, HEAD, origin/main, upstream, and dirty paths.",
        "Interpret branch != main with head_matches_origin_main=true explicitly.",
        "Stop product work when worktree_clean=false."
      ],
      "priority": "critical",
      "rule_id": "strict-start-decision",
      "scope": "successor-chat-start",
      "stop_conditions": [
        "validation_report.status is not PASS",
        "unexpected dirty paths exist",
        "protected files changed without protected-diff-plan",
        "HEAD and origin/main disagree without explanation"
      ]
    },
    {
      "must": [
        "After running the bootstrap block, evaluate the log before starting any new work.",
        "Confirm validation_report.json PASS and execution_contract.json was read.",
        "Confirm worktree clean or only explicitly named WIP files.",
        "Confirm repo-status PASS, agentic-kit check --root . PASS, and agentic-kit doctor --root . Overall PASS.",
        "Classify every WARN as a risk, optional foreign-repo component, or explained skip.",
        "Emit exactly one status decision: Übergabe akzeptiert, keine Admin-Arbeit nötig. or BLOCK with the concrete log-backed reason."
      ],
      "not_required_for_external_workspace": [
        "rules acknowledge",
        "transfer post-merge-check on a non-main feature branch",
        "self-hosting docs-audit",
        "main == origin/main while continuing a feature branch"
      ],
      "priority": "critical",
      "rule_id": "bootstrap_acceptance_gate",
      "scope": "successor-chat-bootstrap"
    },
    {
      "forbidden": [
        "treating Kit self-hosting post-merge or rule-snapshot gates as mandatory external feature-branch startup gates",
        "claiming target-repository product tests are green when only Kit overlay gates ran",
        "planning from stale chat memory or stale copied prompt text"
      ],
      "must": [
        "Use the target repository's native tests and documented quality gates as the product authority.",
        "Use agentic-kit check, doctor, repo-status, and successor handoff package as the operating-layer health checks.",
        "Inspect actual diffs before committing generated operating-layer files.",
        "Regenerate the successor handoff package before a chat switch or after completing a local work slice.",
        "Use Kit PR/post-merge wrappers only when their preconditions fit the target repository and branch state."
      ],
      "priority": "critical",
      "rule_id": "wrapper-first-complete-development-cycle",
      "scope": "external-workspace-development-handoff"
    },
    {
      "forbidden": [
        "using NEW_CHAT_HANDOFF_PROMPT.md or copied chat text as the sole start authority",
        "starting product work before validation_report.json and execution_contract.json were inspected"
      ],
      "must": [
        "Treat successor_prompt.md as a human-readable projection only.",
        "Read execution_contract.json, successor_context.yaml, validation_report.json, and source_manifest.json before work.",
        "Use machine-readable files over stale copied prompt text when they disagree."
      ],
      "priority": "critical",
      "rule_id": "successor-package-not-prompt-only",
      "scope": "chat-switch-handoff"
    },
    {
      "forbidden": [
        "treating missing self-hosting Kit governance documents as external product failures",
        "adding durable target-repository rules only to generated handoff projections",
        "deleting semantic documentation through report-retention GC"
      ],
      "must": [
        "Use .agentic/state/status.md and .agentic/state/handoff/README.md as external workspace continuation state.",
        "Use .agentic/registries/documentation.yaml for operating-layer document classification.",
        "Treat target-repository README, architecture, changelog, and native docs as project-owned authority.",
        "Do not require docs/planning/PROJECT_DIRECTION.yaml unless the external workspace explicitly adopts it."
      ],
      "priority": "critical",
      "rule_id": "documentation-authority-model",
      "scope": "external-workspace-documentation-authority"
    },
    {
      "forbidden": [
        "committing, pushing, creating PRs, or merging after protected-diff-plan FAIL",
        "overwriting protected files broadly to make gates pass"
      ],
      "must": [
        "Treat repo-backed rules, tests, gates, and evidence logs as authoritative.",
        "Stop on BLOCK or FAIL and diagnose before continuing.",
        "Run protected-diff-plan before protected/governance/status/handoff/YAML commits.",
        "Use evidence-producing commands; do not substitute a free-text PASS."
      ],
      "priority": "critical",
      "rule_id": "repo-backed-rules-and-gates",
      "scope": "rules-tests-evidence"
    },
    {
      "forbidden": [
        "using GC as semantic documentation migration",
        "deleting .md/.py/.yaml/.txt without explicit policy and review"
      ],
      "must": [
        "Treat report-retention GC as technical artifact/report retention.",
        "Use dry-run before execute.",
        "Restrict automatic report-retention execution to explicitly allowed candidate types."
      ],
      "priority": "critical",
      "rule_id": "gc-retention-not-document-migration",
      "scope": "artifact-gc"
    },
    {
      "forbidden": [
        "placing new operational rules in docs/reports/ns-migration/",
        "resurrecting removed ./ns routes as active workflow instructions"
      ],
      "must": [
        "Treat ns migration documents as historical or compatibility context unless the registry says otherwise.",
        "Classify ./ns references as historical, test fixture, compatibility implementation, or active blocker before changing them."
      ],
      "priority": "critical",
      "rule_id": "ns-legacy-not-active-control-plane",
      "scope": "legacy-ns-references"
    },
    {
      "forbidden": [
        "manual direct edits to generated handoff projection files as the primary source of a new rule",
        "making copied prompt text the durable source of truth"
      ],
      "must": [
        "Treat docs/handoff/*.md and latest successor package files as generated projections.",
        "Change the generator, execution contract, validation, or rule source before changing projected handoff content.",
        "Regenerate projections with agentic-kit transfer prepare-successor-handoff --render-prompt."
      ],
      "priority": "critical",
      "rule_id": "generated-handoff-projection-update-policy",
      "scope": "generated handoff projections"
    },
    {
      "must": [
        "Require deterministic regeneration and exact byte equality for the durable projection.",
        "Require exact current commit identity and same-run validator PASS from .agentic/tmp/handoff/runtime_identity.json.",
        "Never reuse commit-bound approvals, signed plans, CI or release gates after a commit change."
      ],
      "must_not": [
        "rerender and commit successor projections only to chase the self-created commit SHA",
        "treat stale copied prompt text as stronger authority than machine-readable package plus post-merge evidence"
      ],
      "priority": "critical",
      "rule_id": "successor-final-head-identity",
      "scope": "successor handoff final repository identity"
    },
    {
      "forbidden": [
        "starting a third mutation in the same patch family without diagnosis",
        "continuing a micro-patch cascade after repeated red tests"
      ],
      "must": [
        "After one failed patch, allow exactly one direct correction in the same patch family.",
        "After a second failure in the same patch family, stop mutations and run a bounded diagnosis block.",
        "Classify product bug versus test-model bug before another mutation.",
        "Record next_mutation_allowed explicitly before continuing."
      ],
      "priority": "critical",
      "rule_id": "patch-cycle-diagnostic-gate",
      "scope": "failed patch/test cycles"
    },
    {
      "forbidden": [
        "cat whole diagnostic or summary files into chat",
        "unbounded grep over docs/reports, .agentic/outbox, generated JSON, or logs",
        "tail or grep excerpts as chat output for long workflows",
        "large terminal output pasted directly into chat"
      ],
      "must": [
        "After local blocks, chat output should be only LOG=... and RC=....",
        "Write large outputs to tmp/*.log or ~/Downloads/*.log.",
        "Use compact JSON summaries for diagnostics.",
        "Compress or summarize large logs before discussion."
      ],
      "priority": "critical",
      "rule_id": "copy-paste-output-discipline",
      "scope": "local copy-and-paste workflows"
    },
    {
      "forbidden": [
        "broadly replacing protected files",
        "shortening protected governance/status/handoff/YAML files for convenience",
        "committing after a blocked protected plan"
      ],
      "must": [
        "Inspect the actual git diff before commit.",
        "Run protected-diff-plan against the actual diff.",
        "Patch protected files minimally and additively.",
        "Stop immediately on BLOCK or FAIL."
      ],
      "priority": "critical",
      "rule_id": "protected-file-preservation",
      "scope": "protected governance/status/handoff/YAML files"
    }
  ],
  "schema_version": 1,
  "source_hashes": {
    "@kit/agentic-kit-commands.json": "8c72a09192113a19625aa7772ef5376942427ebb783c8fa78054b29d0798d3fc"
  },
  "validation": {
    "path": ".agentic/successor_handoff_package/validation_report.json",
    "status": "PASS"
  }
}
```
