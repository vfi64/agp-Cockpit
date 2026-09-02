from __future__ import annotations

import tkinter as tk

from agp_cockpit.ui.main_window import MainWindow


def build_root() -> tk.Tk:
    root = tk.Tk()
    root.title("AGP Cockpit")
    root.geometry("1020x600")
    root.minsize(820, 520)
    MainWindow(root)
    return root


def main() -> None:
    root = build_root()
    root.mainloop()


if __name__ == "__main__":
    main()
