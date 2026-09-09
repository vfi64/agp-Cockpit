from __future__ import annotations
from pathlib import Path

class UnsafeRuntimeRoot(RuntimeError):
    pass

def is_transient_runtime_root(path: Path) -> bool:
    value=str(path.expanduser().resolve(strict=False)).lower()
    return value.startswith("/tmp/") or value.startswith("/private/tmp/") or ("var/folders/" in value and "/t/" in value) or "pytest-of-" in value or "/pytest-" in value

def require_stable_production_runtime_root(path: Path) -> Path:
    resolved=path.expanduser().resolve(strict=False)
    if is_transient_runtime_root(resolved):
        raise UnsafeRuntimeRoot(f"production bridge runtime root is transient: {resolved}")
    return resolved
