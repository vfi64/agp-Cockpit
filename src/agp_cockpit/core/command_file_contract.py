from __future__ import annotations

import ast
from pathlib import Path


def _embedded_step_number(tree: ast.AST) -> int | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "STEP":
                value = node.value
            elif isinstance(target, (ast.Tuple, ast.List)):
                names = [item.id if isinstance(item, ast.Name) else None for item in target.elts]
                if "STEP" not in names or not isinstance(node.value, (ast.Tuple, ast.List)):
                    continue
                value = node.value.elts[names.index("STEP")]
            else:
                continue
            if isinstance(value, ast.Constant) and isinstance(value.value, int):
                return int(value.value)
    return None


# AGP_KIT_COMMAND_AUTHORITY_V1: every work order executes at least one
# agentic-kit command (AGENTS.md: the Kit is the command authority). The rule
# is enforced below and stated verbatim to the remote side, which previously
# learned it only from a rejection (live 2026-09-30, step 1486).
WORK_ORDER_KIT_RULE = (
    "Every work order MUST execute at least one agentic-kit command during its real run; "
    "the Kit is the command authority. Use only commands from the agentic-kit command digest "
    "attached to the mission start, prefer the most comprehensive orchestrator command, and "
    "never run git push, git fetch or git pull. Other allowed tools such as git may only be "
    "used in addition. Record every agentic-kit command's argv, returncode, stdout and "
    "stderr (tails) in the return bundle."
    # AGP_WORK_ORDER_SHAPE_RULE_V1 (live 2026-10-02, step 1568): a fresh chat
    # knew nothing of the structural contract below and was stopped by it.
    " Work-order shape, checked locally before anything runs: a main() function and an "
    "if __name__ == '__main__': guard; a module constant STEP equal to the expected local step; "
    "a --self-test mode (sys.argv or argparse) that only checks the file itself, runs no command, "
    "writes no file and exits 0; the real run writes exactly one JSON return bundle named "
    "Download/<STEP>_<topic>_return_bundle.json."
)


def command_content_contract_violations(
    source: str,
    *,
    filename: str = "<command-file>",
    expected_step: int | None = None,
) -> list[str]:
    """Reject syntactically valid but incomplete remote work-order files."""
    tree = ast.parse(source, filename=filename)
    embedded_step = _embedded_step_number(tree)
    functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    has_self_test_argument = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "add_argument"
        and any(
            isinstance(argument, ast.Constant) and argument.value == "--self-test"
            for argument in node.args
        )
        for node in ast.walk(tree)
    )
    has_self_test_argv_guard = any(
        isinstance(node, ast.Compare)
        and len(node.ops) == 1
        and isinstance(node.ops[0], ast.In)
        and isinstance(node.left, ast.Constant)
        and node.left.value == "--self-test"
        and len(node.comparators) == 1
        and isinstance(node.comparators[0], ast.Attribute)
        and isinstance(node.comparators[0].value, ast.Name)
        and node.comparators[0].value.id == "sys"
        and node.comparators[0].attr == "argv"
        for node in ast.walk(tree)
    )
    has_bundle_writer = any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"write_text", "write_bytes"}
        for node in ast.walk(tree)
    ) or any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"dump", "dump_json"}
        for node in ast.walk(tree)
    )
    has_main_guard = any(
        isinstance(node, ast.If)
        and isinstance(node.test, ast.Compare)
        and isinstance(node.test.left, ast.Name)
        and node.test.left.id == "__name__"
        and any(
            isinstance(value, ast.Constant) and value.value == "__main__"
            for value in node.test.comparators
        )
        for node in ast.walk(tree)
    )
    violations: list[str] = []
    if "main" not in functions:
        violations.append("missing main() entry point")
    if not has_main_guard:
        violations.append("missing __main__ execution guard")
    if expected_step is not None and embedded_step is not None and embedded_step != expected_step:
        violations.append(f"embedded STEP {embedded_step} does not match local step {expected_step}")
    if "--self-test" not in strings or not (has_self_test_argument or has_self_test_argv_guard):
        violations.append("missing --self-test contract")
    if "agentic-kit" not in strings:
        violations.append("missing declared agentic-kit command")
    if not any("return_bundle" in value for value in strings) or not has_bundle_writer:
        violations.append("missing return-bundle contract")
    return violations


def command_contract_violations(
    command_file: Path,
    expected_step: int | None = None,
) -> list[str]:
    source = command_file.read_text(encoding="utf-8")
    return command_content_contract_violations(
        source,
        filename=str(command_file),
        expected_step=expected_step,
    )


def validate_command_content(
    source: str,
    *,
    filename: str = "<command-file>",
    expected_step: int | None = None,
    repository_root: Path | None = None,
    allow_remote_effects: bool = False,
    require_orchestrator: bool = False,
    catalog_checks: bool = True,
) -> None:
    try:
        violations = command_content_contract_violations(
            source,
            filename=filename,
            expected_step=expected_step,
        )
        # AGP_KIT_COMMAND_CATALOG_V1: manifest-based command authority.
        from agp_cockpit.core.kit_command_catalog import (
            KitCommandCatalog,
            command_catalog_violations,
        )
        catalog = (KitCommandCatalog.load(repository_root)
                   if repository_root is not None and catalog_checks else None)
        violations = violations + command_catalog_violations(
            source, catalog, allow_remote_effects=allow_remote_effects,
            require_orchestrator=require_orchestrator,
        )
        if repository_root is not None and catalog_checks:
            from agp_cockpit.core.release_policy import violations as release_violations
            violations = violations + release_violations(source, repository_root, catalog)
    except SyntaxError as exc:
        raise ValueError(
            f"command file is not executable Python: {type(exc).__name__}: {exc}"
        ) from exc
    if violations:
        raise ValueError(
            "command file semantic contract rejected: " + "; ".join(violations)
        )
