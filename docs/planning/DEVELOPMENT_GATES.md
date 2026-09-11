# AGP Cockpit Development Gates v2

Status: active
Status-date: 2026-09-09
Decision status: accepted

G0 Authority: read current repository/planning/Kit authority before mutation.
G1 Scope: preserve Remote-LLM / deterministic-controller / Kit split.
G2 Slice: one coherent branch/PR; no autonomy beyond accepted roadmap gate.
G3 Tests: focused plus required full tests are green.
G4 Safety/effect: capabilities/effect classes explicit; request is not permission.
G5 Protocol: explicit version/compatibility treatment; no silent V1 redefinition.
G6 Persistence/replay: no blind replay; preserve OUTCOME_UNKNOWN.
G7 Kit governance: no bypass of Kit BLOCKED/FAIL.
G8 Completion: exact-revision local/CI/PR/post-merge evidence.
G9 Live acceptance: mock evidence never substitutes required live proof.
G10 Systemic failure: after two substantive repairs, run SYSTEMIC_FAILURE_REVIEW.

G11 Independent-review regression: F01-F10/K01-K07 remain explicit open/partial
work until their required behavior and evidence are proven. Do not weaken,
rename away, or replace the independent review guarantees with narrower tests.
Whole-product `FUNCTIONALLY_ACCEPTED` remains withdrawn until K07
re-adjudication.
