from __future__ import annotations

from pathlib import Path
import tkinter as tk

from agp_cockpit.ui.main_window import MainWindow


def build_root() -> tk.Tk:
    root = tk.Tk()
    root.title("AGP Cockpit")
    root.geometry("1020x600")
    root.minsize(820, 520)
    MainWindow(root)
    return root


def run_gui_only() -> None:
    root = build_root()
    root.mainloop()


def main() -> None:
    from agp_cockpit.app_bootstrap import run

    raise SystemExit(run(Path.cwd()))


if __name__ == "__main__":
    main()
