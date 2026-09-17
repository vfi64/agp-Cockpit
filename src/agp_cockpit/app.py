from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from agp_cockpit import __version__


def build_root(repository_root: Path | None = None, local_contract=None):
    import tkinter as tk
    from agp_cockpit.ui.main_window import MainWindow

    root = tk.Tk()
    root.title('AGP Cockpit')
    root.geometry('1020x600')
    root.minsize(820, 520)
    MainWindow(root, repository_root=repository_root, local_contract=local_contract)
    return root


def run_gui_only(repository_root: Path | None = None, local_contract=None) -> None:
    root = build_root(repository_root, local_contract=local_contract)
    root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='agp-cockpit',
        description=(
            'AGP Cockpit — deterministic local bridge between a browser LLM '
            'and the local terminal/executor.'
        ),
    )
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument(
        '--diagnose', action='store_true',
        help='Run bounded first-run desktop diagnostics without launching the GUI.',
    )
    parser.add_argument(
        '--repository-root', type=Path, default=None,
        help='Repository/context root used by the current bridge runtime. Defaults to cwd.',
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    from agp_cockpit.adapters.macos_settings import settings_path
    from agp_cockpit.settings import SettingsError, load_and_migrate_settings

    try:
        settings, migrated = load_and_migrate_settings(settings_path())
    except SettingsError as exc:
        print(f"AGP Cockpit settings error: {exc}", file=sys.stderr)
        return 2

    if args.diagnose:
        root = (args.repository_root or Path.cwd()).expanduser().resolve()
        from agp_cockpit.first_run_diagnostics import run_first_run_diagnostics

        report = run_first_run_diagnostics(root)
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if report['overall'] != 'FAIL' else 1

    from agp_cockpit.adapters.macos_context import (
        choose_repository_root,
        persist_repository_root,
        resolve_repository_root,
    )
    from agp_cockpit.core.diagnostic_log import DiagnosticLogger

    root, root_source = resolve_repository_root(
        explicit_root=args.repository_root,
        settings=settings,
        cwd=Path.cwd(),
        chooser=choose_repository_root,
    )
    if root is None:
        print("AGP Cockpit requires a valid repository/context root.", file=sys.stderr)
        return 2
    if settings.repository_root != str(root):
        settings = persist_repository_root(settings, root)

    log = DiagnosticLogger(root)
    log.event(
        "DESKTOP_START",
        component="desktop",
        details={
            "settings_schema_version": settings.schema_version,
            "settings_migrated": migrated,
            "repository_root_source": root_source,
            "bridge_host": settings.bridge_host,
            "bridge_port": settings.bridge_port,
        },
    )

    from agp_cockpit.app_bootstrap import run
    from agp_cockpit.core.task_contract import LocalTaskContract

    local_contract = LocalTaskContract(
        root,
        allowed_effects=frozenset(settings.allowed_effects),
        allowed_tools=frozenset(settings.allowed_tools),
        allow_network=settings.allow_network,
    )

    return int(
        run(
            root,
            bridge_host=settings.bridge_host,
            bridge_port=settings.bridge_port,
            local_contract=local_contract,
        )
    )


if __name__ == '__main__':
    raise SystemExit(main())
