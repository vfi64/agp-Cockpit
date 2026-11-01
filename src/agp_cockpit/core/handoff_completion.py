"""Local, contract-scoped handoff verification and delivery receipts.

Visible assistant prose is never completion evidence. A successful work order
must produce fresh artifacts, pass the installed Kit validator, and have its
result delivered before the existing durable completion gate is used.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from .task_models import KitResultEvidence

CONTRACT_KIND = "verified-successor-handoff-v1"
PACKAGE = Path(".agentic/state/handoff/packages/latest")
FILES = (
    "execution_contract.json", "source_manifest.json", "successor_context.yaml",
    "successor_prompt.md", "validation_report.json",
)
# AGP_HANDOFF_PROJECTION_V2_CONSUMER_V1 (KIT-GF-094, Kit main 334ac052): external workspaces get a
# deterministic, versioned projection without Git state (contract v2). Its files stay byte-identical across
# regenerations; the run is proven by the ignored runtime identity (new run_id, exact HEAD, validator PASS of
# the same run), never by changed package files. v1 keeps its old evidence. Any other contract version is
# BLOCKED: the Cockpit never guesses how to read a projection it does not know.
RUNTIME_IDENTITY = Path(".agentic/tmp/handoff/runtime_identity.json")   # docs/reference/EXTERNAL_HANDOFF_V2.md
KNOWN_PROJECTION_CONTRACTS = frozenset({1, 2})
FINAL_RECEIPT_PROMPT = (
    "Attached is the final local handoff result. The Cockpit has independently "
    "validated the generated package. Acknowledge receipt only; do not create "
    "another work order or start further product work."
)
_VALIDATE = """
import json, sys
from pathlib import Path
import yaml
from agentic_project_kit.workspace import load_workspace
from agentic_project_kit.successor_handoff_package import validate_successor_outputs
root = Path(sys.argv[1])
package = root / '.agentic/state/handoff/packages/latest'
names = ('execution_contract.json', 'source_manifest.json', 'successor_context.yaml',
         'successor_prompt.md', 'validation_report.json')
outputs = {name: (package / name).read_text(encoding='utf-8') for name in names}
report = validate_successor_outputs(outputs, yaml.safe_load(outputs['successor_context.yaml']),
                                    load_workspace(root))
print(json.dumps(report))
"""


_VALIDATE_V2 = """
import json, sys
from pathlib import Path
from agentic_project_kit.external_handoff_projection import (
    PROJECTION_CONTRACT_VERSION, RUNTIME_PATH, check_projection, validate_runtime_identity)
root, head = Path(sys.argv[1]), sys.argv[2]
identity = json.loads((root / RUNTIME_PATH).read_text(encoding='utf-8'))
print(json.dumps({"contract": PROJECTION_CONTRACT_VERSION, "runtime_path": str(RUNTIME_PATH),
                  "projection": check_projection(root), "identity": identity,
                  "identity_status": validate_runtime_identity(identity, expected_head=head)}))
"""


def projection_contract(root: Path) -> int:
    """1 for the commit-bound v1 package, 2 for the external v2 projection; BLOCKED otherwise."""
    try:
        report = json.loads((root / PACKAGE / "validation_report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"handoff validation report unreadable: {exc}") from exc
    # ValueError on purpose: callers treat it as "not a verified handoff" (a TypeError would escape them).
    version = (report.get("projection_contract_version", 1 if "generated_head" in report else None)
               if isinstance(report, dict) else None)
    if version not in KNOWN_PROJECTION_CONTRACTS or isinstance(version, bool):
        raise ValueError(f"BLOCKED: unknown handoff projection contract {version!r}; update the Cockpit first")
    return int(version)


def runtime_run_id(root: Path) -> str | None:
    try:
        data = json.loads((root / RUNTIME_IDENTITY).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    run_id = data.get("run_id") if isinstance(data, dict) else None
    return run_id if isinstance(run_id, str) and run_id.strip() else None


def validate_v2_with_kit(root: Path, head: str) -> dict:
    """The installed Kit's own pure check plus the Cockpit's independent reading of the runtime identity."""
    result = subprocess.run(
        [str(root / ".venv/bin/python"), "-c", _VALIDATE_V2, str(root), head],
        cwd=root, capture_output=True, text=True, timeout=60, check=True,
    )
    report = json.loads(result.stdout)
    identity = report.get("identity") if isinstance(report, dict) else None
    identity = identity if isinstance(identity, dict) else {}
    if not identity:
        raise ValueError("handoff runtime identity missing")
    if report.get("runtime_path") != str(RUNTIME_IDENTITY):
        raise ValueError("BLOCKED: the Kit moved the handoff runtime identity; update the Cockpit first")
    version = identity.get("projection_contract_version")
    if report.get("contract") != 2 or version != 2:
        raise ValueError(f"BLOCKED: unknown handoff projection contract {version!r}; update the Cockpit first")
    projection = report.get("projection") or {}
    if projection.get("status") != "PASS":
        raise ValueError(f"installed Kit rejected handoff projection: {projection.get('code') or 'FAIL'}")
    if (report.get("identity_status") != "PASS" or identity.get("schema_version") != 1
            or identity.get("head") != head or identity.get("generated_head") != head
            or any(identity.get(key) != "PASS" for key in ("freshness", "integrity", "validator_status"))):
        raise ValueError("handoff runtime identity is not a PASS for the current HEAD")
    return report


def digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= 2_000_000:
        raise ValueError(f"missing, linked or oversized handoff evidence: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contract_enabled(controller) -> bool:
    contract = controller.store.runtime_contract(controller.task_id) or {}
    scope = json.loads(contract.get("scope_json") or "{}")
    return isinstance(scope, dict) and scope.get("completion_contract") == {"kind": CONTRACT_KIND}


def package_snapshot(root: Path) -> dict:
    snapshot = {
        name: (root / PACKAGE / name).stat().st_mtime_ns
        if (root / PACKAGE / name).is_file() else None
        for name in FILES
    }
    snapshot["runtime_run_id"] = runtime_run_id(root)   # v2: the run before this step
    return snapshot


def validate_with_kit(root: Path) -> dict:
    result = subprocess.run(
        [str(root / ".venv/bin/python"), "-c", _VALIDATE, str(root)],
        cwd=root, capture_output=True, text=True, timeout=30, check=True,
    )
    report = json.loads(result.stdout)
    if not isinstance(report, dict) or report.get("status") != "PASS" or report.get("findings"):
        raise ValueError("installed Kit rejected handoff artifacts")
    return report


NEGATIVE_DECLARATIONS = frozenset({"FAIL", "FAILED", "BLOCKED", "ERROR"})


def prepare_receipt(root: Path, runtime: Path, *, mission_id: str, task_id: str,
                    cycle_id: str, run, before: dict) -> dict | None:
    """Return a receipt only when locally observed evidence proves the handoff.

    AGP_HANDOFF_EVIDENCE_NOT_SCHEMA_V1: live 2026-09-30 (step 1482) the remote
    return bundle used "state"/"command" instead of "status"/"execution"; the
    old schema check returned None and the verified PASS was sent on as an
    ordinary continuation. Remote-authored fields are claims, not evidence.
    Completion rests on what the Cockpit observes itself: successful runner,
    package regenerated during this step, installed Kit validator PASS,
    Kit-written validation report for the current HEAD. A remote *negative*
    declaration is respected; a remote positive one is never required.
    None means "not a completion": the loop continues and never succeeds.
    """
    if run.runner_returncode != 0 or run.artifact_kind != "return_bundle":
        return None
    bundle = json.loads(run.return_bundle.read_text(encoding="utf-8"))
    if not isinstance(bundle, dict):
        return None
    declared = str(bundle.get("status") or bundle.get("state") or "").strip().upper()
    if declared in NEGATIVE_DECLARATIONS:
        return None
    version = projection_contract(root)
    if version == 2:
        # Byte-stable files are expected; a new run of the generator is the evidence of regeneration.
        run_id = runtime_run_id(root)
        if run_id is None or run_id == before.get("runtime_run_id"):
            return None
    else:
        current = package_snapshot(root)
        regenerated = [name for name in FILES if current[name] is not None and current[name] != before.get(name)]
        if not regenerated:
            return None
        if len(regenerated) != len(FILES):
            raise ValueError("handoff package was not freshly generated by this run")
    claimed_package = bundle.get("package_path")
    if claimed_package and Path(claimed_package).resolve() != root / PACKAGE:
        raise ValueError("noncanonical handoff package")
    prompt = Path(str(bundle.get("detailed_start_prompt_path") or "")).resolve()
    if prompt.parent != root / "Download" or not prompt.name.startswith(f"{run.step}_"):
        raise ValueError("detailed prompt does not belong to this local step")
    paths = [root / PACKAGE / name for name in FILES] + [prompt, run.return_bundle]
    if version == 2:
        paths.append(root / RUNTIME_IDENTITY)
    hashes = {str(path): digest(path) for path in paths}
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                          capture_output=True, check=True, timeout=10).stdout.strip()
    stored_report = json.loads((root / PACKAGE / "validation_report.json").read_text())
    if version == 2:
        report = validate_v2_with_kit(root, head)
        if stored_report.get("status") != "PASS" or report["identity"].get("run_id") != run_id:
            raise ValueError("handoff validation revision is stale")
    else:
        report = validate_with_kit(root)
        if stored_report.get("status") != "PASS" or stored_report.get("generated_head") != head:
            raise ValueError("handoff validation revision is stale")
    if hashes != {str(path): digest(path) for path in paths}:
        raise ValueError("handoff evidence changed during validation")
    receipt = {
        "mission_id": mission_id, "task_id": task_id, "cycle_id": cycle_id,
        "result_sha256": hashes[str(run.return_bundle)], "hashes": hashes,
        "revision": head, "report": report, "delivered": False,
        "projection_contract": version, "run_id": run_id if version == 2 else None,
    }
    _save(runtime, receipt)
    return receipt


def _save(runtime: Path, receipt: dict) -> None:
    path = runtime / "handoff-completion.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


def acknowledge_delivery(root: Path, runtime: Path, controller, *, mission_id: str,
                         cycle_id: str, result_sha256: str, require_active=None) -> dict:
    receipt = json.loads((runtime / "handoff-completion.json").read_text())
    expected = (mission_id, controller.task_id, cycle_id, result_sha256)
    actual = tuple(receipt.get(key) for key in ("mission_id", "task_id", "cycle_id", "result_sha256"))
    if not contract_enabled(controller) or expected != actual:
        raise ValueError("stale or foreign handoff delivery receipt")
    if any(digest(Path(path)) != value for path, value in receipt["hashes"].items()):
        raise ValueError("handoff evidence changed before delivery acknowledgement")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, text=True,
                          capture_output=True, check=True, timeout=10).stdout.strip()
    if head != receipt["revision"]:
        raise ValueError("repository revision changed before handoff completion")
    if receipt.get("projection_contract", 1) == 2:
        report = validate_v2_with_kit(root, head)
        if report["identity"].get("run_id") != receipt.get("run_id"):
            raise ValueError("handoff runtime identity changed before delivery acknowledgement")
    else:
        report = validate_with_kit(root)
    if any(digest(Path(path)) != value for path, value in receipt["hashes"].items()):
        raise ValueError("handoff evidence changed during final validation")
    if require_active is not None:
        require_active()
    raw_hash = hashlib.sha256(json.dumps(report, sort_keys=True).encode()).hexdigest()
    artifact_hash = hashlib.sha256(json.dumps(receipt["hashes"], sort_keys=True).encode()).hexdigest()
    action_id = "handoff-validation-" + cycle_id
    # Reuse the durable completion gate, including governance and unsettled effects.
    if controller.snapshot["state"] != "VERIFIED_COMPLETE":
        unsettled = controller.store.db.execute(
            "SELECT 1 FROM actions WHERE task_id=? AND status NOT IN "
            "('PASS','FAIL','BLOCKED','RECONCILED_APPLIED','RECONCILED_NOT_APPLIED') LIMIT 1",
            (controller.task_id,),
        ).fetchone()
        if controller.snapshot["state"] in {"CANCELLED", "SUSPENDED"} or unsettled:
            raise ValueError("task has stopped or has unsettled effects")
        controller.store.register_action(controller.task_id, action_id, {"kind": CONTRACT_KIND})
        with controller.store.db:
            controller.store.reserve_action_budgets(controller.task_id, action_id, 0)
        attempt = controller.begin_attempt(action_id)
        controller.record_local_result(action_id, attempt, "PASS", "Installed Kit validated local handoff")
        controller.record_verified_kit_result(
            KitResultEvidence(action_id, "PASS", "agentic-project-kit",
                              ("check_projection", "validate_runtime_identity")
                              if receipt.get("projection_contract", 1) == 2 else ("validate_successor_outputs",),
                              head, artifact_hash, raw_hash),
            acquisition_source="local-kit-handoff-validator",
        )
        controller.set_completion_contract(head, artifact_hash, action_id, raw_hash)
        controller.propose_complete()
        if not controller.verify_completion_contract():
            raise ValueError("durable completion gate rejected handoff")
    receipt["delivered"] = True
    _save(runtime, receipt)
    return {"state": "DONE", "terminal": True, "human_reason": "Handoff verified and result delivered"}
