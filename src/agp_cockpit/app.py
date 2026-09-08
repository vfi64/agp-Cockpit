from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from agp_cockpit import __version__


def build_root():
    import tkinter as tk
    from agp_cockpit.ui.main_window import MainWindow

    root = tk.Tk()
    root.title('AGP Cockpit')
    root.geometry('1020x600')
    root.minsize(820, 520)
    MainWindow(root)
    return root


def run_gui_only() -> None:
    root = build_root()
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
    root = (args.repository_root or Path.cwd()).expanduser().resolve()

    if args.diagnose:
        from agp_cockpit.first_run_diagnostics import run_first_run_diagnostics

        report = run_first_run_diagnostics(root)
        print(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
        return 0 if report['overall'] != 'FAIL' else 1

    from agp_cockpit.app_bootstrap import run
    return int(run(root))


if __name__ == '__main__':
    raise SystemExit(main())
