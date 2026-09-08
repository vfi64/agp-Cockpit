from __future__ import annotations

from pathlib import Path
import os
import platform
import sys
from typing import Any

from agp_cockpit import __version__


SCHEMA_VERSION = 1


def _check(check_id: str, status: str, message: str, **details: Any) -> dict[str, Any]:
    return {
        'id': check_id,
        'status': status,
        'message': message,
        'details': details,
    }


def _chrome_candidates() -> tuple[Path, ...]:
    return (
        Path('/Applications/Google Chrome.app'),
        Path.home() / 'Applications/Google Chrome.app',
    )


def run_first_run_diagnostics(repository_root: Path) -> dict[str, Any]:
    root = repository_root.expanduser().resolve()
    checks: list[dict[str, Any]] = []

    python_ok = sys.version_info >= (3, 12)
    checks.append(_check(
        'python-version', 'PASS' if python_ok else 'FAIL',
        'Python runtime is supported.' if python_ok else 'Python 3.12+ is required.',
        version=platform.python_version(), executable=sys.executable,
    ))

    system = platform.system()
    checks.append(_check(
        'platform', 'PASS' if system == 'Darwin' else 'WARN',
        'macOS host detected.' if system == 'Darwin' else 'Current v0.1 desktop target is macOS.',
        system=system, release=platform.release(),
    ))

    chrome = next((path for path in _chrome_candidates() if path.exists()), None)
    if system == 'Darwin':
        checks.append(_check(
            'chrome', 'PASS' if chrome else 'FAIL',
            'Google Chrome was found.' if chrome else 'Google Chrome was not found.',
            path=str(chrome) if chrome else None,
        ))
    else:
        checks.append(_check(
            'chrome', 'WARN', 'Chrome discovery is only authoritative on macOS.',
            path=str(chrome) if chrome else None,
        ))

    root_exists = root.exists() and root.is_dir()
    checks.append(_check(
        'context-root', 'PASS' if root_exists else 'FAIL',
        'Repository/context root is available.' if root_exists else 'Repository/context root is unavailable.',
        path=str(root),
    ))

    state_root = root / '.local' / 'agp-cockpit'
    parent = state_root if state_root.exists() else state_root.parent
    try:
        parent.mkdir(parents=True, exist_ok=True)
        writable = os.access(parent, os.W_OK)
    except OSError:
        writable = False
    checks.append(_check(
        'local-state', 'PASS' if writable else 'FAIL',
        'Local Cockpit state location is writable.' if writable else 'Local Cockpit state location is not writable.',
        path=str(state_root),
    ))

    try:
        if platform.system() == 'Darwin':
            from agp_cockpit.adapters.macos_settings import settings_path
            from agp_cockpit.settings import load_settings

            user_settings, migration_needed = load_settings(settings_path())
            checks.append(_check(
                'settings', 'PASS',
                'User settings are readable and schema-compatible.',
                schema_version=user_settings.schema_version,
                migration_needed=migration_needed,
                path=str(settings_path()),
            ))
        else:
            checks.append(_check(
                'settings', 'WARN',
                'macOS user-settings location is not authoritative on this host.',
                path=None,
            ))
    except Exception as exc:
        checks.append(_check(
            'settings', 'FAIL',
            'User settings are unreadable or incompatible.',
            error=str(exc),
        ))

    extension_dir = root / 'chrome_extension'
    checks.append(_check(
        'browser-extension-assets', 'PASS' if extension_dir.is_dir() else 'WARN',
        'Browser extension assets are available in the selected context.' if extension_dir.is_dir()
        else 'Browser extension assets are not present in the selected context.',
        path=str(extension_dir),
    ))

    statuses = {item['status'] for item in checks}
    overall = 'FAIL' if 'FAIL' in statuses else ('WARN' if 'WARN' in statuses else 'PASS')
    return {
        'schema': 'agp-cockpit.first-run-diagnostics.v1',
        'schema_version': SCHEMA_VERSION,
        'application': 'agp-cockpit',
        'application_version': __version__,
        'overall': overall,
        'checks': checks,
    }
